# middleware/request_id.py
"""
Request ID middleware for distributed tracing and log correlation.
Generates or extracts a unique ID for each request and propagates it through
the application for correlation in logs and debugging.
"""
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate or extract request IDs for distributed tracing.

    Features:
    - Accepts X-Request-ID from load balancer/proxy if present
    - Generates new UUID if no request ID provided
    - Stores request ID in request.state for access in endpoints
    - Adds X-Request-ID header to response for client-side correlation
    - Enables log correlation across multi-instance deployments
    """

    async def dispatch(self, request: Request, call_next):
        # Check if request already has ID (from load balancer or previous proxy)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in request state for access throughout request lifecycle
        request.state.request_id = request_id

        # Log request with ID for correlation
        logger.debug(
            f"Request {request_id[:8]}... {request.method} {request.url.path}"
        )

        # Process request
        response = await call_next(request)

        # Add request ID to response headers for client-side tracing
        # This allows clients to correlate requests with logs
        if isinstance(response, Response):
            response.headers["X-Request-ID"] = request_id

        return response
