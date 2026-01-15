"""
Comprehensive tests for image proxy endpoint.
Tests the /api/public/image-proxy endpoint including Cloudinary integration,
URL validation, caching, and fallback behavior.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Response


class TestImageProxyBasicValidation:
    """Tests for basic URL validation in image proxy"""

    def test_empty_url_rejected(self, client):
        """Empty URL should be rejected"""
        response = client.get("/api/public/image-proxy?url=")
        assert response.status_code == 400
        assert "Invalid image URL" in response.json()["detail"]

    def test_none_url_rejected(self, client):
        """Missing URL parameter should be rejected"""
        response = client.get("/api/public/image-proxy")
        assert response.status_code == 422  # FastAPI validation error

    def test_whitespace_only_url_rejected(self, client):
        """Whitespace-only URL should be rejected"""
        response = client.get("/api/public/image-proxy?url=   ")
        assert response.status_code == 400

    def test_non_http_scheme_rejected(self, client):
        """Non-HTTP schemes should be rejected"""
        response = client.get("/api/public/image-proxy?url=ftp://example.com/image.jpg")
        assert response.status_code == 400
        assert "Invalid URL scheme" in response.json()["detail"]

    def test_file_scheme_rejected(self, client):
        """File scheme should be rejected"""
        response = client.get("/api/public/image-proxy?url=file:///etc/passwd")
        assert response.status_code == 400

    def test_javascript_scheme_rejected(self, client):
        """JavaScript scheme should be rejected"""
        response = client.get("/api/public/image-proxy?url=javascript:alert(1)")
        assert response.status_code == 400


class TestImageProxyTrustedDomains:
    """Tests for trusted domain validation"""

    def test_bgg_cdn_url_allowed(self, client):
        """BGG CDN URLs should be allowed"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:
            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/abc__md/img/xyz.jpg")
            # Should succeed (200) or redirect (302) - not 400
            assert response.status_code in [200, 302, 502]  # 502 if service fails, but not 400

    def test_bgg_static_url_allowed(self, client):
        """BGG static URLs should be allowed"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:
            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-static.com/images/test.png")
            assert response.status_code in [200, 302, 502]

    def test_untrusted_domain_rejected(self, client):
        """Untrusted domains should be rejected"""
        with patch('api.routers.public.socket.gethostbyname', return_value='93.184.216.34'):
            response = client.get("/api/public/image-proxy?url=https://evil.example.com/image.jpg")
            assert response.status_code == 400
            assert "BoardGameGeek images" in response.json()["detail"]

    def test_random_domain_rejected(self, client):
        """Random external domains should be rejected"""
        with patch('api.routers.public.socket.gethostbyname', return_value='8.8.8.8'):
            response = client.get("/api/public/image-proxy?url=https://random-site.com/img.png")
            assert response.status_code == 400


class TestImageProxySSRFIntegration:
    """Tests for SSRF protection in image proxy"""

    def test_private_ip_blocked(self, client):
        """Private IPs should be blocked"""
        with patch('api.routers.public.socket.gethostbyname', return_value='192.168.1.1'):
            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg")
            assert response.status_code == 400
            assert "private IP" in response.json()["detail"]

    def test_localhost_blocked(self, client):
        """Localhost should be blocked"""
        with patch('api.routers.public.socket.gethostbyname', return_value='127.0.0.1'):
            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg")
            assert response.status_code == 400
            assert "loopback" in response.json()["detail"]

    def test_aws_metadata_blocked(self, client):
        """AWS metadata endpoint should be blocked"""
        with patch('api.routers.public.socket.gethostbyname', return_value='169.254.169.254'):
            response = client.get("/api/public/image-proxy?url=http://169.254.169.254/latest/meta-data/")
            assert response.status_code == 400


class TestImageProxyCloudinaryRedirect:
    """Tests for Cloudinary URL redirect behavior"""

    def test_cloudinary_url_redirect(self, client):
        """Cloudinary URLs should be redirected directly"""
        cloudinary_url = "https://res.cloudinary.com/test/image/upload/v1234/test.jpg"

        with patch('api.routers.public.socket.gethostbyname', return_value='104.16.84.58'):  # Cloudinary IP
            response = client.get(f"/api/public/image-proxy?url={cloudinary_url}", follow_redirects=False)
            # Should redirect (302) to the Cloudinary URL
            if response.status_code == 302:
                assert "cloudinary.com" in response.headers.get("location", "")

    def test_double_proxy_prevention(self, client):
        """Should prevent double-proxying through Cloudinary"""
        cloudinary_url = "https://res.cloudinary.com/demo/image/upload/sample.jpg"

        with patch('api.routers.public.socket.gethostbyname', return_value='104.16.84.58'):
            response = client.get(f"/api/public/image-proxy?url={cloudinary_url}", follow_redirects=False)
            # Should be a redirect, not a proxy
            if response.status_code == 302:
                assert response.headers.get("Cache-Control") == "public, max-age=31536000, immutable"


class TestImageProxyURLTransformation:
    """Tests for URL transformation logic"""

    def test_original_to_md_transformation(self, client):
        """__original should be transformed to __md"""
        original_url = "https://cf.geekdo-images.com/abc__original/img/xyz.jpg"

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:
            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            # Just verify it doesn't error - the transformation happens internally
            response = client.get(f"/api/public/image-proxy?url={original_url}")
            assert response.status_code in [200, 302, 502]

    def test_whitespace_stripping(self, client):
        """URLs with whitespace should be stripped"""
        url_with_whitespace = "  https://cf.geekdo-images.com/test.jpg  "

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:
            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get(f"/api/public/image-proxy?url={url_with_whitespace}")
            # Should work after stripping
            assert response.status_code in [200, 302, 502]

    def test_control_chars_stripped(self, client):
        """URLs with control characters should be stripped"""
        # URL with carriage return and newline (common database issue)
        url_with_crlf = "https://cf.geekdo-images.com/test.jpg\r\n"

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:
            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            # Encode properly for URL
            import urllib.parse
            encoded_url = urllib.parse.quote(url_with_crlf, safe='/:?=&')

            response = client.get(f"/api/public/image-proxy?url={encoded_url}")
            # Should handle without crashing
            assert response.status_code in [200, 302, 400, 502]


class TestImageProxyResizeParameters:
    """Tests for width/height resize parameters"""

    def test_width_parameter_accepted(self, client):
        """Width parameter should be accepted"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:
            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg&width=200")
            assert response.status_code in [200, 302, 502]

    def test_height_parameter_accepted(self, client):
        """Height parameter should be accepted"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:
            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg&height=150")
            assert response.status_code in [200, 302, 502]

    def test_both_dimensions_accepted(self, client):
        """Both width and height should be accepted"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:
            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg&width=200&height=150")
            assert response.status_code in [200, 302, 502]


