# bgg_service.py
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
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
    
    async with httpx.AsyncClient(timeout=float(HTTP_TIMEOUT)) as client:
        for attempt in range(retries):
            try:
                logger.info(f"Fetching BGG data for game {bgg_id} (attempt {attempt + 1})")
                response = await client.get(url, params=params)

                # Handle BGG's queue system and rate limiting
                # 401 is often used by BGG for rate limiting (not actual auth)
                # 202 = request queued, 500/503 = temporary server issues
                if response.status_code in (202, 401, 500, 503):
                    delay = (2 ** attempt) + (attempt * 0.5)  # Exponential backoff with jitter
                    logger.warning(f"BGG returned {response.status_code} for game {bgg_id}, retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue

                if response.status_code == 400:
                    raise BGGServiceError(f"Invalid BGG ID: {bgg_id}")

                response.raise_for_status()
                break
                
            except httpx.TimeoutException:
                logger.error(f"Timeout fetching BGG data for game {bgg_id}")
                if attempt == retries - 1:
                    raise BGGServiceError(f"Timeout fetching game {bgg_id}")
                delay = (2 ** attempt) + (attempt * 0.5)  # Exponential backoff with jitter
                await asyncio.sleep(delay)
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching BGG data for game {bgg_id}: {e}")
                if attempt == retries - 1:
                    raise BGGServiceError(f"Failed to fetch game {bgg_id}: {e}")
                delay = (2 ** attempt) + (attempt * 0.5)  # Exponential backoff with jitter
                await asyncio.sleep(delay)
    
    # Parse XML response
    try:
        root = ET.fromstring(response.text)
        _strip_namespace(root)
        
        item = root.find("item")
        if item is None:
            raise BGGServiceError(f"No game data found for BGG ID {bgg_id}")
        
        return _extract_comprehensive_game_data(item, bgg_id)
        
    except ET.ParseError as e:
        logger.error(f"XML parse error for game {bgg_id}: {e}")
        raise BGGServiceError(f"Failed to parse BGG response for game {bgg_id}")

def _strip_namespace(root):
    """Remove XML namespaces from element tags"""
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]

