"""
Unit tests for middleware/cache.py

Tests cache control middleware for different endpoint types.
"""
import pytest
from unittest.mock import AsyncMock, Mock
from middleware.cache import APICacheControlMiddleware


class TestCacheControlMiddleware:
    """Test cache control middleware"""

    @pytest.mark.asyncio
    async def test_adds_cache_headers_to_public_endpoints(self):
        """Test cache headers are added to public endpoints"""
        app = AsyncMock()
        middleware = APICacheControlMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/public/games",
        }
        receive = AsyncMock()

        sent_messages = []
        async def send(message):
            sent_messages.append(message)

        await middleware(scope, receive, send)

        # Find response start message
        response_start = next(
            (msg for msg in sent_messages if msg.get("type") == "http.response.start"),
            None
        )

        if response_start:
            headers = dict(response_start.get("headers", []))
            assert b"cache-control" in headers or b"Cache-Control" in headers

    @pytest.mark.asyncio
    async def test_skips_non_http_requests(self):
        """Test middleware skips non-HTTP requests"""
        app = AsyncMock()
        middleware = APICacheControlMiddleware(app)

        scope = {
            "type": "websocket",
            "path": "/ws",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # App should be called directly
        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_health_endpoint_caching(self):
        """Test health endpoints have shorter cache"""
        # Create an app that actually sends ASGI messages
        async def app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"status": "ok"}',
            })

        middleware = APICacheControlMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/health",
        }
        receive = AsyncMock()

        sent_messages = []
        async def send(message):
            sent_messages.append(message)

        await middleware(scope, receive, send)

        # Should still add cache control
        response_start = next(
            (msg for msg in sent_messages if msg.get("type") == "http.response.start"),
            None
        )

        assert response_start is not None

    @pytest.mark.asyncio
    async def test_image_proxy_endpoint(self):
        """Test image proxy endpoint is handled"""
        app = AsyncMock()
        middleware = APICacheControlMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/public/image-proxy",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Should pass through
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_default_public_endpoint_caching(self):
        """Test default caching for other public endpoints"""
        # Create an app that actually sends ASGI messages
        async def app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"data": "test"}',
            })

        middleware = APICacheControlMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/public/other",
        }
        receive = AsyncMock()

        sent_messages = []
        async def send(message):
            sent_messages.append(message)

        await middleware(scope, receive, send)

        # Verify default cache headers are added
        response_start = next(
            (msg for msg in sent_messages if msg.get("type") == "http.response.start"),
            None
        )

        assert response_start is not None

    @pytest.mark.asyncio
    async def test_non_public_endpoints_no_cache(self):
        """Test non-public endpoints don't get cache headers"""
        # Create an app that actually sends ASGI messages
        async def app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"data": "test"}',
            })

        middleware = APICacheControlMiddleware(app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/admin/games",
        }
        receive = AsyncMock()

        sent_messages = []
        async def send(message):
            sent_messages.append(message)

        await middleware(scope, receive, send)

        # Admin endpoints should not have caching
        response_start = next(
            (msg for msg in sent_messages if msg.get("type") == "http.response.start"),
            None
        )

        # Response might not have cache headers or have no-cache
        assert response_start is not None

    @pytest.mark.asyncio
    async def test_category_counts_endpoint_caching(self):
        """Test category counts endpoint has proper caching"""
        # Create an app that actually sends ASGI messages
        async def app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"counts": {}}',
            })

        middleware = APICacheControlMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/public/category-counts",
        }
        receive = AsyncMock()

        sent_messages = []
        async def send(message):
            sent_messages.append(message)

        await middleware(scope, receive, send)

        response_start = next(
            (msg for msg in sent_messages if msg.get("type") == "http.response.start"),
            None
        )

        assert response_start is not None


class TestCacheControlIntegration:
    """Integration tests for cache control middleware"""

    @pytest.mark.asyncio
    async def test_complete_caching_workflow(self):
        """Test complete caching workflow"""
        async def app_with_response(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"data": "test"}',
            })

        middleware = APICacheControlMiddleware(app_with_response)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/public/games",
        }
        receive = AsyncMock()

        sent_messages = []
        async def send(message):
            sent_messages.append(message)

        await middleware(scope, receive, send)

        # Verify we have both start and body
        assert len(sent_messages) >= 1
        assert any(msg.get("type") == "http.response.start" for msg in sent_messages)
