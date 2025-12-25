# middleware/cache.py
"""
Cache-Control headers middleware for API responses.
Adds appropriate cache headers based on endpoint cacheability.
"""
import logging
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class APICacheControlMiddleware:
    """
    Add Cache-Control headers to API responses based on endpoint type.

    Cache durations:
    - Public game data: 5 minutes (300s) - Data changes infrequently
    - Category counts: 5 minutes (300s) - Aggregated data changes infrequently
    - Health endpoints: 1 minute (60s) - Status changes more frequently
    - Image proxy: Already handled in endpoint (delegates to response)
    - Admin endpoints: No caching (private, no-store)
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                path = scope.get("path", "")

                # Skip if Cache-Control already set (e.g., image-proxy endpoint)
                headers = dict(message.get("headers", []))
                if b"cache-control" in headers:
                    await send(message)
                    return

                # Determine cache duration based on path
                cache_control = None

                if path.startswith("/api/public/"):
                    # Public game data - cache for 5 minutes
                    if (path.startswith("/api/public/games") or
                        path.startswith("/api/public/category-counts") or
                        path.startswith("/api/public/games/by-designer/")):
                        cache_control = b"public, max-age=300, s-maxage=300"
                    # Image proxy - skip (already handled in endpoint)
                    elif path.startswith("/api/public/image-proxy"):
                        pass
                    else:
                        # Default for other public endpoints
                        cache_control = b"public, max-age=300, s-maxage=300"

                elif path.startswith("/api/health"):
                    # Health checks - cache for 1 minute
                    cache_control = b"public, max-age=60, s-maxage=60"

                elif path.startswith("/api/admin/"):
                    # Admin endpoints - never cache (private data)
                    cache_control = b"private, no-cache, no-store, must-revalidate"

                elif path.startswith("/api/"):
                    # Other API endpoints - short cache
                    cache_control = b"public, max-age=60, s-maxage=60"

                # Add cache-control header if determined
                if cache_control:
                    headers[b"cache-control"] = cache_control
                    message["headers"] = list(headers.items())
                    logger.debug(f"Added cache-control header to {path}: {cache_control.decode()}")

            await send(message)

        await self.app(scope, receive, send_wrapper)
