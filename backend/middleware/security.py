# middleware/security.py
"""
Security headers middleware for defense-in-depth protection.
Adds HTTP security headers to all responses.
"""
import logging
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """
    Add security headers to all HTTP responses.

    Headers added:
    - X-Frame-Options: Prevent clickjacking attacks
    - X-Content-Type-Options: Prevent MIME type sniffing
    - Strict-Transport-Security: Force HTTPS connections
    - Content-Security-Policy: Only added to HTML responses, not API responses
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features

    Note: CSP is only applied to HTML responses.
    API JSON responses do not need CSP and it can cause webhint warnings.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                # Work with headers as a list to avoid interfering with CORS middleware
                headers_list = list(message.get("headers", []))
                headers_dict = dict(headers_list)
                path = scope.get("path", "")

                # Determine if this is an API endpoint (returns JSON)
                is_api_endpoint = path.startswith("/api/")

                # Only add headers that don't already exist
                # This prevents overwriting CORS headers added by CORSMiddleware
                new_headers = []

                # X-Frame-Options: Prevent clickjacking
                # DENY = Never allow framing
                if b"x-frame-options" not in headers_dict:
                    new_headers.append((b"x-frame-options", b"DENY"))

                # X-Content-Type-Options: Prevent MIME type sniffing
                # nosniff = Browsers must respect Content-Type
                if b"x-content-type-options" not in headers_dict:
                    new_headers.append((b"x-content-type-options", b"nosniff"))

                # Strict-Transport-Security (HSTS): Force HTTPS
                # max-age=31536000 = Remember for 1 year
                # includeSubDomains = Apply to all subdomains
                if b"strict-transport-security" not in headers_dict:
                    new_headers.append((
                        b"strict-transport-security",
                        b"max-age=31536000; includeSubDomains"
                    ))

                # X-XSS-Protection: Legacy XSS protection header
                # Note: Deprecated in favor of CSP, but included for compatibility
                # Only added to non-API endpoints (HTML pages)
                if not is_api_endpoint and b"x-xss-protection" not in headers_dict:
                    new_headers.append((b"x-xss-protection", b"1; mode=block"))

                # Content-Security-Policy: Only for HTML pages, not API JSON responses
                # This is a moderate policy that allows same-origin and trusted CDNs
                if not is_api_endpoint and b"content-security-policy" not in headers_dict:
                    csp_policy = "; ".join([
                        "default-src 'self'",
                        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Allow inline scripts for React
                        "style-src 'self' 'unsafe-inline'",  # Allow inline styles for Tailwind
                        "img-src 'self' data: https://cf.geekdo-images.com https://cf.geekdo-static.com",  # BGG images
                        "font-src 'self' data:",
                        "connect-src 'self' https://mana-meeples-boardgame-list.onrender.com",  # API calls
                        "frame-ancestors 'none'",  # Equivalent to X-Frame-Options: DENY
                        "base-uri 'self'",
                        "form-action 'self'",
                    ])
                    new_headers.append((b"content-security-policy", csp_policy.encode()))

                # Referrer-Policy: Control referrer information
                # strict-origin-when-cross-origin = Send full URL for same-origin, only origin for cross-origin
                if b"referrer-policy" not in headers_dict:
                    new_headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))

                # Permissions-Policy: Control browser features
                # Disable potentially risky features
                if b"permissions-policy" not in headers_dict:
                    permissions = ", ".join([
                        "geolocation=()",  # No geolocation
                        "microphone=()",   # No microphone
                        "camera=()",       # No camera
                        "payment=()",      # No payment API
                        "usb=()",          # No USB access
                    ])
                    new_headers.append((b"permissions-policy", permissions.encode()))

                # Append new headers to existing list (preserves CORS headers)
                message["headers"] = headers_list + new_headers

                logger.debug("Security headers added to response")

            await send(message)

        await self.app(scope, receive, send_wrapper)
