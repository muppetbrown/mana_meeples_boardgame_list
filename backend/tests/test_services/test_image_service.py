"""Tests for ImageService business logic layer."""
import pytest
from unittest.mock import Mock, AsyncMock
from urllib.parse import urlparse
import httpx

from services.image_service import ImageService


class TestImageService:
    """Test suite for ImageService"""

    @pytest.mark.asyncio
    async def test_proxy_image_success(self, db_session):
        """Test image proxying with caching"""
        mock_response = Mock()
        mock_response.content = b"proxied image data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        content, content_type, cache_control = await service.proxy_image(
            "https://cf.geekdo-images.com/image.jpg",
            cache_max_age=600
        )

        assert content == b"proxied image data"
        assert content_type == "image/jpeg"
        assert "max-age=600" in cache_control
        assert "public" in cache_control

    @pytest.mark.asyncio
    async def test_proxy_image_default_content_type(self, db_session):
        """Test proxy image with default content type"""
        mock_response = Mock()
        mock_response.content = b"data"
        mock_response.headers = {}  # No content-type header
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        content, content_type, cache_control = await service.proxy_image(
            "https://cf.geekdo-images.com/image.jpg"
        )

        assert content_type == "application/octet-stream"

class TestImageServiceInit:
    """Test ImageService initialization"""

    def test_init_with_custom_client(self, db_session):
        """Test initialization with custom HTTP client"""
        custom_client = AsyncMock()
        service = ImageService(db_session, http_client=custom_client)

        assert service.http_client == custom_client

    def test_init_creates_default_client(self, db_session):
        """Test initialization creates default client if none provided"""
        service = ImageService(db_session)

        assert service.http_client is not None
        assert isinstance(service.http_client, httpx.AsyncClient)

class TestImageFormats:
    """Test handling of different image formats"""

    @pytest.mark.asyncio
    async def test_proxy_image_png_format(self, db_session):
        """Test proxying PNG images"""
        mock_response = Mock()
        mock_response.content = b"PNG data"
        mock_response.headers = {"content-type": "image/png"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://cf.geekdo-images.com/img.png")

        assert content_type == "image/png"

    @pytest.mark.asyncio
    async def test_proxy_image_gif_format(self, db_session):
        """Test proxying GIF images"""
        mock_response = Mock()
        mock_response.content = b"GIF data"
        mock_response.headers = {"content-type": "image/gif"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://cf.geekdo-images.com/img.gif")

        assert content_type == "image/gif"

    @pytest.mark.asyncio
    async def test_proxy_image_webp_format(self, db_session):
        """Test proxying WebP images"""
        mock_response = Mock()
        mock_response.content = b"WebP data"
        mock_response.headers = {"content-type": "image/webp"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://cf.geekdo-images.com/img.webp")

        assert content_type == "image/webp"


class TestImageEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_proxy_image_empty_response(self, db_session):
        """Test proxying image with empty response"""
        mock_response = Mock()
        mock_response.content = b""
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://cf.geekdo-images.com/empty.jpg")

        assert content == b""
        assert content_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_proxy_image_custom_cache_max_age(self, db_session):
        """Test proxy with custom cache max age"""
        mock_response = Mock()
        mock_response.content = b"data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        _, _, cache_control = await service.proxy_image(
            "https://cf.geekdo-images.com/img.jpg",
            cache_max_age=86400
        )

        assert "max-age=86400" in cache_control

    @pytest.mark.asyncio
    async def test_proxy_image_http_error(self, db_session):
        """Test proxy_image raises HTTPError on failure"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Not Found",
            request=Mock(),
            response=Mock(status_code=404)
        ))

        service = ImageService(db_session, http_client=mock_client)

        with pytest.raises(httpx.HTTPStatusError):
            await service.proxy_image("https://cf.geekdo-images.com/missing.jpg")

class TestProxyImageHeaders:
    """Tests for proxy_image HTTP headers"""

    @pytest.mark.asyncio
    async def test_proxy_image_sends_browser_headers(self, db_session):
        """Test that proxy_image sends proper browser headers for BGG"""
        mock_response = Mock()
        mock_response.content = b"image data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        await service.proxy_image("https://cf.geekdo-images.com/test.jpg")

        # Verify headers were passed
        call_args = mock_client.get.call_args
        headers = call_args.kwargs.get('headers', {})

        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]
        assert "Referer" in headers
        _ref_host = urlparse(headers["Referer"]).hostname or ""
        assert _ref_host == "boardgamegeek.com" or _ref_host.endswith(".boardgamegeek.com")
        assert "Accept" in headers
        assert "image" in headers["Accept"]

    @pytest.mark.asyncio
    async def test_proxy_image_avif_format(self, db_session):
        """Test proxying AVIF images"""
        mock_response = Mock()
        mock_response.content = b"AVIF data"
        mock_response.headers = {"content-type": "image/avif"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://cf.geekdo-images.com/img.avif")

        assert content_type == "image/avif"


class TestProxyImageNetworkErrors:
    """Tests for proxy_image network error handling"""

    @pytest.mark.asyncio
    async def test_proxy_image_connection_error(self, db_session):
        """Test proxy_image handles connection errors"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        service = ImageService(db_session, http_client=mock_client)

        with pytest.raises(httpx.ConnectError):
            await service.proxy_image("https://cf.geekdo-images.com/image.jpg")

    @pytest.mark.asyncio
    async def test_proxy_image_timeout(self, db_session):
        """Test proxy_image handles timeout"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

        service = ImageService(db_session, http_client=mock_client)

        with pytest.raises(httpx.TimeoutException):
            await service.proxy_image("https://cf.geekdo-images.com/image.jpg")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
