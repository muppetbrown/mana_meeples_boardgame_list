# bgg_service.py
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict
import httpx
import logging
import html
import config
from config import HTTP_TIMEOUT, HTTP_RETRIES

logger = logging.getLogger(__name__)


class BGGServiceError(Exception):
    """Custom exception for BGG service errors"""

    pass


async def fetch_bgg_thing(bgg_id: int, retries: int = HTTP_RETRIES) -> Dict:
    """
    Enhanced BGG data fetcher that captures comprehensive game information
    including descriptions, mechanics, designers, publishers, and ratings
    Uses exponential backoff for retries.
    """
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

        _strip_namespace(root)

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


def _strip_namespace(root):
    """Remove XML namespaces from element tags"""
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]


def _extract_comprehensive_game_data(item, bgg_id: int) -> Dict:
    """Extract comprehensive game data from BGG XML response"""
    data = {}
    data["bgg_id"] = bgg_id

    # Check if this item is an expansion
    item_type = item.get("type", "boardgame")
    data["is_expansion"] = item_type == "boardgameexpansion"

    # Basic information
    name_elem = item.find("name[@type='primary']") or item.find("name")
    data["title"] = (
        name_elem.attrib.get("value", "") if name_elem is not None else ""
    )

    # Year published
    year_elem = item.find("yearpublished")
    try:
        data["year"] = (
            int(year_elem.attrib.get("value", ""))
            if year_elem is not None
            else None
        )
    except (ValueError, TypeError):
        data["year"] = None

    # Description
    description_elem = item.find("description")
    if description_elem is not None and description_elem.text:
        # Clean up BGG's HTML-like description text
        description = description_elem.text.strip()
        # Decode HTML entities first
        description = html.unescape(description)
        # Remove common BGG markup
        description = description.replace("&#10;", "\n")
        description = description.replace("&quot;", '"')
        description = description.replace("&amp;", "&")
        data["description"] = description[:2000] if description else None
    else:
        data["description"] = None

    # Images
    thumbnail_elem = item.find("thumbnail")
    data["thumbnail"] = (
        thumbnail_elem.text.strip()
        if thumbnail_elem is not None and thumbnail_elem.text
        else None
    )

    image_elem = item.find("image")
    data["image"] = (
        image_elem.text.strip()
        if image_elem is not None and image_elem.text
        else None
    )

    # Player counts
    try:
        min_players_elem = item.find("minplayers")
        data["players_min"] = (
            int(min_players_elem.attrib.get("value", ""))
            if min_players_elem is not None
            else None
        )

        max_players_elem = item.find("maxplayers")
        data["players_max"] = (
            int(max_players_elem.attrib.get("value", ""))
            if max_players_elem is not None
            else None
        )
    except (ValueError, TypeError):
        data["players_min"] = None
        data["players_max"] = None

    # Play time
    try:
        min_time_elem = item.find("minplaytime")
        max_time_elem = item.find("maxplaytime")

        if min_time_elem is not None and max_time_elem is not None:
            data["playtime_min"] = (
                int(min_time_elem.attrib.get("value", "")) or None
            )
            data["playtime_max"] = (
                int(max_time_elem.attrib.get("value", "")) or None
            )
        else:
            # Fallback to playing time
            play_time_elem = item.find("playingtime")
            if play_time_elem is not None:
                playtime = int(play_time_elem.attrib.get("value", "")) or None
                data["playtime_min"] = playtime
                data["playtime_max"] = playtime
            else:
                data["playtime_min"] = None
                data["playtime_max"] = None
    except (ValueError, TypeError):
        data["playtime_min"] = None
        data["playtime_max"] = None

    # Minimum age
    try:
        age_elem = item.find("minage")
        data["min_age"] = (
            int(age_elem.attrib.get("value", ""))
            if age_elem is not None
            else None
        )
    except (ValueError, TypeError):
        data["min_age"] = None

    # Categories (themes)
    categories = []
    for link in item.findall("link[@type='boardgamecategory']"):
        category = link.attrib.get("value", "").strip()
        if category:
            categories.append(category)
    data["categories"] = categories

    # Mechanics
    mechanics = []
    for link in item.findall("link[@type='boardgamemechanic']"):
        mechanic = link.attrib.get("value", "").strip()
        if mechanic:
            mechanics.append(mechanic)
    data["mechanics"] = mechanics

    # Designers
    designers = []
    for link in item.findall("link[@type='boardgamedesigner']"):
        designer = link.attrib.get("value", "").strip()
        if designer:
            designers.append(designer)
    data["designers"] = designers

    # Publishers
    publishers = []
    for link in item.findall("link[@type='boardgamepublisher']"):
        publisher = link.attrib.get("value", "").strip()
        if publisher:
            publishers.append(publisher)
    data["publishers"] = publishers

    # Artists
    artists = []
    for link in item.findall("link[@type='boardgameartist']"):
        artist = link.attrib.get("value", "").strip()
        if artist:
            artists.append(artist)
    data["artists"] = artists

    # Expansion relationships
    # Find base game link (if this IS an expansion)
    base_game_link = item.find("link[@type='boardgameexpansion'][@inbound='true']")
    if base_game_link is not None:
        try:
            data["base_game_bgg_id"] = int(base_game_link.get("id"))
            data["base_game_name"] = base_game_link.get("value", "")
        except (ValueError, TypeError):
            data["base_game_bgg_id"] = None
            data["base_game_name"] = None
    else:
        data["base_game_bgg_id"] = None
        data["base_game_name"] = None

    # Find expansion links (if this is a base game with expansions)
    expansion_links = []
    for link in item.findall("link[@type='boardgameexpansion']"):
        # Skip inbound links (those are base games, not expansions)
        if link.get("inbound") != "true":
            try:
                expansion_links.append(
                    {
                        "bgg_id": int(link.get("id")),
                        "name": link.get("value", ""),
                    }
                )
            except (ValueError, TypeError):
                continue
    data["expansion_bgg_ids"] = expansion_links

    # Auto-detect player count modifications for expansions
    # Look for patterns like "5-6 Player" or "5-6 Extension" in title
    if data["is_expansion"]:
        title_lower = data["title"].lower()
        # Common patterns for player expansion titles
        import re

        player_expansion_pattern = r"(\d+)[-–](\d+)\s*(player|extension)"
        match = re.search(player_expansion_pattern, title_lower)
        if match:
            try:
                data["modifies_players_min"] = int(match.group(1))
                data["modifies_players_max"] = int(match.group(2))
                logger.info(
                    f"Auto-detected player modification for {data['title']}: {data['modifies_players_min']}-{data['modifies_players_max']}"
                )
            except (ValueError, TypeError):
                pass

        # Set default expansion_type
        # Check if title suggests it's standalone (common keywords)
        standalone_keywords = [
            "standalone",
            "stand alone",
            "stand-alone",
            "can be played alone",
            "playable without",
        ]
        is_standalone = any(keyword in title_lower for keyword in standalone_keywords)

        if is_standalone:
            data["expansion_type"] = "both"
            logger.info(
                f"Auto-detected standalone expansion for {data['title']}"
            )
        else:
            # Default to requires_base for most expansions
            data["expansion_type"] = "requires_base"

    # Statistics (ratings, complexity, etc.)
    statistics = item.find("statistics")
    if statistics is not None:
        ratings = statistics.find("ratings")
        if ratings is not None:
            # Average rating
            try:
                rating_elem = ratings.find("average")
                if rating_elem is not None:
                    data["average_rating"] = (
                        float(rating_elem.attrib.get("value", "")) or None
                    )
                else:
                    data["average_rating"] = None
            except (ValueError, TypeError):
                data["average_rating"] = None

            # Complexity (weight)
            try:
                weight_elem = ratings.find("averageweight")
                if weight_elem is not None:
                    data["complexity"] = (
                        float(weight_elem.attrib.get("value", "")) or None
                    )
                else:
                    data["complexity"] = None
            except (ValueError, TypeError):
                data["complexity"] = None

            # BGG Rank and Game Type from ranks
            ranks = ratings.find("ranks")
            if ranks is not None:
                main_rank = ""
                game_types = []
                has_consensus = False
                not_ranked_category = None

                # First pass: check if any category has a numerical rank (consensus)
                for rank in ranks.findall("rank"):
                    rank_name = rank.attrib.get("name", "")
                    rank_value = rank.attrib.get("value", "")

                    if (
                        rank_name == "boardgame"
                        and rank_value
                        and rank_value != "Not Ranked"
                    ):
                        main_rank = rank_value
                    elif (
                        rank_name != "boardgame"
                        and rank_value
                        and rank_value != "Not Ranked"
                        and rank_value.isdigit()
                    ):
                        has_consensus = True
                        break

                # Second pass: collect game types based on consensus
                for rank in ranks.findall("rank"):
                    rank_name = rank.attrib.get("name", "")
                    rank_value = rank.attrib.get("value", "")

                    if rank_name != "boardgame":
                        if has_consensus:
                            # Enough votes for consensus - use ALL ranked categories
                            if (
                                rank_value
                                and rank_value != "Not Ranked"
                                and rank_value.isdigit()
                            ):
                                game_types.append((int(rank_value), rank_name))
                        else:
                            # Not enough votes - use the "Not Ranked" category
                            if (
                                rank_value == "Not Ranked"
                                and not_ranked_category is None
                            ):
                                not_ranked_category = rank_name

                try:
                    data["bgg_rank"] = int(main_rank) if main_rank else None
                except (ValueError, TypeError):
                    data["bgg_rank"] = None

                # Determine final game type
                if has_consensus and game_types:
                    # Sort by rank and convert to friendly names
                    game_types.sort(
                        key=lambda x: x[0]
                    )  # Sort by numerical rank

                    friendly_names = {
                        "strategygames": "Strategy",
                        "familygames": "Family",
                        "thematic": "Thematic",
                        "partygames": "Party",
                        "abstracts": "Abstract",
                        "cgs": "Card Game",
                        "childrensgames": "Children's",
                        "wargames": "War Game",
                    }

                    friendly_categories = []
                    for rank_num, category in game_types:
                        friendly_name = friendly_names.get(
                            category, category.title()
                        )
                        friendly_categories.append(friendly_name)

                    data["game_type"] = " • ".join(friendly_categories)

                    if config.SAVE_DEBUG_INFO:
                        print(
                            f"    Consensus found - ranked categories: {[cat for _, cat in game_types]}"
                        )
                        print(f"    Combined game type: {data['game_type']}")

                elif not_ranked_category:
                    # No consensus - use "Not Ranked" category + first boardgame category
                    friendly_names = {
                        "strategygames": "Strategy",
                        "familygames": "Family",
                        "thematic": "Thematic",
                        "partygames": "Party",
                        "abstracts": "Abstract",
                        "cgs": "Card Game",
                        "childrensgames": "Children's",
                        "wargames": "War Game",
                    }

                    rank_type = friendly_names.get(
                        not_ranked_category, not_ranked_category.title()
                    )

                    # Get first boardgame category for additional context
                    first_category = categories[0] if categories else None

                    if first_category:
                        data["game_type"] = f"{rank_type} • {first_category}"
                    else:
                        data["game_type"] = rank_type

                    if config.SAVE_DEBUG_INFO:
                        print(
                            f"    No consensus - using Not Ranked category: {not_ranked_category}"
                        )
                        print(
                            f"    First boardgame category: {first_category}"
                        )
                        print(f"    Combined game type: {data['game_type']}")
                else:
                    # Fallback to our classification system
                    data["game_type"] = _get_game_classification(item)
                    if config.SAVE_DEBUG_INFO:
                        print(
                            f"    No BGG ranking data, using fallback classification: {data['game_type']}"
                        )

                if config.SAVE_DEBUG_INFO:
                    print(f"    Found main rank: {data['bgg_rank']}")
            else:
                if config.SAVE_DEBUG_INFO:
                    print(f"    ranks element not found in ratings")
                # Fallback for both rank and game type
                data["bgg_rank"] = None
                data["game_type"] = _get_game_classification(item)

            # Number of ratings
            try:
                users_rated_elem = ratings.find("usersrated")
                if users_rated_elem is not None:
                    data["users_rated"] = (
                        int(users_rated_elem.attrib.get("value", "")) or None
                    )
                else:
                    data["users_rated"] = None
            except (ValueError, TypeError):
                data["users_rated"] = None
        else:
            # No ratings data
            data["average_rating"] = None
            data["complexity"] = None
            data["bgg_rank"] = None
            data["users_rated"] = None
            data["game_type"] = _get_game_classification(item)
    else:
        # No statistics data
        data["average_rating"] = None
        data["complexity"] = None
        data["bgg_rank"] = None
        data["users_rated"] = None
        data["game_type"] = _get_game_classification(item)

    # Game classification - ensure game_type is always set
    if "game_type" not in data or not data["game_type"]:
        data["game_type"] = _get_game_classification(item)

    # Determine if cooperative
    is_cooperative = any(
        "cooperative" in mechanic.lower() for mechanic in mechanics
    )
    data["is_cooperative"] = is_cooperative

    logger.info(
        f"Successfully extracted comprehensive data for '{data['title']}'"
    )

    # Fetch sleeve data using Selenium scraper
    try:
        from services.sleeve_scraper import scrape_sleeve_data

        logger.info(f"Fetching sleeve data for '{data['title']}' (BGG ID: {bgg_id})")
        sleeve_result = scrape_sleeve_data(bgg_id, data['title'])
        data['sleeve_data'] = sleeve_result
        logger.info(f"Sleeve data fetch result: {sleeve_result['status']}")
    except Exception as e:
        logger.error(f"Failed to fetch sleeve data for {data['title']}: {e}")
        data['sleeve_data'] = {'status': 'error', 'card_types': [], 'notes': None}

    return data


def _get_game_classification(item) -> str:
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
