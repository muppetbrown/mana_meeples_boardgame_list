# middleware/logging.py
"""
Request logging middleware that logs all HTTP requests with timing and request IDs.
Integrates with the performance monitor for metrics collection.
"""
import time
import uuid
import logging
from starlette.types import ASGIApp, Receive, Scope, Send
from .performance import performance_monitor

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Log all HTTP requests with timing and request IDs"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        status_code = 200  # Default

        # Add request ID to scope for downstream handlers
        scope["request_id"] = request_id

        path = scope.get("path", "")
        method = scope.get("method", "")

        logger.info(
            f"Request started: {method} {path}",
            extra={"request_id": request_id},
        )

        # Capture status code from response
        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration = time.time() - start_time
            status_code = 500
            performance_monitor.record_request(
                path, method, duration, status_code
            )
            logger.error(
                f"Request failed: {method} {path} - {str(e)} ({duration:.3f}s)",
                extra={"request_id": request_id},
            )
            raise
        else:
            duration = time.time() - start_time
            performance_monitor.record_request(
                path, method, duration, status_code
            )
            logger.info(
                f"Request completed: {method} {path} ({duration:.3f}s)",
                extra={"request_id": request_id},
            )
