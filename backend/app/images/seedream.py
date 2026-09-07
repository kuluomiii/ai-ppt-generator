from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SeedreamClient:
    """火山方舟 Seedream 图片生成客户端。

    Seedream 的官方示例使用 /images/generations；将供应商细节隔离在此处，
    业务层只需要拿到生成图片的 URL。
    """

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 120,
    ) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds

    async def generate(self, prompt: str, aspect_ratio: str) -> str:
        if not self._api_key.strip():
            raise ValueError("未配置 SEEDREAM_API_KEY，无法生成图片")

        response = await self._http_client.post(
            f"{self._base_url}/images/generations",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "prompt": prompt,
                "size": _size_for_ratio(aspect_ratio),
                "response_format": "url",
                "watermark": False,
            },
            timeout=self._timeout,
        )
        if response.status_code >= 400:
            # 把上游返回的错误体记录下来，方便排查（默认 raise_for_status 只给通用文案）
            logger.warning(
                "Seedream API error %s for prompt=%r aspect_ratio=%s size=%s body=%s",
                response.status_code,
                (prompt[:80] + "...") if len(prompt) > 80 else prompt,
                aspect_ratio,
                _size_for_ratio(aspect_ratio),
                response.text[:1500],
            )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        try:
            url = payload["data"][0]["url"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("Seedream 返回结果中没有图片地址") from error
        if not isinstance(url, str) or not url:
            raise RuntimeError("Seedream 返回了无效图片地址")
        return url

    async def aclose(self) -> None:
        await self._http_client.aclose()


def _size_for_ratio(aspect_ratio: str) -> str:
    sizes = {"1:1": "2K", "16:9": "2560x1440", "9:16": "1440x2560"}
    try:
        return sizes[aspect_ratio]
    except KeyError as error:
        raise ValueError("aspect_ratio 必须是 1:1、16:9 或 9:16") from error