def _extract_comprehensive_game_data(item, bgg_id: int) -> Dict:
    """Extract comprehensive game data from BGG XML response"""
    data = {}
    data['bgg_id'] = bgg_id
    
    # Basic information
    name_elem = item.find("name[@type='primary']") or item.find("name")
    data['title'] = name_elem.attrib.get('value', '') if name_elem is not None else ''
    
    # Year published
    year_elem = item.find("yearpublished")
    try:
        data['year'] = int(year_elem.attrib.get('value', '')) if year_elem is not None else None
    except (ValueError, TypeError):
        data['year'] = None
    
    # Description
    description_elem = item.find("description")
    if description_elem is not None and description_elem.text:
        # Clean up BGG's HTML-like description text
        description = description_elem.text.strip()
        # Decode HTML entities first
        description = html.unescape(description)
        # Remove common BGG markup
        description = description.replace('&#10;', '\n')
        description = description.replace('&quot;', '"')
        description = description.replace('&amp;', '&')
        data['description'] = description[:2000] if description else None
    else:
        data['description'] = None
    
    # Images
    thumbnail_elem = item.find("thumbnail")
    data['thumbnail'] = thumbnail_elem.text.strip() if thumbnail_elem is not None and thumbnail_elem.text else None
    
    image_elem = item.find("image")
    data['image'] = image_elem.text.strip() if image_elem is not None and image_elem.text else None
    
    # Player counts
    try:
        min_players_elem = item.find("minplayers")
        data['players_min'] = int(min_players_elem.attrib.get('value', '')) if min_players_elem is not None else None
        
        max_players_elem = item.find("maxplayers")
        data['players_max'] = int(max_players_elem.attrib.get('value', '')) if max_players_elem is not None else None
    except (ValueError, TypeError):
        data['players_min'] = None
        data['players_max'] = None
    
    # Play time
    try:
        min_time_elem = item.find("minplaytime")
        max_time_elem = item.find("maxplaytime")
        
        if min_time_elem is not None and max_time_elem is not None:
            data['playtime_min'] = int(min_time_elem.attrib.get('value', '')) or None
            data['playtime_max'] = int(max_time_elem.attrib.get('value', '')) or None
        else:
            # Fallback to playing time
            play_time_elem = item.find("playingtime")
            if play_time_elem is not None:
                playtime = int(play_time_elem.attrib.get('value', '')) or None
                data['playtime_min'] = playtime
                data['playtime_max'] = playtime
            else:
                data['playtime_min'] = None
                data['playtime_max'] = None
    except (ValueError, TypeError):
        data['playtime_min'] = None
        data['playtime_max'] = None
    
    # Minimum age
    try:
        age_elem = item.find("minage")
        data['min_age'] = int(age_elem.attrib.get('value', '')) if age_elem is not None else None
    except (ValueError, TypeError):
        data['min_age'] = None
    
    # Categories (themes)
    categories = []
    for link in item.findall("link[@type='boardgamecategory']"):
        category = link.attrib.get('value', '').strip()
        if category:
            categories.append(category)
    data['categories'] = categories
    
    # Mechanics
    mechanics = []
    for link in item.findall("link[@type='boardgamemechanic']"):
        mechanic = link.attrib.get('value', '').strip()
        if mechanic:
            mechanics.append(mechanic)
    data['mechanics'] = mechanics
    
    # Designers
    designers = []
    for link in item.findall("link[@type='boardgamedesigner']"):
        designer = link.attrib.get('value', '').strip()
        if designer:
            designers.append(designer)
    data['designers'] = designers
    
    # Publishers
    publishers = []
    for link in item.findall("link[@type='boardgamepublisher']"):
        publisher = link.attrib.get('value', '').strip()
        if publisher:
            publishers.append(publisher)
    data['publishers'] = publishers
    
    # Artists
    artists = []
    for link in item.findall("link[@type='boardgameartist']"):
        artist = link.attrib.get('value', '').strip()
        if artist:
            artists.append(artist)
    data['artists'] = artists
    
    # Statistics (ratings, complexity, etc.)
    statistics = item.find("statistics")
    if statistics is not None:
        ratings = statistics.find("ratings")
        if ratings is not None:
            # Average rating
            try:
                rating_elem = ratings.find("average")
                if rating_elem is not None:
                    data['average_rating'] = float(rating_elem.attrib.get('value', '')) or None
                else:
                    data['average_rating'] = None
            except (ValueError, TypeError):
                data['average_rating'] = None
            
            # Complexity (weight)
            try:
                weight_elem = ratings.find("averageweight")
                if weight_elem is not None:
                    data['complexity'] = float(weight_elem.attrib.get('value', '')) or None
                else:
                    data['complexity'] = None
            except (ValueError, TypeError):
                data['complexity'] = None
            
            # BGG Rank and Game Type from ranks
            ranks = ratings.find("ranks")
            if ranks is not None:
                main_rank = ''
                game_types = []
                has_consensus = False
                not_ranked_category = None

                # First pass: check if any category has a numerical rank (consensus)
                for rank in ranks.findall("rank"):
                    rank_name = rank.attrib.get('name', '')
                    rank_value = rank.attrib.get('value', '')

                    if rank_name == 'boardgame' and rank_value and rank_value != 'Not Ranked':
                        main_rank = rank_value
                    elif rank_name != 'boardgame' and rank_value and rank_value != 'Not Ranked' and rank_value.isdigit():
                        has_consensus = True
                        break

                # Second pass: collect game types based on consensus
                for rank in ranks.findall("rank"):
                    rank_name = rank.attrib.get('name', '')
                    rank_value = rank.attrib.get('value', '')

                    if rank_name != 'boardgame':
                        if has_consensus:
                            # Enough votes for consensus - use ALL ranked categories
                            if rank_value and rank_value != 'Not Ranked' and rank_value.isdigit():
                                game_types.append((int(rank_value), rank_name))
                        else:
                            # Not enough votes - use the "Not Ranked" category
                            if rank_value == 'Not Ranked' and not_ranked_category is None:
                                not_ranked_category = rank_name

                try:
                    data['bgg_rank'] = int(main_rank) if main_rank else None
                except (ValueError, TypeError):
                    data['bgg_rank'] = None

                # Determine final game type
                if has_consensus and game_types:
                    # Sort by rank and convert to friendly names
                    game_types.sort(key=lambda x: x[0])  # Sort by numerical rank

                    friendly_names = {
                        'strategygames': 'Strategy',
                        'familygames': 'Family',
                        'thematic': 'Thematic',
                        'partygames': 'Party',
                        'abstracts': 'Abstract',
                        'cgs': 'Card Game',
                        'childrensgames': "Children's",
                        'wargames': 'War Game'
                    }

                    friendly_categories = []
                    for rank_num, category in game_types:
                        friendly_name = friendly_names.get(category, category.title())
                        friendly_categories.append(friendly_name)

                    data['game_type'] = ' • '.join(friendly_categories)

                    if config.SAVE_DEBUG_INFO:
                        print(f"    Consensus found - ranked categories: {[cat for _, cat in game_types]}")
                        print(f"    Combined game type: {data['game_type']}")

                elif not_ranked_category:
                    # No consensus - use "Not Ranked" category + first boardgame category
                    friendly_names = {
                        'strategygames': 'Strategy',
                        'familygames': 'Family',
                        'thematic': 'Thematic',
                        'partygames': 'Party',
                        'abstracts': 'Abstract',
                        'cgs': 'Card Game',
                        'childrensgames': "Children's",
                        'wargames': 'War Game'
                    }

                    rank_type = friendly_names.get(not_ranked_category, not_ranked_category.title())

                    # Get first boardgame category for additional context
                    first_category = categories[0] if categories else None

                    if first_category:
                        data['game_type'] = f"{rank_type} • {first_category}"
                    else:
                        data['game_type'] = rank_type

                    if config.SAVE_DEBUG_INFO:
                        print(f"    No consensus - using Not Ranked category: {not_ranked_category}")
                        print(f"    First boardgame category: {first_category}")
                        print(f"    Combined game type: {data['game_type']}")
                else:
                    # Fallback to our classification system
                    data['game_type'] = _get_game_classification(item)
                    if config.SAVE_DEBUG_INFO:
                        print(f"    No BGG ranking data, using fallback classification: {data['game_type']}")

                if config.SAVE_DEBUG_INFO:
                    print(f"    Found main rank: {data['bgg_rank']}")
            else:
                if config.SAVE_DEBUG_INFO:
                    print(f"    ranks element not found in ratings")
                # Fallback for both rank and game type
                data['bgg_rank'] = None
                data['game_type'] = _get_game_classification(item)
            
            # Number of ratings
            try:
                users_rated_elem = ratings.find("usersrated")
                if users_rated_elem is not None:
                    data['users_rated'] = int(users_rated_elem.attrib.get('value', '')) or None
                else:
                    data['users_rated'] = None
            except (ValueError, TypeError):
                data['users_rated'] = None
        else:
            # No ratings data
            data['average_rating'] = None
            data['complexity'] = None
            data['bgg_rank'] = None
            data['users_rated'] = None
            data['game_type'] = _get_game_classification(item)
    else:
        # No statistics data
        data['average_rating'] = None
        data['complexity'] = None
        data['bgg_rank'] = None
        data['users_rated'] = None
        data['game_type'] = _get_game_classification(item)
    
    # Game classification - ensure game_type is always set
    if 'game_type' not in data or not data['game_type']:
        data['game_type'] = _get_game_classification(item)

    # Determine if cooperative
    is_cooperative = any('cooperative' in mechanic.lower() for mechanic in mechanics)
    data['is_cooperative'] = is_cooperative

    logger.info(f"Successfully extracted comprehensive data for '{data['title']}'")

    return data

