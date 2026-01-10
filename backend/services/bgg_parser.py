"""
BoardGameGeek XML Parser
Focused parsing functions for BGG API XML responses
Each function handles one specific parsing concern with clear inputs/outputs
"""
import html
import re
import logging
from typing import Dict, List, Any, Optional
from xml.etree.ElementTree import Element

logger = logging.getLogger(__name__)


def parse_basic_info(item: Element) -> Dict[str, Any]:
    """
    Parse basic game information (title, year, description, is_expansion)

    Args:
        item: XML Element representing a game/expansion

    Returns:
        Dictionary with title, year, description, is_expansion, item_type
    """
    data = {}

    # Check if this item is an expansion
    item_type = item.get("type", "boardgame")
    data["is_expansion"] = item_type == "boardgameexpansion"
    data["item_type"] = item_type

    # Title (prefer primary name)
    name_elem = item.find("name[@type='primary']")
    if name_elem is None:
        name_elem = item.find("name")
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

    # Description (with HTML entity decoding)
    description_elem = item.find("description")
    if description_elem is not None and description_elem.text:
        description = description_elem.text.strip()
        # Decode HTML entities
        description = html.unescape(description)
        # Remove common BGG markup
        description = description.replace("&#10;", "\n")
        description = description.replace("&quot;", '"')
        description = description.replace("&amp;", "&")
        data["description"] = description[:2000] if description else None
    else:
        data["description"] = None

    return data


def parse_images(item: Element) -> Dict[str, Optional[str]]:
    """
    Parse image URLs (thumbnail and full image)

    Args:
        item: XML Element representing a game/expansion

    Returns:
        Dictionary with thumbnail and image URLs (or None)
    """
    data = {}

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

    return data


def parse_player_counts(item: Element) -> Dict[str, Optional[int]]:
    """
    Parse player count information (min/max players)

    Args:
        item: XML Element representing a game/expansion

    Returns:
        Dictionary with players_min and players_max (or None)
    """
    data = {}

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

    return data


def parse_playtime(item: Element) -> Dict[str, Optional[int]]:
    """
    Parse playtime information (min/max playtime, min_age)

    Args:
        item: XML Element representing a game/expansion

    Returns:
        Dictionary with playtime_min, playtime_max, min_age (or None)
    """
    data = {}

    # Playtime
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

    return data


def parse_links(item: Element, link_type: str) -> List[str]:
    """
    Parse link elements of a specific type (categories, mechanics, designers, etc.)

    Args:
        item: XML Element representing a game/expansion
        link_type: Type of link to extract (e.g., 'boardgamecategory', 'boardgamedesigner')

    Returns:
        List of string values for the specified link type
    """
    result = []
    for link in item.findall(f"link[@type='{link_type}']"):
        value = link.attrib.get("value", "").strip()
        if value:
            result.append(value)
    return result


def parse_expansion_relationships(item: Element, title: str, is_expansion: bool) -> Dict[str, Any]:
    """
    Parse expansion relationship data (base game links, expansion links, player modifications)

    Args:
        item: XML Element representing a game/expansion
        title: Game title (for pattern matching)
        is_expansion: Whether this item is an expansion

    Returns:
        Dictionary with base_game_bgg_id, base_game_name, expansion_bgg_ids,
        modifies_players_min, modifies_players_max, expansion_type
    """
    data = {}

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
    if is_expansion:
        title_lower = title.lower()

        # Look for patterns like "5-6 Player" or "5-6 Extension" in title
        player_expansion_pattern = r"(\d+)[-–](\d+)\s*(player|extension)"
        match = re.search(player_expansion_pattern, title_lower)
        if match:
            try:
                data["modifies_players_min"] = int(match.group(1))
                data["modifies_players_max"] = int(match.group(2))
                logger.info(
                    f"Auto-detected player modification for {title}: "
                    f"{data['modifies_players_min']}-{data['modifies_players_max']}"
                )
            except (ValueError, TypeError):
                pass

        # Check if title suggests it's standalone
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
            logger.info(f"Auto-detected standalone expansion for {title}")
        else:
            data["expansion_type"] = "requires_base"

    return data


def parse_statistics(item: Element) -> Dict[str, Any]:
    """
    Parse statistics section (ratings, complexity, BGG rank, game types)

    Args:
        item: XML Element representing a game/expansion

    Returns:
        Dictionary with average_rating, complexity, bgg_rank, users_rated,
        game_type, is_cooperative
    """
    data = {
        "average_rating": None,
        "complexity": None,
        "bgg_rank": None,
        "users_rated": None,
        "game_type": None,
        "is_cooperative": None,
    }

    statistics = item.find("statistics")
    if statistics is None:
        return data

    ratings = statistics.find("ratings")
    if ratings is None:
        return data

    # Average rating
    try:
        rating_elem = ratings.find("average")
        if rating_elem is not None:
            data["average_rating"] = (
                float(rating_elem.attrib.get("value", "")) or None
            )
    except (ValueError, TypeError):
        pass

    # Complexity (weight)
    try:
        weight_elem = ratings.find("averageweight")
        if weight_elem is not None:
            data["complexity"] = (
                float(weight_elem.attrib.get("value", "")) or None
            )
    except (ValueError, TypeError):
        pass

    # Number of users who rated
    try:
        users_rated_elem = ratings.find("usersrated")
        if users_rated_elem is not None:
            data["users_rated"] = (
                int(users_rated_elem.attrib.get("value", "")) or None
            )
    except (ValueError, TypeError):
        pass

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

        # Process results
        if game_types:
            # Sort by rank value and take the best (lowest) rank
            game_types.sort(key=lambda x: x[0])
            best_type = game_types[0][1]
            data["game_type"] = best_type

            # Determine if cooperative based on game type
            if best_type in ("thematic", "cgs"):
                data["is_cooperative"] = None  # Can't determine
            else:
                data["is_cooperative"] = False
        elif not_ranked_category:
            data["game_type"] = not_ranked_category
            data["is_cooperative"] = None  # Can't determine

        # Parse main BGG rank
        if main_rank and main_rank != "Not Ranked":
            try:
                data["bgg_rank"] = int(main_rank)
            except ValueError:
                pass

    return data


def strip_namespace(root: Element) -> None:
    """
    Strip XML namespace from all elements in the tree (modifies in place)

    Args:
        root: Root XML Element to strip namespaces from
    """
    for elem in root.iter():
        # Remove namespace from tag
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]

        # Remove namespace from attributes
        attrib_to_update = {}
        for key, value in list(elem.attrib.items()):
            if '}' in key:
                new_key = key.split('}', 1)[1]
                attrib_to_update[new_key] = value
                del elem.attrib[key]
        elem.attrib.update(attrib_to_update)
