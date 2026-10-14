"""Client IP resolution shared by the login limiter and the API rate limiter."""
import functools
import logging

from starlette.requests import Request

import config

logger = logging.getLogger(__name__)

# Fixed wording per chain length so no request-derived value is ever written to the log.
_CHAIN_LABELS = {1: "1 entry", 2: "2 entries", 3: "3 entries"}


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
            _log_chain_length_once(_chain_label(len(parts)))
            return parts[max(len(parts) - hops, 0)]
    return request.client.host if request.client else "unknown"


def _chain_label(entries: int) -> str:
    return _CHAIN_LABELS.get(entries, "4 or more entries")


@functools.lru_cache(maxsize=None)
def _log_chain_length_once(label: str) -> None:
    """Log how many X-Forwarded-For entries arrive, once per process and per distinct size.

    Lets us confirm TRUSTED_PROXY_COUNT against the real proxy chain from the deploy logs.
    The label comes from a fixed table, so neither addresses nor header text reach the log.
    """
    logger.info("X-Forwarded-For arrived with %s (TRUSTED_PROXY_COUNT is set in config)", label)
