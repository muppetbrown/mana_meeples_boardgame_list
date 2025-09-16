import httpx
import xml.etree.ElementTree as ET
import asyncio
from typing import Dict, Any, List, Optional

BGG_THING_URL = "https://www.boardgamegeek.com/xmlapi2/thing"

async def fetch_bgg_thing(bgg_id: int) -> Dict[str, Any]:
    params = {"id": str(bgg_id), "stats": "1"}
    headers = {"User-Agent": "ManaMeeples/1.0 (+https://manaandmeeples.co.nz)"}

    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
        # Retry loop to handle BGG's 202 "queued" and occasional empty responses
        for attempt in range(6):
            r = await client.get(BGG_THING_URL, params=params)
            if r.status_code == 202:
                await asyncio.sleep(2)
                continue
            r.raise_for_status()
            text = (r.text or "").strip()
            if not text or "<items" not in text:
                await asyncio.sleep(2)
                continue

            root = ET.fromstring(text)
            item = root.find("./item")
            if item is None:
                await asyncio.sleep(2)
                continue

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

            def int_or_none(s: Optional[str]):
                try:
                    return int(s) if s is not None else None
                except ValueError:
                    return None

            year       = int_or_none(attr(item.find("yearpublished") or ET.Element("x"), "value"))
            minplayers = int_or_none(attr(item.find("minplayers")     or ET.Element("x"), "value"))
            maxplayers = int_or_none(attr(item.find("maxplayers")     or ET.Element("x"), "value"))
            minplay    = int_or_none(attr(item.find("minplaytime")    or ET.Element("x"), "value"))
            maxplay    = int_or_none(attr(item.find("maxplaytime")    or ET.Element("x"), "value"))
            # Extra fallbacks
            playing = int_or_none(attr(item.find("playingtime") or ET.Element("x"), "value"))
            if minplay is None and playing is not None:
                minplay = playing
            if maxplay is None and playing is not None:
                maxplay = playing


            thumb = (item.findtext("thumbnail") or "").strip()
            cats: List[str] = [
                attr(l, "value")
                for l in item.findall("link")
                if attr(l, "type") == "boardgamecategory"
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

    raise ValueError("BGG item not available after retries")
