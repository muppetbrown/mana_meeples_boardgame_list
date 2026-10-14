"""SSRF hardening for ImageService.proxy_image / build_trusted_image_url."""
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from services.image_service import (
    ImageService,
    UntrustedImageURLError,
    build_trusted_image_url,
)

BGG_URL = "https://cf.geekdo-images.com/HASH__md/img/abc=/fit-in/900x600/filters:no_upscale()/pic1.jpg"


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/a.png",
        "https://cf.geekdo-images.com@evil.com/a.png",
        "https://evil.com\\@cf.geekdo-images.com/a.png",
        "https://user:pw@cf.geekdo-images.com/a.png",
        "https://cf.geekdo-images.com:8080/a.png",
        "https://cf.geekdo-images.com.evil.com/a.png",
        "https://sub.cf.geekdo-images.com/a.png",
        "http://127.0.0.1/a.png",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "ftp://cf.geekdo-images.com/a.png",
        "https://cf.geekdo-images.com/a b.png",
        "https://cf.geekdo-images.com/a\r\nHost: evil.com",
    ],
)
def test_untrusted_urls_are_rejected(url):
    with pytest.raises(UntrustedImageURLError):
        build_trusted_image_url(url)


def test_bgg_urls_are_rebuilt_from_trusted_origin():
    assert build_trusted_image_url(BGG_URL) == BGG_URL
    assert (
        build_trusted_image_url("http://cf.geekdo-static.com/a.png?x=1")
        == "https://cf.geekdo-static.com/a.png?x=1"
    )


def _response(status, location=None, content=b"img"):
    headers = {"content-type": "image/jpeg"}
    if location:
        headers["location"] = location
    return httpx.Response(status, headers=headers, content=content, request=httpx.Request("GET", BGG_URL))


@pytest.mark.asyncio
async def test_proxy_image_rejects_untrusted_host_without_fetching():
    client = MagicMock()
    client.get = AsyncMock()
    service = ImageService(MagicMock(), http_client=client)

    with pytest.raises(UntrustedImageURLError):
        await service.proxy_image("https://evil.com/a.png")

    client.get.assert_not_called()


@pytest.mark.asyncio
async def test_proxy_image_does_not_auto_follow_redirects():
    client = MagicMock()
    client.get = AsyncMock(return_value=_response(200))
    service = ImageService(MagicMock(), http_client=client)

    content, content_type, _ = await service.proxy_image(BGG_URL)

    assert content == b"img" and content_type == "image/jpeg"
    assert client.get.call_args.kwargs["follow_redirects"] is False


@pytest.mark.asyncio
async def test_proxy_image_blocks_redirect_to_internal_host():
    client = MagicMock()
    client.get = AsyncMock(return_value=_response(302, location="http://169.254.169.254/latest/meta-data/"))
    service = ImageService(MagicMock(), http_client=client)

    with pytest.raises(UntrustedImageURLError):
        await service.proxy_image(BGG_URL)

    assert client.get.call_count == 1


@pytest.mark.asyncio
async def test_proxy_image_follows_redirect_to_trusted_host():
    client = MagicMock()
    client.get = AsyncMock(
        side_effect=[_response(301, location="/other/pic.jpg"), _response(200, content=b"final")]
    )
    service = ImageService(MagicMock(), http_client=client)

    content, _, _ = await service.proxy_image(BGG_URL)

    assert content == b"final"
    assert client.get.call_args.args[0] == "https://cf.geekdo-images.com/other/pic.jpg"


@pytest.mark.asyncio
async def test_proxy_image_gives_up_after_too_many_redirects():
    client = MagicMock()
    client.get = AsyncMock(return_value=_response(302, location="/loop.jpg"))
    service = ImageService(MagicMock(), http_client=client)

    with pytest.raises(httpx.TooManyRedirects):
        await service.proxy_image(BGG_URL)