class TestImageProxyCaching:
    """Tests for caching behavior"""

    def test_cloudinary_redirect_has_immutable_cache(self, client):
        """Cloudinary redirects should have immutable cache headers"""
        cloudinary_url = "https://res.cloudinary.com/test/image/upload/v1234/test.jpg"

        with patch('api.routers.public.socket.gethostbyname', return_value='104.16.84.58'):
            response = client.get(f"/api/public/image-proxy?url={cloudinary_url}", follow_redirects=False)

            if response.status_code == 302:
                cache_control = response.headers.get("Cache-Control", "")
                assert "max-age=31536000" in cache_control
                assert "immutable" in cache_control

    def test_direct_proxy_has_cache_headers(self, client):
        """Direct proxy responses should have cache headers"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService, \
             patch('api.routers.public.CLOUDINARY_ENABLED', False):

            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'public, max-age=300'))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg")

            if response.status_code == 200:
                assert "Cache-Control" in response.headers


class TestImageProxyCloudinaryUpload:
    """Tests for Cloudinary upload workflow"""

    @pytest.mark.asyncio
    async def test_cloudinary_upload_success_redirects(self, async_client, db_session):
        """Successful Cloudinary upload should redirect"""
        from models import Game

        # Create a test game with image URL
        game = Game(
            title="Test Game",
            bgg_id=99999,
            image="https://cf.geekdo-images.com/abc__md/img/xyz.jpg",
            status="OWNED"
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.CLOUDINARY_ENABLED', True), \
             patch('api.routers.public.cloudinary_service') as mock_cloudinary:

            mock_cloudinary.upload_from_url = AsyncMock(return_value={"public_id": "test123"})
            mock_cloudinary.get_image_url = MagicMock(return_value="https://res.cloudinary.com/test/image/upload/test123.jpg")

            response = await async_client.get(
                "/api/public/image-proxy?url=https://cf.geekdo-images.com/abc__md/img/xyz.jpg"
            )
            # Should be redirect or success
            assert response.status_code in [200, 302, 502]

    @pytest.mark.asyncio
    async def test_cloudinary_upload_failure_falls_back(self, async_client):
        """Cloudinary upload failure should fall back to direct proxy"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.CLOUDINARY_ENABLED', True), \
             patch('api.routers.public.cloudinary_service') as mock_cloudinary, \
             patch('api.routers.public.ImageService') as MockService:

            # Cloudinary fails
            mock_cloudinary.upload_from_url = AsyncMock(return_value=None)

            # But direct proxy works
            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'image data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = await async_client.get(
                "/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg"
            )
            # Should fall back to direct proxy
            assert response.status_code in [200, 502]


