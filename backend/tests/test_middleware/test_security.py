"""
Unit tests for middleware/security.py

Tests security headers middleware including X-Frame-Options, X-Content-Type-Options,
HSTS, CSP, and other security headers.
"""
import pytest
from unittest.mock import AsyncMock
from middleware.security import SecurityHeadersMiddleware


async def simple_app(scope, receive, send):
    """Simple ASGI app that sends a basic HTTP response"""
    await send({"type": "http.response.start", "status": 200})


class TestSecurityHeadersMiddleware:
    """Test security headers middleware"""

    @pytest.mark.asyncio
    async def test_adds_x_frame_options_header(self):
        """Test middleware adds X-Frame-Options: DENY header"""
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/api/test",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # Verify X-Frame-Options header was added
        assert len(headers_sent) > 0
        assert b"x-frame-options" in headers_sent[0]
        assert headers_sent[0][b"x-frame-options"] == b"DENY"

    @pytest.mark.asyncio
    async def test_adds_x_content_type_options_header(self):
        """Test middleware adds X-Content-Type-Options: nosniff header"""
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/api/test",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # Verify X-Content-Type-Options header was added
        assert b"x-content-type-options" in headers_sent[0]
        assert headers_sent[0][b"x-content-type-options"] == b"nosniff"

    @pytest.mark.asyncio
    async def test_adds_hsts_header(self):
        """Test middleware adds Strict-Transport-Security header"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/api/test",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # Verify HSTS header was added
        assert b"strict-transport-security" in headers_sent[0]
        assert b"max-age=31536000" in headers_sent[0][b"strict-transport-security"]
        assert b"includeSubDomains" in headers_sent[0][b"strict-transport-security"]

    @pytest.mark.asyncio
    async def test_adds_referrer_policy_header(self):
        """Test middleware adds Referrer-Policy header"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/api/test",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # Verify Referrer-Policy header was added
        assert b"referrer-policy" in headers_sent[0]
        assert headers_sent[0][b"referrer-policy"] == b"strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_adds_permissions_policy_header(self):
        """Test middleware adds Permissions-Policy header"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/api/test",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # Verify Permissions-Policy header was added
        assert b"permissions-policy" in headers_sent[0]
        permissions = headers_sent[0][b"permissions-policy"].decode()
        assert "geolocation=()" in permissions
        assert "microphone=()" in permissions
        assert "camera=()" in permissions
        assert "payment=()" in permissions
        assert "usb=()" in permissions

    @pytest.mark.asyncio
    async def test_api_endpoint_no_xss_protection(self):
        """Test API endpoints do not get X-XSS-Protection header"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/api/public/games",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # API endpoints should NOT have X-XSS-Protection
        assert b"x-xss-protection" not in headers_sent[0]

    @pytest.mark.asyncio
    async def test_api_endpoint_no_csp(self):
        """Test API endpoints do not get Content-Security-Policy header"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/api/admin/games",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # API endpoints should NOT have CSP
        assert b"content-security-policy" not in headers_sent[0]

    @pytest.mark.asyncio
    async def test_non_api_endpoint_has_xss_protection(self):
        """Test non-API endpoints get X-XSS-Protection header"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/index.html",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # Non-API endpoints should have X-XSS-Protection
        assert b"x-xss-protection" in headers_sent[0]
        assert headers_sent[0][b"x-xss-protection"] == b"1; mode=block"

    @pytest.mark.asyncio
    async def test_non_api_endpoint_has_csp(self):
        """Test non-API endpoints get Content-Security-Policy header"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # Non-API endpoints should have CSP
        assert b"content-security-policy" in headers_sent[0]
        csp = headers_sent[0][b"content-security-policy"].decode()
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    @pytest.mark.asyncio
    async def test_csp_allows_bgg_images(self):
        """Test CSP policy allows BoardGameGeek images"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/games",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # CSP should allow BGG images
        csp = headers_sent[0][b"content-security-policy"].decode()
        assert "cf.geekdo-images.com" in csp
        assert "cf.geekdo-static.com" in csp

    @pytest.mark.asyncio
    async def test_skips_non_http_requests(self):
        """Test middleware skips non-HTTP requests"""
        app_mock = AsyncMock()
        middleware = SecurityHeadersMiddleware(app_mock)

        scope = {
            "type": "websocket",
            "path": "/ws",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # App should be called directly without header manipulation
        app_mock.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_does_not_override_existing_headers(self):
        """Test middleware does not override existing security headers"""
        async def app_with_headers(scope, receive, send):
            await send({
                "type": "http.response.start",
                "headers": [
                    (b"x-frame-options", b"SAMEORIGIN"),
                    (b"x-content-type-options", b"custom-value"),
                ]
            })

        middleware = SecurityHeadersMiddleware(app_with_headers)

        scope = {
            "type": "http",
            "path": "/api/test",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # Existing headers should not be overridden
        assert headers_sent[0][b"x-frame-options"] == b"SAMEORIGIN"
        assert headers_sent[0][b"x-content-type-options"] == b"custom-value"

    @pytest.mark.asyncio
    async def test_handles_response_without_headers(self):
        """Test middleware handles response messages without headers"""
        async def app_no_headers(scope, receive, send):
            await send({"type": "http.response.start"})

        middleware = SecurityHeadersMiddleware(app_no_headers)

        scope = {
            "type": "http",
            "path": "/api/test",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # Should add headers even when none existed
        assert b"x-frame-options" in headers_sent[0]
        assert b"x-content-type-options" in headers_sent[0]

    @pytest.mark.asyncio
    async def test_handles_missing_path(self):
        """Test middleware handles scope without path gracefully"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            # No path
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        # Should not crash
        await middleware(scope, receive, capture_send)

        # Should still add headers (treats as non-API)
        assert b"x-frame-options" in headers_sent[0]

    @pytest.mark.asyncio
    async def test_only_modifies_response_start(self):
        """Test middleware only modifies http.response.start messages"""
        async def app_with_body(scope, receive, send):
            await send({"type": "http.response.start"})
            await send({"type": "http.response.body", "body": b"test"})

        middleware = SecurityHeadersMiddleware(app_with_body)

        scope = {
            "type": "http",
            "path": "/api/test",
        }
        receive = AsyncMock()

        messages_sent = []
        async def capture_send(message):
            messages_sent.append(message)

        await middleware(scope, receive, capture_send)

        # Should have 2 messages
        assert len(messages_sent) == 2
        # First should be modified
        assert "headers" in messages_sent[0]
        # Second should be unmodified
        assert messages_sent[1]["type"] == "http.response.body"
        assert messages_sent[1]["body"] == b"test"


class TestSecurityHeadersIntegration:
    """Integration tests for security headers middleware"""

    @pytest.mark.asyncio
    async def test_all_required_headers_present_for_api(self):
        """Test all required security headers are present for API endpoints"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/api/public/games",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        headers = headers_sent[0]

        # Required headers for API endpoints
        assert b"x-frame-options" in headers
        assert b"x-content-type-options" in headers
        assert b"strict-transport-security" in headers
        assert b"referrer-policy" in headers
        assert b"permissions-policy" in headers

        # Should NOT have these for API
        assert b"x-xss-protection" not in headers
        assert b"content-security-policy" not in headers

    @pytest.mark.asyncio
    async def test_all_required_headers_present_for_html(self):
        """Test all required security headers are present for HTML pages"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/index.html",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        headers = headers_sent[0]

        # All headers for HTML pages
        assert b"x-frame-options" in headers
        assert b"x-content-type-options" in headers
        assert b"strict-transport-security" in headers
        assert b"referrer-policy" in headers
        assert b"permissions-policy" in headers
        assert b"x-xss-protection" in headers
        assert b"content-security-policy" in headers

    @pytest.mark.asyncio
    async def test_various_api_paths_detected_correctly(self):
        """Test various /api/* paths are correctly identified"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        api_paths = [
            "/api/health",
            "/api/public/games",
            "/api/admin/login",
            "/api/admin/games/123",
        ]

        for path in api_paths:
            scope = {
                "type": "http",
                "path": path,
            }
            receive = AsyncMock()

            headers_sent = []
            async def capture_send(message):
                if message["type"] == "http.response.start":
                    headers_sent.append(dict(message.get("headers", [])))

            await middleware(scope, receive, capture_send)

            # All should be detected as API endpoints
            assert b"content-security-policy" not in headers_sent[0], \
                f"Path {path} should be detected as API endpoint"

    @pytest.mark.asyncio
    async def test_header_values_are_bytes(self):
        """Test all header values are properly encoded as bytes"""
        # app = AsyncMock()
        middleware = SecurityHeadersMiddleware(simple_app)

        scope = {
            "type": "http",
            "path": "/index.html",
        }
        receive = AsyncMock()

        headers_sent = []
        async def capture_send(message):
            if message["type"] == "http.response.start":
                headers_sent.append(dict(message.get("headers", [])))

        await middleware(scope, receive, capture_send)

        # All header names and values should be bytes
        for name, value in headers_sent[0].items():
            assert isinstance(name, bytes), f"Header name {name} should be bytes"
            assert isinstance(value, bytes), f"Header value for {name} should be bytes"

    @pytest.mark.asyncio
    async def test_complete_request_lifecycle(self):
        """Test middleware works with complete request/response lifecycle"""
        async def complete_app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")]
            })
            await send({
                "type": "http.response.body",
                "body": b'{"status": "ok"}'
            })

        middleware = SecurityHeadersMiddleware(complete_app)

        scope = {
            "type": "http",
            "path": "/api/test",
        }
        receive = AsyncMock()

        messages = []
        async def capture_send(message):
            messages.append(message)

        await middleware(scope, receive, capture_send)

        # Should have both start and body
        assert len(messages) == 2
        assert messages[0]["type"] == "http.response.start"
        assert messages[1]["type"] == "http.response.body"

        # First message should have security headers
        headers = dict(messages[0]["headers"])
        assert b"x-frame-options" in headers

        # Original header should be preserved
        assert b"content-type" in headers
        assert headers[b"content-type"] == b"application/json"
