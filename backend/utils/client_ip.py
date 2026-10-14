"""Client IP resolution shared by the login limiter and the API rate limiter."""
import logging

from starlette.requests import Request

import config

logger = logging.getLogger(__name__)
_logged_chain_length = False


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
            _log_chain_length_once(len(parts), hops)
            return parts[max(len(parts) - hops, 0)]
    return request.client.host if request.client else "unknown"


def _log_chain_length_once(entries: int, hops: int) -> None:
    """Log how many X-Forwarded-For entries actually arrive, once per process.

    Lets us confirm TRUSTED_PROXY_COUNT against the real proxy chain from the deploy logs
    (only counts are logged, never addresses).
    """
    global _logged_chain_length
    if not _logged_chain_length:
        _logged_chain_length = True
        logger.info(
            "X-Forwarded-For has %d entr%s; TRUSTED_PROXY_COUNT=%d",
            entries, "y" if entries == 1 else "ies", hops,
        )