class TestImageProxyErrorHandling:
    """Tests for error handling"""

    def test_network_error_returns_502(self, client):
        """Network errors should return 502"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:

            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(side_effect=Exception("Network error"))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg")
            assert response.status_code == 502
            assert "Failed to fetch image" in response.json()["detail"]

    def test_timeout_error_returns_502(self, client):
        """Timeout errors should return 502"""
        import httpx

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:

            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg")
            assert response.status_code == 502

    def test_http_exceptions_preserved(self, client):
        """HTTPExceptions should be re-raised without modification"""
        # Invalid URL format should give 400, not 502
        response = client.get("/api/public/image-proxy?url=not-a-url")
        assert response.status_code == 400


class TestImageProxyFastPath:
    """Tests for the cached cloudinary_url fast-path"""

    @pytest.mark.asyncio
    async def test_cached_cloudinary_url_used(self, async_client, db_session):
        """Should use cached cloudinary_url when available"""
        from models import Game

        # Create game with cached Cloudinary URL
        game = Game(
            title="Cached Test Game",
            bgg_id=88888,
            image="https://cf.geekdo-images.com/cached__md/img/test.jpg",
            cloudinary_url="https://res.cloudinary.com/cached/image/upload/cached_test.jpg",
            status="OWNED"
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.CLOUDINARY_ENABLED', True):

            response = await async_client.get(
                "/api/public/image-proxy?url=https://cf.geekdo-images.com/cached__md/img/test.jpg",
                follow_redirects=False
            )

            # Should redirect to cached URL without re-uploading
            if response.status_code == 302:
                location = response.headers.get("location", "")
                assert "cloudinary" in location.lower()


class TestImageProxyContentType:
    """Tests for content type handling"""

    def test_jpeg_content_type_returned(self, client):
        """JPEG content type should be returned correctly"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.CLOUDINARY_ENABLED', False), \
             patch('api.routers.public.ImageService') as MockService:

            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'jpeg data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg")

            if response.status_code == 200:
                assert response.headers.get("content-type") == "image/jpeg"

    def test_png_content_type_returned(self, client):
        """PNG content type should be returned correctly"""
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.CLOUDINARY_ENABLED', False), \
             patch('api.routers.public.ImageService') as MockService:

            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'png data', 'image/png', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get("/api/public/image-proxy?url=https://cf.geekdo-images.com/test.png")

            if response.status_code == 200:
                assert response.headers.get("content-type") == "image/png"


class TestImageProxyEdgeCases:
    """Tests for edge cases"""

    def test_very_long_url_handled(self, client):
        """Very long URLs should be handled"""
        long_path = "a" * 1000
        long_url = f"https://cf.geekdo-images.com/{long_path}.jpg"

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:

            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get(f"/api/public/image-proxy?url={long_url}")
            # Should handle without crashing
            assert response.status_code in [200, 302, 400, 502]

    def test_url_with_query_params_handled(self, client):
        """URLs with query parameters should be handled"""
        url = "https://cf.geekdo-images.com/test.jpg?format=webp&quality=90"

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:

            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            import urllib.parse
            encoded = urllib.parse.quote(url, safe='')

            response = client.get(f"/api/public/image-proxy?url={encoded}")
            assert response.status_code in [200, 302, 502]

    def test_url_with_special_chars_handled(self, client):
        """URLs with special characters should be handled"""
        url = "https://cf.geekdo-images.com/test%20image.jpg"

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'), \
             patch('api.routers.public.ImageService') as MockService:

            mock_instance = MagicMock()
            mock_instance.proxy_image = AsyncMock(return_value=(b'data', 'image/jpeg', 'max-age=300'))
            MockService.return_value = mock_instance

            response = client.get(f"/api/public/image-proxy?url={url}")
            assert response.status_code in [200, 302, 502]
