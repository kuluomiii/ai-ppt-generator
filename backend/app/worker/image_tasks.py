"""ARQ Worker 任务：AI 图片生成。

流程：幂等校验 → 调 Seedream → 下载图片 → 校验 → 存本地 Storage → 更新状态。
Seedream 返回的是临时 URL，必须下载到本地持久化存储。

进度百分比约定：
    0   = pending（排队中）
    10  = generating 开始
    40  = Seedream API 调用完成
    70  = 图片下载 + 校验完成
    90  = 图片已保存到 Storage
    100 = completed / failed（终态）
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from sqlalchemy import select

from app.core.db import async_session_factory
from app.images.seedream import SeedreamClient
from app.images.validate import ImageRejected, validate_image
from app.models.image_project import ImageProject
from app.storage import get_storage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 错误映射：不泄露供应商内部信息
# ---------------------------------------------------------------------------
_HTTP_ERROR_MAP: dict[int, str] = {
    401: "图片生成服务认证失败，请联系管理员",
    403: "图片生成服务认证失败，请联系管理员",
    429: "图片生成服务繁忙，请稍后重试",
    500: "图片生成服务内部错误，请稍后重试",
    502: "图片生成服务暂时不可用，请稍后重试",
    503: "图片生成服务维护中，请稍后重试",
}


def _public_error(exc: Exception) -> str:
    """将底层异常转换为用户友好的中文错误信息。"""
    if isinstance(exc, ValueError):
        # SeedreamClient 在 API Key 为空时抛 ValueError
        return "图片生成服务未配置，请联系管理员"
    if isinstance(exc, httpx.HTTPStatusError):
        return _HTTP_ERROR_MAP.get(
            exc.response.status_code,
            f"图片生成服务异常（{exc.response.status_code}），请稍后重试",
        )
    if isinstance(exc, httpx.TimeoutException):
        return "图片生成超时，请稍后重试"
    if isinstance(exc, RuntimeError):
        # SeedreamClient 在响应格式异常时抛 RuntimeError
        return "图片生成结果异常，请重试"
    if isinstance(exc, ImageRejected):
        return str(exc)
    return "图片生成失败，请稍后重试"


async def _update_progress(project_uuid: uuid.UUID, job_id: str, progress: int) -> None:
    """安全更新进度值（仅在 job_id 匹配时写入）。"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(ImageProject)
            .where(ImageProject.id == project_uuid)
            .with_for_update()
        )
        project = result.scalar_one_or_none()
        if project is None or str(project.job_id) != job_id:
            return
        project.progress = progress
        await session.commit()


async def generate_image(ctx: dict[str, Any], entity_id: str, job_id: str) -> None:
    """ARQ 异步任务：调用 Seedream 生成图片并保存到本地存储。

    Parameters
    ----------
    ctx : dict
        ARQ worker context，包含共享的 seedream_client 和 http_client。
    entity_id : str
        ImageProject UUID。
    job_id : str
        幂等校验用的任务 ID。
    """
    project_uuid = uuid.UUID(entity_id)

    async with async_session_factory() as session:
        # ---- 幂等校验 ----
        result = await session.execute(
            select(ImageProject)
            .where(ImageProject.id == project_uuid)
            .with_for_update()
        )
        project = result.scalar_one_or_none()

        if project is None:
            logger.warning("generate_image: project %s not found, skipping", entity_id)
            return

        if str(project.job_id) != job_id:
            logger.info(
                "generate_image: job_id mismatch for %s (expected %s, got %s), skipping",
                entity_id,
                project.job_id,
                job_id,
            )
            return

        # ---- 状态流转：pending → generating, progress=10 ----
        project.status = "generating"
        project.progress = 10
        await session.commit()

    try:
        # ---- 调用 Seedream (progress 10→40) ----
        client: SeedreamClient = ctx["seedream_client"]
        image_url = await client.generate(
            prompt=project.optimized_prompt or project.raw_prompt,
            aspect_ratio=project.aspect_ratio,
        )
        await _update_progress(project_uuid, job_id, 40)

        # ---- 下载图片 (progress 40→60) ----
        http_client: httpx.AsyncClient = ctx["http_client"]
        resp = await http_client.get(image_url, timeout=60.0)
        resp.raise_for_status()
        image_data = resp.content
        await _update_progress(project_uuid, job_id, 60)

        # ---- 校验图片 (progress 60→70) ----
        ext, _content_type = validate_image(image_data)
        await _update_progress(project_uuid, job_id, 70)

        # ---- 存入本地 Storage (progress 70→90) ----
        storage = get_storage()
        key = f"media/{project.user_id}/{uuid.uuid4().hex}{ext}"
        storage.save(key, image_data)
        await _update_progress(project_uuid, job_id, 90)

        # ---- 更新为完成 (progress=100) ----
        async with async_session_factory() as session:
            result = await session.execute(
                select(ImageProject)
                .where(ImageProject.id == project_uuid)
                .with_for_update()
            )
            project = result.scalar_one_or_none()
            if project is None or str(project.job_id) != job_id:
                logger.info("generate_image: project deleted/changed during generation, skipping")
                return

            project.image_key = key
            project.status = "completed"
            project.progress = 100
            project.error_message = None
            await session.commit()

        logger.info("generate_image: completed for %s", entity_id)

    except Exception as exc:
        # ---- 失败：保存用户友好错误, progress=100 ----
        error_msg = _public_error(exc)
        logger.error("generate_image: failed for %s: %s", entity_id, exc, exc_info=True)

        async with async_session_factory() as session:
            result = await session.execute(
                select(ImageProject)
                .where(ImageProject.id == project_uuid)
                .with_for_update()
            )
            project = result.scalar_one_or_none()
            if project is None or str(project.job_id) != job_id:
                return

            project.status = "failed"
            project.progress = 100
            project.error_message = error_msg
            await session.commit()
