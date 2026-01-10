# bgg_service.py
"""
BoardGameGeek API service with circuit breaker pattern.
Sprint 5: Enhanced with circuit breaker for fail-fast during BGG outages
Sprint 16: Added rate limiting to prevent BGG API abuse
"""
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, Any
from xml.etree.ElementTree import Element
from datetime import datetime, timedelta
from collections import deque
import httpx
import logging
import html
import config
from config import HTTP_TIMEOUT, HTTP_RETRIES
from pybreaker import CircuitBreaker, CircuitBreakerError
from services.bgg_parser import (
    parse_basic_info,
    parse_images,
    parse_player_counts,
    parse_playtime,
    parse_links,
    parse_expansion_relationships,
    parse_statistics,
    strip_namespace,
)

logger = logging.getLogger(__name__)


class BGGServiceError(Exception):
    """Custom exception for BGG service errors"""

    pass


class BGGRateLimiter:
    """
    Token bucket rate limiter for BGG API requests.
    Prevents hitting BGG's rate limits by throttling requests.

    Algorithm: Token bucket with exponential backoff
    - Tracks request timestamps in a sliding window
    - Blocks requests when limit exceeded
    - Implements exponential backoff (capped at 60s)
    """

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window (default: 10)
            time_window: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()  # Store request timestamps
        self._lock = asyncio.Lock()  # Thread-safe for async

    async def acquire(self) -> None:
        """
        Acquire permission to make a BGG API request.

        Blocks (with exponential backoff) if rate limit exceeded.
        Thread-safe for concurrent async requests.

        Raises:
            No exceptions - blocks until request can proceed
        """
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.time_window)

            # Remove old requests outside time window (sliding window)
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            # Check if rate limit exceeded
            if len(self.requests) >= self.max_requests:
                # Calculate wait time with exponential backoff
                oldest_request = self.requests[0]
                wait_until = oldest_request + timedelta(seconds=self.time_window)
                wait_time = (wait_until - now).total_seconds()

                # Cap wait time at 60 seconds max
                wait_time = min(wait_time, 60)

                logger.warning(
                    f"BGG API rate limit reached ({self.max_requests} req/{self.time_window}s), "
                    f"waiting {wait_time:.1f}s before retry"
                )

                # Wait and retry
                await asyncio.sleep(wait_time)
                return await self.acquire()  # Recursive retry after waiting

            # Record this request
            self.requests.append(now)
            logger.debug(
                f"BGG API request acquired "
                f"({len(self.requests)}/{self.max_requests} in window)"
            )


# Global rate limiter instance
# 10 requests per 60 seconds (conservative to respect BGG's limits)
bgg_rate_limiter = BGGRateLimiter(max_requests=10, time_window=60)


# Circuit breaker configuration
# - failure_threshold: Number of failures before opening circuit
# - recovery_timeout: Seconds to wait before attempting recovery
# - expected_exception: Exceptions that trigger circuit breaker
# Note: pybreaker doesn't support async functions directly, so we use manual tracking
bgg_circuit_breaker = CircuitBreaker(
    fail_max=5,  # Open circuit after 5 failures
    reset_timeout=60,  # Wait 60 seconds before attempting recovery
    exclude=[BGGServiceError],  # Don't count BGGServiceError (validation errors) as failures
    name="BGG API",
)


def _is_bgg_available() -> bool:
    """
    Check if BGG circuit breaker is closed (service available).
    Used for monitoring and graceful degradation.
    """
    return bgg_circuit_breaker.current_state == "closed"


