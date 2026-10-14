# services/image_service.py
"""
Image service layer - SSRF-safe proxying of BoardGameGeek images.

(Local thumbnail downloading was removed: images are served via Cloudinary or
proxied on demand.)
"""
import logging
import httpx
import re
from typing import Optional
from urllib.parse import unquote, urljoin, urlparse
from sqlalchemy.orm import Session

from config import API_BASE, HTTP_TIMEOUT

logger = logging.getLogger(__name__)

# Hosts the image proxy is allowed to fetch from (exact match on hostname).
BGG_IMAGE_HOSTS = ("cf.geekdo-images.com", "cf.geekdo-static.com")

# Maximum redirects followed (each hop is re-validated)
MAX_PROXY_REDIRECTS = 3

# Characters allowed in the path / query of a proxied image URL (RFC 3986
# pchar plus "/" and "?"), which covers BGG's /img/..=/fit-in/WxH/filters:...() URLs.
_SAFE_PATH_RE = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/-]*$")
_SAFE_QUERY_RE = re.compile(r"^[A-Za-z0-9._~!$&'()*+,;=:@%/?-]*$")


class UntrustedImageURLError(ValueError):
    """Raised when an image URL is not on the proxy allowlist."""


def build_trusted_image_url(url: str) -> str:
    """
    Validate a user-supplied image URL and rebuild it from a trusted origin.

    Only the path and query of the caller's URL are kept. The scheme, host and
    port come from constants (the BGG image hosts) or from API_BASE (our own
    /thumbs/ files), so user input can never choose where the request is sent.

    Raises:
        UntrustedImageURLError: If the URL is malformed or not allowlisted.
    """
    if not isinstance(url, str) or any(
        ch.isspace() or ord(ch) < 32 or ch == "\\" for ch in url
    ):
        raise UntrustedImageURLError("Malformed image URL")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        raise UntrustedImageURLError("Malformed image URL")

    try:
        port = parsed.port
    except ValueError:
        raise UntrustedImageURLError("Malformed image URL")

    host = (parsed.hostname or "").lower()
    origin = None

    for trusted_host in BGG_IMAGE_HOSTS:
        if host == trusted_host and port in (None, 80, 443):
            origin = f"https://{trusted_host}"
            break

    if origin is None:
        api = urlparse(API_BASE)
        if (
            api.hostname
            and host == api.hostname.lower()
            and parsed.scheme == api.scheme
            and port == api.port
        ):
            origin = API_BASE.rstrip("/")

    if origin is None:
        raise UntrustedImageURLError("Image host is not allowed")

    path = parsed.path or "/"
    query = parsed.query

    # The origin is fixed, but the path/query still come from the caller: keep
    # them to a strict character set and refuse dot-segments (including
    # percent-encoded ones) and encoded separators so they can't walk out of
    # the intended directory or smuggle extra URL structure.
    decoded_path = unquote(path)
    if (
        not _SAFE_PATH_RE.match(path)
        or not _SAFE_QUERY_RE.match(query)
        or "\\" in decoded_path
        or any(segment in (".", "..") for segment in decoded_path.split("/"))
        or re.search(r"%2f|%5c", path + query, re.IGNORECASE)
    ):
        raise UntrustedImageURLError("Malformed image URL")

    return origin + path + (f"?{query}" if query else "")


class ImageService:
    """Service for image-related operations"""

    def __init__(
        self, db: Session, http_client: Optional[httpx.AsyncClient] = None
    ):
        """
        Initialize image service.

        Args:
            db: Database session
            http_client: Optional httpx client for downloads
        """
        self.db = db
        self.http_client = http_client or httpx.AsyncClient(
            follow_redirects=True, timeout=HTTP_TIMEOUT
        )

    async def proxy_image(
        self, url: str, cache_max_age: int = 300
    ) -> tuple[bytes, str, str]:
        """
        Proxy an external image with caching headers.
        Requests modern image formats (WebP/AVIF) for better compression.

        Args:
            url: URL of the image to proxy
            cache_max_age: Cache max age in seconds (default 5 minutes)

        Returns:
            Tuple of (content bytes, content_type, cache_control header)

        Raises:
            UntrustedImageURLError: If the URL host is not allowlisted
            httpx.HTTPError: If image fetch fails
        """
        # Request modern image formats for better compression and performance
        # Priority: AVIF (best compression) > WebP (good compression) > any image format
        # CRITICAL: BGG requires proper browser headers to allow image downloads
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://boardgamegeek.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

        # SSRF protection: only fetch allowlisted hosts, and follow redirects
        # manually so every hop is re-validated (the shared client auto-follows).
        target = build_trusted_image_url(url)
        response = None
        for _ in range(MAX_PROXY_REDIRECTS + 1):
            response = await self.http_client.get(
                target, headers=headers, follow_redirects=False
            )
            if response.is_redirect and response.headers.get("location"):
                target = build_trusted_image_url(
                    urljoin(target, response.headers["location"])
                )
                continue
            break
        else:
            raise httpx.TooManyRedirects(
                "Too many redirects while proxying image", request=response.request
            )

        response.raise_for_status()

        content_type = response.headers.get(
            "content-type", "application/octet-stream"
        )
        cache_control = f"public, max-age={cache_max_age}"

        return response.content, content_type, cache_control
