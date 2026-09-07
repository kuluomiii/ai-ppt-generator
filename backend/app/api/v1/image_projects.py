"""AI 图片生成项目接口。

独立于 PPT 功能，不影响现有 projects / outlines / deck 路由。
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_queue
from app.core.config import get_settings
from app.core.db import get_session
from app.llm.client import create_chat_model
from app.models.image_project import ImageProject
from app.models.user import User
from app.schemas.image_project import (
    ImageProjectCreate,
    ImageProjectListResponse,
    ImageProjectResponse,
    OptimizedPromptResponse,
    ProgressResponse,
    PromptUpdate,
)
from app.services.image_generation import enforce_record_limit, optimize_prompt
from app.services.media import media_url
from app.storage import get_storage

router = APIRouter(prefix="/image-projects", tags=["图片生成"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# 依赖：按用户隔离取图片项目（别人的返回 404）
# ---------------------------------------------------------------------------
async def get_owned_image_project(
    project_id: Annotated[uuid.UUID, Path()],
    session: SessionDep,
    current_user: CurrentUser,
) -> ImageProject:
    result = await session.execute(
        select(ImageProject).where(
            ImageProject.id == project_id,
            ImageProject.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="图片项目不存在"
        )
    return project


OwnedImageProject = Annotated[ImageProject, Depends(get_owned_image_project)]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _build_image_url(project: ImageProject) -> str | None:
    """将存储 key 拼接为可访问的 media URL。"""
    if project.image_key:
        return media_url(project.image_key)
    return None


def _to_response(project: ImageProject) -> ImageProjectResponse:
    return ImageProjectResponse(
        id=project.id,
        raw_prompt=project.raw_prompt,
        style=project.style,
        aspect_ratio=project.aspect_ratio,
        optimized_prompt=project.optimized_prompt,
        status=project.status,
        progress=project.progress,
        error_message=project.error_message,
        image_url=_build_image_url(project),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------


@router.post("", response_model=ImageProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_image_project(
    body: ImageProjectCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ImageProjectResponse:
    """创建图片生成项目。超过 10 条时自动清理最早记录。"""
    storage = get_storage()
    await enforce_record_limit(session, current_user.id, storage)

    project = ImageProject(
        user_id=current_user.id,
        raw_prompt=body.raw_prompt,
        style=body.style,
        aspect_ratio=body.aspect_ratio,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return _to_response(project)


@router.get("", response_model=ImageProjectListResponse)
async def list_image_projects(
    session: SessionDep,
    current_user: CurrentUser,
) -> ImageProjectListResponse:
    """获取当前用户最近的图片项目列表（最多 10 条）。"""
    stmt = (
        select(ImageProject)
        .where(ImageProject.user_id == current_user.id)
        .order_by(ImageProject.created_at.desc())
        .limit(10)
    )
    result = await session.execute(stmt)
    projects = result.scalars().all()

    count_stmt = (
        select(func.count())
        .select_from(ImageProject)
        .where(ImageProject.user_id == current_user.id)
    )
    total = (await session.execute(count_stmt)).scalar() or 0

    return ImageProjectListResponse(
        items=[_to_response(p) for p in projects],
        total=min(total, 10),
    )


@router.get("/{project_id}", response_model=ImageProjectResponse)
async def get_image_project(project: OwnedImageProject) -> ImageProjectResponse:
    """获取图片项目详情。"""
    return _to_response(project)


@router.post("/{project_id}/prompt", response_model=OptimizedPromptResponse)
async def generate_optimized_prompt(
    project: OwnedImageProject,
    session: SessionDep,
) -> OptimizedPromptResponse:
    """使用 LLM 根据原始需求和风格模板生成优化后的英文提示词。"""
    settings = get_settings()
    if not settings.llm_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 服务未配置",
        )

    chat = create_chat_model(settings)
    try:
        optimized = await optimize_prompt(
            chat=chat,
            style=project.style,
            raw_prompt=project.raw_prompt,
            aspect_ratio=project.aspect_ratio,
        )
    finally:
        client = getattr(chat, "async_client", None)
        if client is not None:
            close = getattr(client, "close", None)
            if close is not None:
                await close()

    project.optimized_prompt = optimized
    await session.commit()

    return OptimizedPromptResponse(optimized_prompt=optimized)


@router.patch("/{project_id}/prompt", response_model=ImageProjectResponse)
async def update_prompt(
    body: PromptUpdate,
    project: OwnedImageProject,
    session: SessionDep,
) -> ImageProjectResponse:
    """保存用户手动编辑的优化提示词。"""
    project.optimized_prompt = body.optimized_prompt
    await session.commit()
    await session.refresh(project)
    return _to_response(project)


@router.post("/{project_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_generation(
    project: OwnedImageProject,
    session: SessionDep,
) -> dict[str, str]:
    """提交图片生成任务到 ARQ 队列。

    - generating → 409（正在生成中不可重复提交）
    - pending 且已有 job_id → 409（已入队等待执行）
    - pending 且无 job_id → 允许（首次提交）
    - completed/failed → 允许（重新生成/重试）
    - 无 optimized_prompt → 422
    """
    if project.status == "generating":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="任务正在生成中，请勿重复提交",
        )
    if project.status == "pending" and project.job_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="任务已提交，正在排队中",
        )

    if not project.optimized_prompt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="请先生成或填写优化提示词",
        )

    # 重置状态（支持 failed 重试）
    project.status = "pending"
    project.progress = 0
    project.error_message = None
    project.image_key = None

    job_id = str(uuid.uuid4())
    project.job_id = uuid.UUID(job_id)
    await session.commit()

    queue = await get_queue()
    try:
        await queue.enqueue_job("generate_image", str(project.id), job_id, _job_id=job_id)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="任务队列不可用，请稍后重试",
        ) from error

    return {"message": "生成任务已提交", "job_id": job_id}


@router.get("/{project_id}/progress", response_model=ProgressResponse)
async def get_progress(project: OwnedImageProject) -> ProgressResponse:
    """轮询生成进度。"""
    return ProgressResponse(
        status=project.status,
        progress=project.progress,
        error_message=project.error_message,
        image_url=_build_image_url(project),
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_project(
    project: OwnedImageProject,
    session: SessionDep,
) -> None:
    """删除图片项目及关联的存储文件。"""
    if project.image_key:
        storage = get_storage()
        try:
            storage.delete(project.image_key)
        except Exception:
            pass  # best-effort 清理

    await session.delete(project)
    await session.commit()
