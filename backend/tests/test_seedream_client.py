import httpx
import pytest

from app.images.seedream import SeedreamClient


@pytest.mark.asyncio
async def test_seedream_client_posts_prompt_and_returns_image_url() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": [{"url": "https://cdn.example/image.png"}]})

    client = SeedreamClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        base_url="https://ark.example/api/v3",
        api_key="secret",
        model="doubao-seedream-5-0-260128",
    )

    result = await client.generate("一只猫", "1:1")

    assert result == "https://cdn.example/image.png"
    assert requests[0].url.path == "/api/v3/images/generations"
    assert requests[0].headers["Authorization"] == "Bearer secret"
    assert requests[0].content

    await client.aclose()


@pytest.mark.asyncio
async def test_seedream_client_rejects_missing_api_key() -> None:
    client = SeedreamClient(
        http_client=httpx.AsyncClient(),
        base_url="https://ark.example/api/v3",
        api_key="",
        model="model",
    )

    with pytest.raises(ValueError, match="SEEDREAM_API_KEY"):
        await client.generate("一只猫", "1:1")

    await client.aclose()
