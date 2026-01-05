# middleware/csrf_protection.py
"""
CSRF protection middleware for REST API with JWT authentication.

For JWT-based APIs, traditional CSRF tokens are not necessary because:
1. JWTs in Authorization headers are not automatically sent by browsers
2. JavaScript must explicitly add the header
3. Same-origin policy prevents malicious sites from reading tokens

However, we still validate Origin/Referer headers for defense-in-depth.
"""
import logging
from urllib.parse import urlparse
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse
from config import CORS_ORIGINS

logger = logging.getLogger(__name__)


class OriginValidationMiddleware:
    """
    Validates Origin/Referer headers for state-changing requests.

    This provides CSRF protection for JWT-based APIs by ensuring
    that POST/PUT/DELETE/PATCH requests come from allowed origins.

    GET/HEAD/OPTIONS requests are exempt (they should be read-only).
    """

    def __init__(self, app: ASGIApp):
        self.app = app

        # Parse allowed origins from CORS_ORIGINS config
        self.allowed_origins = set()
        if CORS_ORIGINS:
            for origin in CORS_ORIGINS:
                self.allowed_origins.add(origin.rstrip('/'))

        # Always allow localhost for development
        self.allowed_origins.update([
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:5173',
            'http://127.0.0.1:5173',
        ])

        logger.info(f"CSRF protection enabled for origins: {self.allowed_origins}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        # Only validate state-changing requests
        if method in ("POST", "PUT", "DELETE", "PATCH"):
            # Skip validation for non-admin endpoints (public API is read-only)
            if not path.startswith("/api/admin/"):
                await self.app(scope, receive, send)
                return

            # Skip validation for login endpoint (no prior origin)
            if path == "/api/admin/login":
                await self.app(scope, receive, send)
                return

            # Extract Origin or Referer header
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode("utf-8")
            referer = headers.get(b"referer", b"").decode("utf-8")

            request_origin = origin or referer

            if not request_origin:
                logger.warning(
                    f"CSRF validation failed: Missing Origin/Referer header for {method} {path}"
                )
                response = JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Missing Origin or Referer header. CSRF protection requires these headers for state-changing requests."
                    }
                )
                await response(scope, receive, send)
                return

            # Extract origin from referer if needed (referer includes path)
            if referer and not origin:
                parsed = urlparse(referer)
                request_origin = f"{parsed.scheme}://{parsed.netloc}"

            # Normalize origin (remove trailing slash)
            request_origin = request_origin.rstrip('/')

            # Validate against allowed origins
            if request_origin not in self.allowed_origins:
                logger.warning(
                    f"CSRF validation failed: Origin '{request_origin}' not in allowed list for {method} {path}"
                )
                response = JSONResponse(
                    status_code=403,
                    content={
                        "detail": f"Origin '{request_origin}' not allowed. CSRF protection blocks cross-origin state-changing requests."
                    }
                )
                await response(scope, receive, send)
                return

            logger.debug(f"CSRF validation passed: {request_origin} for {method} {path}")

        await self.app(scope, receive, send)
