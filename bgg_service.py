# bgg_service.py
import asyncio
import httpx
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

BGG_THING_URL = "https://www.boardgamegeek.com/xmlapi2/thing"

def _int_or_none(val: Optional[str]) -> Optional[int]:
    try:
        return int(val) if val is not None else None
    except ValueError:
        return None

def _attr(elem: Optional[ET.Element], key: str) -> Optional[str]:
    return elem.attrib.get(key) if elem is not None else None

async def fetch_bgg_thing(bgg_id: int) -> Dict[str, Any]:
    """
    Robust BGG fetch:
    - follows redirects (www -> bare domain)
    - retries while BGG queues (202)
    - extracts title, year, players min/max, playtime min/max with fallbacks
    - returns categories list + thumbnail URL
    """
    params = {"id": str(bgg_id), "stats": "1"}
    headers = {"User-Agent": "ManaMeeples/1.0 (+https://manaandmeeples.co.nz)"}

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers=headers
    ) as client:
        for _ in range(6):  # ~12s total
            r = await client.get(BGG_THING_URL, params=params)
            if r.status_code == 202:
                await asyncio.sleep(2)
                continue
            r.raise_for_status()
            xml = (r.text or "").strip()
            if not xml or "<items" not in xml:
                await asyncio.sleep(2)
                continue

            root = ET.fromstring(xml)
            item = root.find("./item")
            if item is None:
                await asyncio.sleep(2)
                continue

            # --- core fields ---
            # title
            title = None
            for n in item.findall("name"):
                if _attr(n, "type") == "primary":
                    title = _attr(n, "value")
                    break
            if not title:
                first = item.find("name")
                title = _attr(first, "value") if first is not None else "Unknown"

            # numbers
            year        = _int_or_none(_attr(item.find("yearpublished"), "value"))
            players_min = _int_or_none(_attr(item.find("minplayers"), "value"))
            players_max = _int_or_none(_attr(item.find("maxplayers"), "value"))
            play_min    = _int_or_none(_attr(item.find("minplaytime"), "value"))
            play_max    = _int_or_none(_attr(item.find("maxplaytime"), "value"))

            # fallback to <playingtime> if min/max missing (your desktop script does this too)
            playing     = _int_or_none(_attr(item.find("playingtime"), "value"))
            if play_min is None and playing is not None:
                play_min = playing
            if play_max is None and playing is not None:
                play_max = playing

            # categories
            categories: List[str] = [
                _attr(l, "value") or ""
                for l in item.findall("link")
                if _attr(l, "type") == "boardgamecategory"
            ]
            categories = [c for c in categories if c]

            # thumbnail
            thumb_text = (item.findtext("thumbnail") or "").strip()

            return {
                "title": title,
                "year": year,
                "players_min": players_min,
                "players_max": players_max,
                "playtime_min": play_min,
                "playtime_max": play_max,
                "thumbnail": thumb_text,
                "categories": categories,
            }

    raise ValueError("BGG item not available after retries")
