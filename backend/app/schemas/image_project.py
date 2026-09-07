from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# 枚举常量
# ---------------------------------------------------------------------------
StyleTemplate = Literal["chiikawa_science", "minimal_doodle", "shinchan_education"]
AspectRatio = Literal["1:1", "16:9", "9:16"]
ImageProjectStatus = Literal["pending", "generating", "completed", "failed"]


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------
class ImageProjectCreate(BaseModel):
    raw_prompt: str = Field(min_length=1, max_length=2000, description="原始图片需求")
    style: StyleTemplate = Field(description="风格模板")
    aspect_ratio: AspectRatio = Field(description="宽高比")


class PromptUpdate(BaseModel):
    optimized_prompt: str = Field(
        min_length=1, max_length=5000, description="用户编辑后的优化提示词"
    )


# ---------------------------------------------------------------------------
# 响应模型
# ---------------------------------------------------------------------------
class ImageProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_prompt: str
    style: StyleTemplate
    aspect_ratio: AspectRatio
    optimized_prompt: str | None = None
    status: ImageProjectStatus
    progress: int = Field(ge=0, le=100, description="生成进度百分比 0-100")
    error_message: str | None = None
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime


class ImageProjectListResponse(BaseModel):
    """列表响应，最多 10 条。"""

    items: list[ImageProjectResponse]
    total: int = Field(le=10)


class OptimizedPromptResponse(BaseModel):
    optimized_prompt: str = Field(description="LLM 生成的优化提示词")


class ProgressResponse(BaseModel):
    status: ImageProjectStatus
    progress: int = Field(ge=0, le=100, description="生成进度百分比 0-100")
    error_message: str | None = None
    image_url: str | None = None