def _get_game_classification(item) -> str:
    """
    Fallback game classification system based on categories and mechanics
    when BGG ranking data is not available
    """
    # Extract categories and mechanics from the item
    categories = []
    for link in item.findall("link[@type='boardgamecategory']"):
        category = link.attrib.get('value', '').strip()
        if category:
            categories.append(category)

    mechanics = []
    for link in item.findall("link[@type='boardgamemechanic']"):
        mechanic = link.attrib.get('value', '').strip()
        if mechanic:
            mechanics.append(mechanic)

    # Primary game types (most recognizable)
    primary_types = {
        'party': ['party game'],
        'family': ['children\'s game', 'family game'],
        'coop': ['cooperative game'],
        'social_deduction': ['social deduction', 'bluffing', 'deduction'],
        'dexterity': ['dexterity', 'real time'],
        'trivia': ['trivia'],
        'abstract': ['abstract strategy'],
        'war': ['wargame', 'world war'],
        'economic': ['economic'],
        'thematic': ['thematic'],
    }

    # Check categories first for primary type
    for game_type, keywords in primary_types.items():
        for keyword in keywords:
            if any(keyword in cat.lower() for cat in categories):
                type_names = {
                    'party': 'Party',
                    'family': 'Family',
                    'coop': 'Co-op',
                    'social_deduction': 'Social Deduction',
                    'dexterity': 'Dexterity',
                    'trivia': 'Trivia',
                    'abstract': 'Abstract',
                    'war': 'War Game',
                    'economic': 'Economic',
                    'thematic': 'Thematic'
                }
                return type_names[game_type]

    # Check mechanics for cooperative games
    if any('cooperative' in mech.lower() for mech in mechanics):
        return 'Co-op'

    # Mechanic-based classification
    mechanic_priority = [
        ('deck building', 'Deck Builder'),
        ('bag building', 'Bag Builder'),
        ('worker placement', 'Worker Placement'),
        ('tile placement', 'Tile Laying'),
        ('roll and write', 'Roll & Write'),
        ('flip and write', 'Roll & Write'),
        ('drafting', 'Drafting'),
        ('trick-taking', 'Trick Taking'),
        ('area control', 'Area Control'),
        ('area majority', 'Area Control'),
        ('route building', 'Route Building'),
        ('network building', 'Route Building'),
        ('engine building', 'Engine Builder'),
        ('tableau building', 'Engine Builder'),
        ('pattern building', 'Pattern Builder'),
        ('set collection', 'Set Collection'),
        ('auction', 'Auction'),
        ('trading', 'Trading'),
    ]

    for keyword, display_name in mechanic_priority:
        if any(keyword in mech.lower() for mech in mechanics):
            return display_name

    # Fallback to strategy if nothing else matches
    return 'Strategy'
