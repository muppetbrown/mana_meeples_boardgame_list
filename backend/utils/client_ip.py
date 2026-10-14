"""Client IP resolution shared by the login limiter and the API rate limiter."""
from starlette.requests import Request

import config


def get_client_ip(request: Request) -> str:
    """Return the caller's IP, trusting only the proxies we operate.

    X-Forwarded-For is "client-supplied..., real client, proxy1, ...". Only the entries our
    own proxies appended are trustworthy, so the client is taken from the right-hand side
    (``TRUSTED_PROXY_COUNT`` entries in). Taking the leftmost entry would let any caller pick
    their own rate-limit bucket by sending a header.
    """
    hops = config.TRUSTED_PROXY_COUNT
    if hops > 0:
        forwarded = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[max(len(parts) - hops, 0)]
    return request.client.host if request.client else "unknown"