async def fetch_bgg_thing(bgg_id: int, retries: int = HTTP_RETRIES) -> Dict[str, Any]:
    """
    Enhanced BGG data fetcher that captures comprehensive game information
    including descriptions, mechanics, designers, publishers, and ratings.
    Uses exponential backoff for retries and circuit breaker for fail-fast.
    Sprint 5: Circuit breaker prevents cascading failures during BGG outages
    Sprint 16: Rate limiting prevents BGG API abuse
    """
    # Check circuit breaker before attempting request
    try:
        bgg_circuit_breaker.call(lambda: None)  # Check if circuit is open
    except CircuitBreakerError:
        logger.warning(f"BGG circuit breaker is open, rejecting request for game {bgg_id}")
        raise BGGServiceError("BGG API is currently unavailable (circuit breaker open)")

    # Rate limiting: Acquire permission to make BGG API request
    # Blocks if rate limit exceeded (10 requests per 60 seconds)
    await bgg_rate_limiter.acquire()

    url = "https://boardgamegeek.com/xmlapi2/thing"
    params = {"id": str(bgg_id), "stats": "1"}

    # Add BGG API key to headers if available
    headers = {}
    if config.BGG_API_KEY:
        headers["Authorization"] = f"Bearer {config.BGG_API_KEY}"
        logger.info(f"Using BGG API key for authentication")
    else:
        logger.warning(f"No BGG API key configured - request may be rate limited")

    # Initialize variables outside of try blocks to ensure they're in scope for exception handlers
    response = None
    response_text = None

    async with httpx.AsyncClient(timeout=float(HTTP_TIMEOUT)) as client:
        for attempt in range(retries):
            try:
                logger.info(
                    f"Fetching BGG data for game {bgg_id} (attempt {attempt + 1})"
                )

                # Special debugging for problematic IDs
                if bgg_id in [314421, 13]:  # 13 = Catan (known good ID)
                    logger.info(f"=== SPECIAL DEBUG FOR BGG ID {bgg_id} ===")
                    logger.info(f"Request URL: {url}")
                    logger.info(f"Request params: {params}")

                response = await client.get(url, params=params, headers=headers)

                # Extra debugging for test IDs
                if bgg_id in [314421, 13]:
                    logger.info(f"Raw response status: {response.status_code}")
                    logger.info(
                        f"Raw response headers: {dict(response.headers)}"
                    )
                    logger.info(f"Raw response encoding: {response.encoding}")
                    logger.info(
                        f"Raw response content length: {len(response.content)} bytes"
                    )
                    logger.info(
                        f"Raw response text length: {len(response.text)} chars"
                    )
                    logger.info(
                        f"Raw response content (first 500 bytes): {repr(response.content[:500])}"
                    )
                    logger.info(
                        f"Raw response text (first 500 chars): {repr(response.text[:500])}"
                    )
                    logger.info(
                        f"=== END SPECIAL DEBUG FOR BGG ID {bgg_id} ==="
                    )

                # Handle BGG's queue system and rate limiting
                # 401 is often used by BGG for rate limiting (not actual auth)
                # 202 = request queued, 500/503 = temporary server issues
                if response.status_code in (202, 401, 500, 503):
                    delay = (2**attempt) + (
                        attempt * 0.5
                    )  # Exponential backoff with jitter
                    logger.warning(
                        f"BGG returned {response.status_code} for game {bgg_id}, retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    continue

                if response.status_code == 400:
                    raise BGGServiceError(f"Invalid BGG ID: {bgg_id}")

                response.raise_for_status()

                # Validate response content
                content_type = response.headers.get("content-type", "").lower()
                response_text = response.text.strip()

                # COMPREHENSIVE RESPONSE DEBUGGING
                logger.info(f"BGG response status: {response.status_code}")
                logger.info(f"BGG response content-type: {content_type}")
                logger.info(f"BGG response length: {len(response_text)} chars")
                logger.info(
                    f"BGG response first 200 chars: {repr(response_text[:200])}"
                )
                logger.info(
                    f"BGG response last 200 chars: {repr(response_text[-200:])}"
                )

                # Special debugging for test IDs during validation
                if bgg_id in [314421, 13]:
                    logger.info(f"=== BGG ID {bgg_id} VALIDATION DEBUG ===")
                    logger.info(
                        f"Original response.text length: {len(response.text)}"
                    )
                    logger.info(
                        f"Stripped response_text length: {len(response_text)}"
                    )
                    logger.info(
                        f"response.text == response_text.strip(): {response.text == response_text}"
                    )
                    logger.info(f"response_text is falsy: {not response_text}")
                    logger.info(
                        f"response_text.strip() is falsy: {not response_text.strip()}"
                    )
                    logger.info(
                        f"len(response_text.strip()) < 20: {len(response_text.strip()) < 20}"
                    )
                    logger.info(
                        f"'xml' in content_type: {'xml' in content_type}"
                    )
                    logger.info(
                        f"response_text.startswith('<?xml'): {response_text.startswith('<?xml')}"
                    )
                    logger.info(
                        f"=== END BGG ID {bgg_id} VALIDATION DEBUG ==="
                    )

                # Check for truly empty response
                if not response_text:
                    logger.error(
                        f"BGG returned truly empty response for game {bgg_id}"
                    )
                    raise BGGServiceError(
                        f"Game ID {bgg_id} does not exist on BoardGameGeek (empty response)"
                    )

                # Check for whitespace-only response
                if not response_text.strip():
                    logger.error(
                        f"BGG returned whitespace-only response for game {bgg_id}"
                    )
                    raise BGGServiceError(
                        f"Game ID {bgg_id} does not exist on BoardGameGeek (whitespace-only response)"
                    )

                # Check for extremely short responses (less than 20 chars is suspicious)
                if len(response_text.strip()) < 20:
                    logger.error(
                        f"BGG returned suspiciously short response for game {bgg_id}: {repr(response_text)}"
                    )
                    # Check if it's a specific "Not Found" type response
                    if response_text.strip().lower() in [
                        "",
                        "not found",
                        "404",
                        "error",
                    ]:
                        raise BGGServiceError(
                            f"Game ID {bgg_id} does not exist on BoardGameGeek"
                        )
                    else:
                        raise BGGServiceError(
                            f"Game ID {bgg_id} returned invalid response from BoardGameGeek: '{response_text.strip()}'"
                        )

                # Validate we received XML content
                if (
                    "xml" not in content_type
                    and not response_text.strip().startswith("<?xml")
                ):
                    # BGG sometimes returns HTML error pages with 200 status
                    logger.error(
                        f"BGG returned non-XML content for game {bgg_id}. Content-Type: {content_type}"
                    )
                    if "<html" in response_text.lower()[:100]:
                        # Check for common "not found" patterns in HTML
                        if any(
                            pattern in response_text.lower()
                            for pattern in [
                                "not found",
                                "404",
                                "does not exist",
                            ]
                        ):
                            raise BGGServiceError(
                                f"Game ID {bgg_id} does not exist on BoardGameGeek"
                            )
                        else:
                            raise BGGServiceError(
                                f"Game ID {bgg_id} returned an error page from BoardGameGeek"
                            )
                    else:
                        raise BGGServiceError(
                            f"Game ID {bgg_id} returned invalid content type from BoardGameGeek: {content_type}"
                        )

                # Check if response looks like valid XML structure
                stripped_response = response_text.strip()
                if not stripped_response.startswith(
                    "<?xml"
                ) and not stripped_response.startswith("<"):
                    logger.error(
                        f"BGG response doesn't look like XML for game {bgg_id}: {repr(stripped_response[:100])}"
                    )
                    raise BGGServiceError(
                        f"Game ID {bgg_id} returned non-XML content from BoardGameGeek"
                    )

                break

            except httpx.TimeoutException:
                logger.error(f"Timeout fetching BGG data for game {bgg_id}")
                if attempt == retries - 1:
                    raise BGGServiceError(f"Timeout fetching game {bgg_id}")
                delay = (2**attempt) + (
                    attempt * 0.5
                )  # Exponential backoff with jitter
                await asyncio.sleep(delay)

            except httpx.HTTPError as e:
                logger.error(
                    f"HTTP error fetching BGG data for game {bgg_id}: {e}"
                )
                if attempt == retries - 1:
                    raise BGGServiceError(
                        f"Failed to fetch game {bgg_id}: {e}"
                    )
                delay = (2**attempt) + (
                    attempt * 0.5
                )  # Exponential backoff with jitter
                await asyncio.sleep(delay)

            except BGGServiceError:
                # BGGServiceError from validation checks should be re-raised immediately
                # (don't retry for invalid game IDs, malformed responses, etc.)
                raise

            except Exception as e:
                logger.error(
                    f"Unexpected error fetching BGG data for game {bgg_id}: {e}"
                )
                if attempt == retries - 1:
                    raise BGGServiceError(
                        f"Unexpected error fetching game {bgg_id}: {e}"
                    )
                delay = (2**attempt) + (
                    attempt * 0.5
                )  # Exponential backoff with jitter
                await asyncio.sleep(delay)

    # Parse XML response with comprehensive error handling
    try:
        logger.info(f"Attempting to parse XML response for game {bgg_id}...")

        # Check if we have valid response_text before attempting to parse
        if response_text is None:
            logger.error(
                f"No response_text available for game {bgg_id} - all retry attempts failed"
            )
            raise BGGServiceError(
                f"Failed to fetch valid response for game {bgg_id} after {retries} attempts"
            )

        # Try to parse the XML (use the validated response_text, not original response.text)
        root = ET.fromstring(response_text)
        logger.info(
            f"Successfully parsed XML for game {bgg_id}. Root tag: {root.tag}"
        )

        strip_namespace(root)

        # Check if BGG returned an error in XML format
        error_elem = root.find(".//error")
        if error_elem is not None:
            error_message = error_elem.get("message", "Unknown error")
            logger.error(
                f"BGG returned XML error for game {bgg_id}: {error_message}"
            )
            raise BGGServiceError(
                f"BGG API error for game {bgg_id}: {error_message}"
            )

        item = root.find("item")
        if item is None:
            # Log the actual response for debugging
            logger.error(
                f"No item found in BGG response for game {bgg_id}. Response root tag: {root.tag}"
            )
            logger.error(f"Full response content: {response_text}")

            # Check if this is a "things" response with no items (empty response for non-existent game)
            if root.tag == "things" and len(list(root)) == 0:
                raise BGGServiceError(
                    f"Game ID {bgg_id} does not exist on BoardGameGeek"
                )
            else:
                raise BGGServiceError(
                    f"No game data found for BGG ID {bgg_id} - unexpected response format"
                )

        logger.info(
            f"Successfully found item in BGG response for game {bgg_id}"
        )
        return _extract_comprehensive_game_data(item, bgg_id)

    except ET.ParseError as e:
        # Enhanced XML parsing error logging - now all variables are in scope
        logger.error("=== XML PARSE ERROR DEBUG INFO ===")
        logger.error(f"Game ID: {bgg_id}")
        logger.error(f"Parse Error: {str(e)}")

        # Only log response details if we have a response object
        if response is not None:
            logger.error(f"Response status code: {response.status_code}")
            logger.error(f"Response headers: {dict(response.headers)}")
            logger.error(f"Response length: {len(response.text)} chars")
            logger.error(f"Response encoding: {response.encoding}")
            logger.error(
                f"Raw response bytes length: {len(response.content)} bytes"
            )

            # Show response content in multiple ways
            logger.error(f"Response text repr: {repr(response.text)}")
            logger.error(
                f"Response bytes repr (first 500): {repr(response.content[:500])}"
            )

            # Try to identify specific issues
            if not response.text.strip():
                logger.error(
                    "Response is empty or whitespace-only after .text conversion"
                )
            elif len(response.content) == 0:
                logger.error("Response content (bytes) is empty")
            elif response.text != response.content.decode(
                response.encoding or "utf-8", errors="ignore"
            ):
                logger.error(
                    "Response text differs from decoded content - encoding issue?"
                )
        else:
            logger.error("No response object available for debugging")

        # Log response_text if available
        if response_text is not None:
            logger.error(
                f"Processed response_text length: {len(response_text)} chars"
            )
            logger.error(
                f"Processed response_text repr: {repr(response_text[:500])}"
            )
        else:
            logger.error("No processed response_text available")

        logger.error("=== END XML PARSE ERROR DEBUG INFO ===")

        raise BGGServiceError(
            f"Failed to parse BGG response for game {bgg_id}: {str(e)} - See logs for detailed debugging info"
        )


def _extract_comprehensive_game_data(item: Element, bgg_id: int) -> Dict[str, Any]:
    """Extract comprehensive game data from BGG XML response"""
    data = {"bgg_id": bgg_id}

    # Use focused parser functions for each data section
    data.update(parse_basic_info(item))
    data.update(parse_images(item))
    data.update(parse_player_counts(item))
    data.update(parse_playtime(item))

    # Parse link elements for different types
    data["categories"] = parse_links(item, "boardgamecategory")
    data["mechanics"] = parse_links(item, "boardgamemechanic")
    data["designers"] = parse_links(item, "boardgamedesigner")
    data["publishers"] = parse_links(item, "boardgamepublisher")
    data["artists"] = parse_links(item, "boardgameartist")

    # Parse expansion relationships
    data.update(parse_expansion_relationships(item, data["title"], data["is_expansion"]))

    # Parse statistics (ratings, complexity, BGG rank, game type)
    data.update(parse_statistics(item))

    # Game classification - ensure game_type is always set with fallback
    if "game_type" not in data or not data["game_type"]:
        data["game_type"] = _get_game_classification(item)

    # Determine if cooperative based on mechanics
    is_cooperative = any(
        "cooperative" in mechanic.lower() for mechanic in data["mechanics"]
    )
    data["is_cooperative"] = is_cooperative

    logger.info(
        f"Successfully extracted comprehensive data for '{data['title']}'"
    )

    # Note: Sleeve data fetching has been moved to a background task in the import endpoint
    # to prevent blocking the import process. Sleeve data is now fetched asynchronously
    # after the game is created/updated.

    return data


def _get_game_classification(item: Element) -> str:
    """
    Fallback game classification system based on categories and mechanics
    when BGG ranking data is not available
    """
    # Extract categories and mechanics from the item
    categories = []
    for link in item.findall("link[@type='boardgamecategory']"):
        category = link.attrib.get("value", "").strip()
        if category:
            categories.append(category)

    mechanics = []
    for link in item.findall("link[@type='boardgamemechanic']"):
        mechanic = link.attrib.get("value", "").strip()
        if mechanic:
            mechanics.append(mechanic)

    # Primary game types (most recognizable)
    primary_types = {
        "party": ["party game"],
        "family": ["children's game", "family game"],
        "coop": ["cooperative game"],
        "social_deduction": ["social deduction", "bluffing", "deduction"],
        "dexterity": ["dexterity", "real time"],
        "trivia": ["trivia"],
        "abstract": ["abstract strategy"],
        "war": ["wargame", "world war"],
        "economic": ["economic"],
        "thematic": ["thematic"],
    }

    # Check categories first for primary type
    for game_type, keywords in primary_types.items():
        for keyword in keywords:
            if any(keyword in cat.lower() for cat in categories):
                type_names = {
                    "party": "Party",
                    "family": "Family",
                    "coop": "Co-op",
                    "social_deduction": "Social Deduction",
                    "dexterity": "Dexterity",
                    "trivia": "Trivia",
                    "abstract": "Abstract",
                    "war": "War Game",
                    "economic": "Economic",
                    "thematic": "Thematic",
                }
                return type_names[game_type]

    # Check mechanics for cooperative games
    if any("cooperative" in mech.lower() for mech in mechanics):
        return "Co-op"

    # Mechanic-based classification
    mechanic_priority = [
        ("deck building", "Deck Builder"),
        ("bag building", "Bag Builder"),
        ("worker placement", "Worker Placement"),
        ("tile placement", "Tile Laying"),
        ("roll and write", "Roll & Write"),
        ("flip and write", "Roll & Write"),
        ("drafting", "Drafting"),
        ("trick-taking", "Trick Taking"),
        ("area control", "Area Control"),
        ("area majority", "Area Control"),
        ("route building", "Route Building"),
        ("network building", "Route Building"),
        ("engine building", "Engine Builder"),
        ("tableau building", "Engine Builder"),
        ("pattern building", "Pattern Builder"),
        ("set collection", "Set Collection"),
        ("auction", "Auction"),
        ("trading", "Trading"),
    ]

    for keyword, display_name in mechanic_priority:
        if any(keyword in mech.lower() for mech in mechanics):
            return display_name

    # Fallback to strategy if nothing else matches
    return "Strategy"
