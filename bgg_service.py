import httpx
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

BGG_THING_URL = "https://www.boardgamegeek.com/xmlapi2/thing"

async def fetch_bgg_thing(bgg_id: int) -> Dict[str, Any]:
    params = {"id": str(bgg_id), "stats": "1"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(BGG_THING_URL, params=params)
        r.raise_for_status()
    root = ET.fromstring(r.text)
    item = root.find("./item")
    if item is None:
        raise ValueError("BGG item not found")

    def attr(elem, name, default=None):
        return elem.attrib.get(name, default)

    # title
    title = None
    for n in item.findall("name"):
        if attr(n, "type") == "primary":
            title = attr(n, "value")
            break
    if not title:
        n = item.find("name")
        title = attr(n, "value") if n is not None else "Unknown"

    # numbers
    def int_or_none(s: Optional[str]):
        try:
            return int(s) if s is not None else None
        except ValueError:
            return None

    year = int_or_none(attr(item.find("yearpublished") or ET.Element("x"), "value"))
    minplayers = int_or_none(attr(item.find("minplayers") or ET.Element("x"), "value"))
    maxplayers = int_or_none(attr(item.find("maxplayers") or ET.Element("x"), "value"))
    minplay = int_or_none(attr(item.find("minplaytime") or ET.Element("x"), "value"))
    maxplay = int_or_none(attr(item.find("maxplaytime") or ET.Element("x"), "value"))

    # thumbnail + categories
    thumb = (item.findtext("thumbnail") or "").strip()
    cats: List[str] = [
        attr(l, "value") for l in item.findall("link") if attr(l, "type") == "boardgamecategory"
    ]

    return {
        "title": title,
        "year": year,
        "players_min": minplayers,
        "players_max": maxplayers,
        "playtime_min": minplay,
        "playtime_max": maxplay,
        "thumbnail": thumb,
        "categories": cats,
    }
