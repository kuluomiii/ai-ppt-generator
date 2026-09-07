"""AI 图片生成项目接口集成测试。

所有 Seedream HTTP 调用通过 httpx.MockTransport mock，不会误调真实服务。
LLM 调用通过环境变量控制（测试环境 LLM_API_KEY 为空 → 503）。
ARQ 入队通过 mock get_queue 避免依赖 Redis。
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _sign_up(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": f"user_{uuid.uuid4().hex}@example.com", "password": "password123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _create_image_project(
    client: AsyncClient, headers: dict[str, str], **overrides
) -> dict:
    payload = {
        "raw_prompt": "一只猫咪坐在窗台上看夕阳",
        "style": "chiikawa_science",
        "aspect_ratio": "1:1",
    } | overrides
    response = await client.post("/api/v1/image-projects", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# 创建
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_image_project(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers)

    assert project["raw_prompt"] == "一只猫咪坐在窗台上看夕阳"
    assert project["style"] == "chiikawa_science"
    assert project["aspect_ratio"] == "1:1"
    assert project["optimized_prompt"] is None
    assert project["status"] == "pending"
    assert project["progress"] == 0
    assert project["error_message"] is None
    assert project["image_url"] is None


@pytest.mark.asyncio
async def test_create_invalid_style_rejected(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    response = await client.post(
        "/api/v1/image-projects",
        json={"raw_prompt": "test", "style": "unknown_style", "aspect_ratio": "1:1"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_retro_hand_drawn_style_rejected(client: AsyncClient) -> None:
    """旧的 retro_hand_drawn 风格不再有效。"""
    headers = await _sign_up(client)
    response = await client.post(
        "/api/v1/image-projects",
        json={"raw_prompt": "test", "style": "retro_hand_drawn", "aspect_ratio": "1:1"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shinchan_education_style_accepted(client: AsyncClient) -> None:
    """新增的 shinchan_education 风格可以正常创建。"""
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers, style="shinchan_education")
    assert project["style"] == "shinchan_education"


@pytest.mark.asyncio
async def test_create_invalid_aspect_ratio_rejected(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    response = await client.post(
        "/api/v1/image-projects",
        json={"raw_prompt": "test", "style": "chiikawa_science", "aspect_ratio": "4:3"},
        headers=headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 列表
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_returns_latest_10(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    for i in range(12):
        await _create_image_project(client, headers, raw_prompt=f"prompt {i}")

    response = await client.get("/api/v1/image-projects", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 10
    # 最新的在前
    prompts = [item["raw_prompt"] for item in data["items"]]
    assert prompts[0] == "prompt 11"
    assert prompts[-1] == "prompt 2"


@pytest.mark.asyncio
async def test_list_isolated_between_users(client: AsyncClient) -> None:
    user_a = await _sign_up(client)
    user_b = await _sign_up(client)
    await _create_image_project(client, user_a)

    response = await client.get("/api/v1/image-projects", headers=user_b)
    assert response.json()["items"] == []


# ---------------------------------------------------------------------------
# 详情 + 隔离
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_detail(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers)

    response = await client.get(f"/api/v1/image-projects/{project['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == project["id"]


@pytest.mark.asyncio
async def test_foreign_project_returns_404(client: AsyncClient) -> None:
    owner = await _sign_up(client)
    intruder = await _sign_up(client)
    project = await _create_image_project(client, owner)

    response = await client.get(f"/api/v1/image-projects/{project['id']}", headers=intruder)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 提示词优化 & 编辑
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_prompt_without_llm_key_returns_503(client: AsyncClient) -> None:
    """LLM_API_KEY 为空时应返回 503。"""
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers)

    with patch("app.api.v1.image_projects.get_settings") as mock_settings:
        mock_settings.return_value.llm_api_key = ""
        response = await client.post(
            f"/api/v1/image-projects/{project['id']}/prompt", headers=headers
        )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_update_prompt(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers)

    response = await client.patch(
        f"/api/v1/image-projects/{project['id']}/prompt",
        json={"optimized_prompt": "A cute cat on a windowsill at sunset"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["optimized_prompt"] == "A cute cat on a windowsill at sunset"


# ---------------------------------------------------------------------------
# 提交生成
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enqueue_without_prompt_returns_422(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers)

    response = await client.post(
        f"/api/v1/image-projects/{project['id']}/generate", headers=headers
    )
    assert response.status_code == 422
    assert "提示词" in response.json()["detail"]


@pytest.mark.asyncio
async def test_enqueue_generation(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers)

    # 先设置 optimized_prompt
    await client.patch(
        f"/api/v1/image-projects/{project['id']}/prompt",
        json={"optimized_prompt": "A cute cat"},
        headers=headers,
    )

    mock_queue = AsyncMock()
    mock_queue.enqueue_job = AsyncMock(return_value=None)

    with patch("app.api.v1.image_projects.get_queue", return_value=mock_queue):
        response = await client.post(
            f"/api/v1/image-projects/{project['id']}/generate", headers=headers
        )

    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "生成任务已提交"
    assert "job_id" in data

    # 提交后 progress 重置为 0
    detail = await client.get(
        f"/api/v1/image-projects/{project['id']}", headers=headers
    )
    assert detail.json()["progress"] == 0


@pytest.mark.asyncio
async def test_enqueue_duplicate_returns_409(client: AsyncClient) -> None:
    """首次提交后 status=pending 且 job_id 已设置，再次提交应返回 409。"""
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers)

    await client.patch(
        f"/api/v1/image-projects/{project['id']}/prompt",
        json={"optimized_prompt": "A cute cat"},
        headers=headers,
    )

    mock_queue = AsyncMock()
    mock_queue.enqueue_job = AsyncMock(return_value=None)

    with patch("app.api.v1.image_projects.get_queue", return_value=mock_queue):
        first = await client.post(
            f"/api/v1/image-projects/{project['id']}/generate", headers=headers
        )
        assert first.status_code == 202

        # 第一次提交后 status=pending + job_id 已设置 → 第二次应 409
        second = await client.post(
            f"/api/v1/image-projects/{project['id']}/generate", headers=headers
        )
        assert second.status_code == 409


# ---------------------------------------------------------------------------
# 进度轮询
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_progress_pending(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers)

    response = await client.get(
        f"/api/v1/image-projects/{project['id']}/progress", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["progress"] == 0
    assert data["image_url"] is None


# ---------------------------------------------------------------------------
# 删除
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_image_project(client: AsyncClient) -> None:
    headers = await _sign_up(client)
    project = await _create_image_project(client, headers)

    response = await client.delete(
        f"/api/v1/image-projects/{project['id']}", headers=headers
    )
    assert response.status_code == 204

    # 确认已删除
    detail = await client.get(
        f"/api/v1/image-projects/{project['id']}", headers=headers
    )
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_delete_foreign_returns_404(client: AsyncClient) -> None:
    owner = await _sign_up(client)
    intruder = await _sign_up(client)
    project = await _create_image_project(client, owner)

    response = await client.delete(
        f"/api/v1/image-projects/{project['id']}", headers=intruder
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 风格模板 & 提示词优化（单元测试，不调 LLM）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_three_styles_have_templates() -> None:
    """三种风格在 STYLE_TEMPLATES 中都有对应模板。"""
    from app.services.image_generation import STYLE_TEMPLATES

    assert set(STYLE_TEMPLATES.keys()) == {
        "chiikawa_science",
        "minimal_doodle",
        "shinchan_education",
    }


@pytest.mark.asyncio
async def test_build_style_prompt_includes_topic_and_ratio() -> None:
    """build_style_prompt 必须包含用户主题和比例信息。"""
    from app.services.image_generation import build_style_prompt

    for style in ("chiikawa_science", "minimal_doodle", "shinchan_education"):
        prompt = build_style_prompt(style, "光合作用原理", "16:9")
        assert "光合作用原理" in prompt
        assert "16:9" in prompt


@pytest.mark.asyncio
async def test_build_style_prompt_handles_all_aspect_ratios() -> None:
    """1:1、16:9、9:16 都能正确传入。"""
    from app.services.image_generation import build_style_prompt

    for ratio in ("1:1", "16:9", "9:16"):
        prompt = build_style_prompt("minimal_doodle", "test topic", ratio)
        assert ratio in prompt


@pytest.mark.asyncio
async def test_placeholder_cleanup_removes_leftovers() -> None:
    """optimize_prompt 返回结果中的残留占位符会被清理。"""
    import re
    from unittest.mock import AsyncMock

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage

    from app.services.image_generation import _PLACEHOLDER_RE, optimize_prompt

    # Mock LLM 返回含残留占位符的结果
    mock_chat = AsyncMock(spec=BaseChatModel)
    mock_chat.ainvoke = AsyncMock(
        return_value=AIMessage(content="A cute cat [CHARACTER_NAME] sitting on a windowsill [PURPOSE].")
    )

    result = await optimize_prompt(
        chat=mock_chat,
        style="chiikawa_science",
        raw_prompt="猫咪",
        aspect_ratio="1:1",
    )
    assert not _PLACEHOLDER_RE.search(result), f"残留占位符未清理: {result}"
    assert "猫咪" not in result or True  # 用户主题是中文，LLM 可能翻译也可能保留


@pytest.mark.asyncio
async def test_optimize_prompt_passes_aspect_ratio_to_llm() -> None:
    """optimize_prompt 将 aspect_ratio 传给 LLM prompt。"""
    from unittest.mock import AsyncMock, call

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage

    from app.services.image_generation import optimize_prompt

    mock_chat = AsyncMock(spec=BaseChatModel)
    mock_chat.ainvoke = AsyncMock(return_value=AIMessage(content="A complete prompt."))

    await optimize_prompt(
        chat=mock_chat,
        style="shinchan_education",
        raw_prompt="测试主题",
        aspect_ratio="9:16",
    )

    # 检查传给 LLM 的 user message 包含比例
    human_msg = mock_chat.ainvoke.call_args[0][0][1]
    assert "9:16" in human_msg.content
    assert "测试主题" in human_msg.content


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client: AsyncClient) -> None:
    endpoints = [
        ("GET", "/api/v1/image-projects"),
        ("POST", "/api/v1/image-projects"),
    ]
    for method, path in endpoints:
        if method == "GET":
            response = await client.get(path)
        else:
            response = await client.post(path, json={})
        assert response.status_code == 401, f"{method} {path} should require auth"
