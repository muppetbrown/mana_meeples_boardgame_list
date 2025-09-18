# bgg_service.py
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import httpx
import logging
import html
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
                
                # Handle BGG's queue system
                if response.status_code in (202, 500, 503):
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
        
        return _extract_comprehensive_game_data(item)
        
    except ET.ParseError as e:
        logger.error(f"XML parse error for game {bgg_id}: {e}")
        raise BGGServiceError(f"Failed to parse BGG response for game {bgg_id}")

def _strip_namespace(root):
    """Remove XML namespaces from element tags"""
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]

def _extract_comprehensive_game_data(item) -> Dict:
    """Extract comprehensive game data from BGG XML response"""
    data = {}
    
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
            
            # BGG Rank
            try:
                ranks = ratings.find("ranks")
                if ranks is not None:
                    # Get overall boardgame rank
                    main_rank = ranks.find("rank[@name='boardgame']")
                    if main_rank is not None:
                        rank_value = main_rank.attrib.get('value', '')
                        if rank_value and rank_value != 'Not Ranked':
                            data['bgg_rank'] = int(rank_value)
                        else:
                            data['bgg_rank'] = None
                    else:
                        data['bgg_rank'] = None
                else:
                    data['bgg_rank'] = None
            except (ValueError, TypeError):
                data['bgg_rank'] = None
            
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
    else:
        # No statistics data
        data['average_rating'] = None
        data['complexity'] = None
        data['bgg_rank'] = None
        data['users_rated'] = None
    
    # Determine if cooperative
    is_cooperative = any('cooperative' in mechanic.lower() for mechanic in mechanics)
    data['is_cooperative'] = is_cooperative
    
    logger.info(f"Successfully extracted comprehensive data for '{data['title']}'")
    
    return data

def _determine_game_type(categories: List[str], mechanics: List[str]) -> str:
    """
    Determine game type based on categories and mechanics
    Enhanced version of your classification system
    """
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
