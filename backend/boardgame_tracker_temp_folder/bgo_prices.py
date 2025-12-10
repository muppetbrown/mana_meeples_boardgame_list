# -*- coding: utf-8 -*-
# bgo_prices.py
# BoardGameOracle (en-NZ) price fetcher
# Modified to read from Excel file 'Boardgame Library.xlsx', tab 'BUY LIST'
# Outputs: data/offers.csv, data/best_prices.csv, data/summary_prices.csv
#
# One-time setup:
#   pip install playwright beautifulsoup4 lxml pandas python-dateutil openpyxl

import asyncio
import json
import os
import re
import unicodedata
import urllib.parse
from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from dateutil.tz import tzlocal
from playwright.async_api import async_playwright

# =========================
# CONFIG – EDIT HERE
# =========================
# Excel file settings
EXCEL_FILE = Path(__file__).parent / "Boardgame Library.xlsx"
EXCEL_TAB = "BUY LIST"

OUT_DIR = Path(__file__).parent / "data"

DELAY_MS = int(os.getenv('DELAY_MS', '800'))            # delay between games
PAGE_WAIT_MS = int(os.getenv('PAGE_WAIT_MS', '800'))    # grace after content appears
QUICK_CHECK_MS = int(os.getenv('QUICK_CHECK_MS', '3000'))  # quick check for content

# Always headless in CI, can be overridden locally
HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true' or os.getenv('CI') == 'true'
VIEWPORT = {"width": 1400, "height": 1200}

BASE = "https://www.boardgameoracle.com/en-NZ"
USER_AGENT = os.getenv('USER_AGENT', "ManaMeeplesPriceCheck/1.3 (+contact=automation@github.com)")

def rnd(x, nd=2):
    """Round a number to a specified number of decimal places, handling None values."""
    try:
        return None if x is None else round(float(x), nd)
    except Exception:
        return None

# ---------- Excel reading ----------
def read_games_from_excel(excel_file, tab_name: str):
    """Read games from Excel file 'BUY LIST' tab"""
    excel_path = Path(excel_file) if not isinstance(excel_file, Path) else excel_file
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    
    try:
        # Read the specific tab
        df = pd.read_excel(excel_path, sheet_name=tab_name, engine='openpyxl')
        print(f"Read {len(df)} rows from Excel tab '{tab_name}'")
        print(f"Columns found: {list(df.columns)}")
        
        # Clean up column names (remove extra spaces, standardize)
        df.columns = df.columns.str.strip()
        
        # Map expected columns - handle different possible column names
        column_mapping = {}
        
        # Find NAME column (required)
        name_candidates = ['NAME', 'Game', 'Title', 'Game Name']
        name_col = None
        for candidate in name_candidates:
            if candidate in df.columns:
                name_col = candidate
                break
        if not name_col:
            raise ValueError(f"Could not find NAME column. Available columns: {list(df.columns)}")
        column_mapping['name'] = name_col
        
        # Find BGO LINK column (required)
        bgo_candidates = ['BGO LINK', 'BGO_LINK', 'BGO Link', 'Link', 'URL', 'BGO URL']
        bgo_col = None
        for candidate in bgo_candidates:
            if candidate in df.columns:
                bgo_col = candidate
                break
        if not bgo_col:
            raise ValueError(f"Could not find BGO LINK column. Available columns: {list(df.columns)}")
        column_mapping['url'] = bgo_col

        print(f"Column mapping: {column_mapping}")

        # Extract and clean the data
        rows = []
        for idx, row in df.iterrows():
            name = str(row[column_mapping['name']]).strip() if pd.notna(row[column_mapping['name']]) else ""
            url = str(row[column_mapping['url']]).strip() if pd.notna(row[column_mapping['url']]) else ""

            # Skip rows with missing essential data or invalid URLs
            if not name or not url or url in ['#N/A', 'nan', 'None']:
                continue
            if not url.startswith('http'):
                continue

            rows.append({
                "name": name,
                "url": url,
                "excel_row": idx + 2  # +2 because pandas is 0-indexed and Excel starts at 1, plus header row
            })
        
        if not rows:
            raise ValueError("No valid games found in Excel file. Check that NAME and BGO LINK columns have data.")
        
        print(f"Successfully parsed {len(rows)} games from Excel")
        return rows
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        raise

# ---------- Banners / region ----------
async def dismiss_banners(page):
    """Attempt to dismiss cookie banners and select NZ region."""
    candidates = [
        "button:has-text('Accept')",
        "button:has-text('I agree')",
        "button:has-text('Got it')",
        "text=/^Accept all$/i",
        "[aria-label='accept cookies']",
    ]
    for sel in candidates:
        try:
            btn = page.locator(sel)
            if await btn.count():
                await btn.first.click(timeout=1500)
                await page.wait_for_timeout(400)
        except Exception:
            pass

    try:
        nz = page.locator("a[href*='/en-NZ'], button:has-text('New Zealand')")
        if await nz.count():
            await nz.first.click(timeout=1500)
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
    except Exception:
        pass

# ---------- Fetch BGO product page ----------
async def fetch_page(context, url: str, wait_ms: int):
    """
    Fetch a BoardGameOracle product page and return HTML content.

    Args:
        context: Playwright browser context
        url: Product URL to fetch
        wait_ms: Milliseconds to wait after page load

    Returns:
        Tuple of (status_code, html_content)
    """
    page = await context.new_page()
    await page.set_extra_http_headers({"User-Agent": USER_AGENT, "Referer": BASE})
    try:
        # Visit base site first to establish session
        await page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
        await dismiss_banners(page)
        await page.wait_for_timeout(500)

        # Navigate to product page
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000, referer=BASE)
        if "/price/" not in page.url:
            await page.evaluate("(u) => window.location.assign(u)", url)
            await page.wait_for_load_state("domcontentloaded", timeout=30000)

        # Quick check for "no prices" indicators
        try:
            no_data_indicators = await page.locator("text=/no prices found|no retailers|not available in NZ|region not supported/i").count()
            if no_data_indicators > 0:
                print("  (No NZ prices available - detected early)")
                html = await page.content()
                status = resp.status if resp else None
                return status, html
        except Exception:
            pass

        # Scroll to load dynamic content
        for _ in range(2):  # Reduced from 3 to 2 scrolls
            await page.mouse.wheel(0, 1500)
            await page.wait_for_timeout(200)  # Reduced from 400ms

        # Wait for price table or store links to appear (with shorter timeout)
        content_found = False
        for sel in [
            "tbody[class*='MuiTableBody-root'] tr",
            "a[aria-label='go-to-store']",
            "span:has-text('In stock')",
            "span:has-text('Out of stock')",
        ]:
            try:
                await page.wait_for_selector(sel, timeout=QUICK_CHECK_MS)
                content_found = True
                break
            except Exception:
                continue

        # If content found quickly, wait a bit for everything to load
        # Otherwise, skip the extra wait (likely no data available)
        if content_found:
            await page.wait_for_timeout(wait_ms)
        else:
            await page.wait_for_timeout(500)  # Minimal wait if no content

        # Only save debug files if not in CI or debug mode is enabled
        if not os.getenv('CI') or os.getenv('DEBUG_MODE'):
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(OUT_DIR / "debug_current.png"))
            with open(OUT_DIR / "debug_current.html", "w", encoding="utf-8") as fh:
                fh.write(await page.content())

        html = await page.content()
        status = resp.status if resp else None
        return status, html
    finally:
        await page.close()

# ---------- Parse BGO offers ----------
def parse_offers(html: str, game_name: str, page_url: str):
    """
    Parse price offers from BoardGameOracle HTML.

    Args:
        html: Page HTML content
        game_name: Name of the game
        page_url: URL of the page

    Returns:
        List of offer dictionaries
    """
    soup = BeautifulSoup(html, "lxml")
    tbody = soup.select_one("tbody[class*='MuiTableBody-root']")
    if not tbody:
        return []

    offers = []
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        # Extract store name
        store_text = ""
        if len(tds) >= 2:
            a = tds[1].find("a")
            store_text = (a.get_text(" ", strip=True) if a else tds[1].get_text(" ", strip=True))

        # Extract price
        price_text = ""
        price_value = None
        if len(tds) >= 3:
            price_ps = tds[2].find_all("p")
            price_text = (price_ps[-1].get_text(" ", strip=True) if price_ps else tds[2].get_text(" ", strip=True))
            clean_price = re.sub(r'[^\d.,]', '', price_text)
            clean_price = clean_price.replace(',', '')
            m = re.search(r'(\d+(?:\.\d{1,2})?)', clean_price)
            price_value = float(m.group(1)) if m else None

        # Extract availability
        availability_text = ""
        if len(tds) >= 7:
            span = tds[6].find("span")
            availability_text = span.get_text(strip=True) if span else tds[6].get_text(" ", strip=True)

        # Extract store link
        store_link = None
        last_td = tds[-1]
        a = last_td.find("a", href=True) or tr.find("a", href=True)
        if a and a.has_attr("href"):
            store_link = a["href"]

        if store_text or price_value is not None:
            offers.append({
                "game": game_name,
                "store": store_text,
                "price_nzd": price_value,
                "raw_price": price_text,
                "availability": availability_text,
                "store_link": store_link,
                "page_url": page_url
            })

    return offers

# ---------- Try to read 'Mean' / 'Disc-mean' from DOM (best-effort) ----------
def parse_site_mean(html: str):
    """Parse the mean price from BoardGameOracle page HTML."""
    soup = BeautifulSoup(html, "lxml")
    def num_from(el):
        if not el:
            return None
        txt = el.get_text(" ", strip=True)
        m = re.search(r"(\d+(?:[.,]\d+)?)", txt.replace(",", ""))
        return float(m.group(1)) if m else None

    for div in soup.find_all("div", class_=lambda c: c and "MuiGrid-item" in str(c)):
        p = div.find("p")
        if p and p.get_text(strip=True).lower() == "mean":
            sib = div.find_next_sibling("div")
            val = num_from(sib.find("p") if sib else None)
            if val is not None:
                return val
            val = num_from(p.find_next("p"))
            if val is not None:
                return val

    txt = soup.get_text(" ", strip=True)
    m = re.search(r"\bmean\b[^0-9]*([0-9]+(?:[.,][0-9]+)?)", txt, flags=re.I)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except Exception:
            return None
    return None

def parse_site_disc_mean(html: str):
    """Parse the discount-mean percentage from BoardGameOracle page HTML."""
    soup = BeautifulSoup(html, "lxml")

    def norm(s: str) -> str:
        s = unicodedata.normalize("NFKC", s or "")
        s = s.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\u00A0", " ")
        return s.strip().lower()

    def is_label(s: str) -> bool:
        t = norm(s).replace(" ", "")
        return ("disc-mean" in t) or ("discmean" in t)

    def num_from(el):
        if not el:
            return None
        txt = el.get_text(" ", strip=True)
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*%?", txt.replace(",", ""))
        return float(m.group(1)) if m else None

    for div in soup.find_all("div", class_=lambda c: c and "MuiGrid-item" in str(c)):
        p = div.find("p")
        if p and is_label(p.get_text()):
            sib = div.find_next_sibling("div")
            v = num_from(sib.find("p") if sib else None)
            if v is not None:
                return v
            v = num_from(p.find_next("p"))
            if v is not None:
                return v

    for p in soup.find_all("p"):
        if is_label(p.get_text()):
            v = num_from(p.find_next("p"))
            if v is not None:
                return v

    txt = norm(soup.get_text(" ", strip=True))
    m = re.search(r"disc-?\s*mean[^0-9]*([0-9]+(?:[.,][0-9]+)?)", txt, flags=re.I)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except Exception:
            return None
    return None

# ---------- JSON/tRPC helpers (robust) ----------
def _to_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", "").replace("%", "").strip()
        return float(x)
    except Exception:
        return None

def _deep_find(obj, want_keys):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in want_keys:
                val = _to_float(v)
                if val is not None:
                    return val
            found = _deep_find(v, want_keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _deep_find(v, want_keys)
            if found is not None:
                return found
    return None

def _json_loads_loose(raw: str):
    """Attempt to parse JSON from potentially malformed input."""
    s = raw.lstrip(")]}',\n\r\t ").strip()
    try:
        return json.loads(s)
    except Exception:
        pass

    payloads = []
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        if line and not line.startswith("{") and "{" in line:
            line = line[line.index("{"):]
        try:
            payloads.append(json.loads(line))
        except Exception:
            continue

    if payloads:
        return payloads
    return None

def _trpc_collect_payloads(parsed):
    if parsed is None:
        return []
    if isinstance(parsed, list):
        return parsed
    return [parsed]

def _trpc_unwrap_json_nodes(node):
    if isinstance(node, dict):
        cur = node
        if "result" in cur and isinstance(cur["result"], dict):
            cur = cur["result"]
        if "data" in cur and isinstance(cur["data"], dict):
            cur = cur["data"]
        if "json" in cur:
            j = cur["json"]
            if isinstance(j, str):
                try:
                    j = json.loads(j)
                except Exception:
                    j = None
            if isinstance(j, (dict, list)):
                yield j; return
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from _trpc_unwrap_json_nodes(item)

def _product_key_from_url(url: str):
    try:
        path = urllib.parse.urlparse(url).path
        parts = [p for p in path.split("/") if p]
        i = parts.index("price")
        return parts[i+1] if i + 1 < len(parts) else None
    except Exception:
        return None

async def fetch_pricestats_via_page(page, product_url: str, debug_slug: str = None) -> dict:
    """
    Fetch price statistics from BoardGameOracle API using tRPC endpoints.

    Returns dict with keys: mean, disc_mean_pct, low
    """
    key = _product_key_from_url(product_url)
    if not key:
        return {"mean": None, "disc_mean_pct": None, "low": None}
    if product_url not in page.url:
        await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)

    batched_input = {"0": {"region": "nz", "key": key, "range": "7d"},
                     "1": {"region": "nz", "key": key}}
    qs = urllib.parse.quote(json.dumps(batched_input, separators=(",", ":")))
    url = f"/api/trpc/pricehistory.list,pricestats.get?batch=1&input={qs}"

    js = """
    async (u) => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const r = await fetch(u, {
          credentials: "include",
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        const txt = await r.text();
        return txt;
      } catch (e) {
        return '{"error": "' + e.message + '"}';
      }
    }
    """
    raw = await page.evaluate(js, url)
    raw_stripped = raw.lstrip(")]}',\n\r\t ")

    # Only save debug files if not in CI or debug mode is enabled
    try:
        if debug_slug and (not os.getenv('CI') or os.getenv('DEBUG_MODE')):
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            with open(OUT_DIR / f"stats_{debug_slug}.json", "w", encoding="utf-8") as fh:
                fh.write(raw_stripped)
    except Exception:
        pass

    parsed = _json_loads_loose(raw_stripped)
    payloads = _trpc_collect_payloads(parsed)

    mean = None
    disc_mean = None
    low = None
    for pl in payloads:
        for inner in _trpc_unwrap_json_nodes(pl):
            if inner is None:
                continue
            mean = mean or _deep_find(inner, {"mean", "avg", "average"})
            disc_mean = disc_mean or _deep_find(inner, {"discmean", "disc_mean", "discmeanpct", "discountmean", "discountpct"})
            low = low or _deep_find(inner, {"low", "min", "lowest", "minprice"})

    return {"mean": mean, "disc_mean_pct": disc_mean, "low": low}

# =========================
# MAIN
# =========================
async def run():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        games = read_games_from_excel(EXCEL_FILE, EXCEL_TAB)
        print(f"Found {len(games)} games in Excel file")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Make sure to place your '{EXCEL_FILE}' file in the same directory as this script.")
        return
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    checked_at = datetime.now(tzlocal()).isoformat(timespec="seconds")
    all_offers = []
    site_means = {}
    site_disc_means = {}
    site_lows = {}

    start_time = datetime.now()

    # Browser settings
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-sandbox",
    ]
    
    if os.getenv('CI'):
        browser_args.extend([
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
        ])

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=browser_args,
        )
        context = await browser.new_context(
            viewport=VIEWPORT,
            locale="en-NZ",
            timezone_id="Pacific/Auckland",
            user_agent=USER_AGENT,
        )
        # Create a reusable page for API calls to avoid repeated page creation
        api_page = await context.new_page()
        try:
            for i, g in enumerate(games, start=1):
                game_start = datetime.now()
                print(f"[{i}/{len(games)}] Fetching: {g['name']} → {g['url']}")

                try:
                    status, html = await fetch_page(context, g["url"], PAGE_WAIT_MS)

                    # Try DOM parsing
                    site_means[g["name"]] = parse_site_mean(html)
                    site_disc_means[g["name"]] = parse_site_disc_mean(html)

                    # BGO offers
                    offers = parse_offers(html, g["name"], g["url"])
                    if not offers:
                        print(f"  No BGO offers parsed for {g['name']}")
                    else:
                        print(f"  Parsed {len(offers)} BGO offers")
                    all_offers.extend(offers)

                    # API stats - reuse the same page for all API calls
                    slug = re.sub(r"[^a-z0-9]+", "-", g["name"].lower()).strip("-")
                    try:
                        # Only navigate if we're not already on a BGO page
                        if not api_page.url.startswith(BASE):
                            await api_page.goto(BASE, wait_until="domcontentloaded", timeout=30000)
                            await dismiss_banners(api_page)
                        stats = await fetch_pricestats_via_page(api_page, g["url"], debug_slug=slug)
                    except Exception as e:
                        print(f"  Warning: Could not fetch API stats: {e}")
                        stats = {"mean": None, "disc_mean_pct": None, "low": None}

                    if stats.get("mean") is not None:
                        site_means[g["name"]] = stats["mean"]
                    if stats.get("disc_mean_pct") is not None:
                        site_disc_means[g["name"]] = stats["disc_mean_pct"]
                    if stats.get("low") is not None:
                        site_lows[g["name"]] = stats["low"]

                    if g["name"] not in site_lows:
                        prices = [o["price_nzd"] for o in offers if o.get("price_nzd") is not None]
                        if prices:
                            site_lows[g["name"]] = min(prices)

                    # Print timing info
                    game_duration = (datetime.now() - game_start).total_seconds()
                    print(f"  ✓ Completed in {game_duration:.1f}s")

                except Exception as e:
                    print(f"  Error processing {g['name']}: {e}")
                    continue

                await asyncio.sleep(DELAY_MS / 1000.0)
        finally:
            await api_page.close()
            await context.close()
            await browser.close()

    if not all_offers:
        print("No offers found.")
        return

    # Build offers DataFrame
    df = pd.DataFrame(all_offers)
    df.insert(0, "checked_at", checked_at)

    def is_in_stock(x):
        if pd.isna(x) or x == "":
            return True  # Assume available if unknown
        if not isinstance(x, str):
            return True  # Assume available if not a string
        t = str(x).lower()
        if "out of stock" in t or "sold out" in t:
            return False
        return True  # Default to in stock

    df["in_stock"] = df["availability"].apply(is_in_stock)

    # Save outputs
    offers_out = OUT_DIR / "offers.csv"
    best_out = OUT_DIR / "best_prices.csv"
    summary_out = OUT_DIR / "summary_prices.csv"

    df.to_csv(offers_out, index=False, encoding="utf-8")
    print(f"Wrote {offers_out}")

    # Best price per game
    best_rows = []
    for game, gdf in df.groupby("game"):
        gdf_price = gdf.dropna(subset=["price_nzd"])
        choice = None
        if not gdf_price.empty:
            in_stock = gdf_price[gdf_price["in_stock"] == True]
            if not in_stock.empty:
                choice = in_stock.sort_values("price_nzd").iloc[0]
            else:
                choice = gdf_price.sort_values("price_nzd").iloc[0]
        if choice is not None:
            best_rows.append({
                "checked_at": checked_at,
                "game": game,
                "best_price_nzd": float(choice["price_nzd"]),
                "store": str(choice["store"]),
                "availability": str(choice["availability"]),
                "store_link": str(choice["store_link"]),
                "page_url": str(choice["page_url"])
            })
        else:
            best_rows.append({
                "checked_at": checked_at,
                "game": game,
                "best_price_nzd": None,
                "store": "",
                "availability": "No price parsed",
                "store_link": "",
                "page_url": gdf["page_url"].iloc[0] if len(gdf) else ""
            })

    pd.DataFrame(best_rows).to_csv(best_out, index=False, encoding="utf-8")
    print(f"Wrote {best_out}")

    # Summary with all metrics
    summary_rows = []
    for game, gdf in df.groupby("game"):
        gdfp = gdf.dropna(subset=["price_nzd"])
        try:
            mean_all_offers = float(gdfp["price_nzd"].mean()) if not gdfp.empty else None
        except (ValueError, TypeError):
            mean_all_offers = None
        instock = gdfp[gdfp["in_stock"] == True]
        mean_instock_offers = float(instock["price_nzd"].mean()) if not instock.empty else None

        best_in = None
        best_store = ""
        if not instock.empty:
            row_ = instock.sort_values("price_nzd").iloc[0]
            best_in = float(row_["price_nzd"])
            best_store = str(row_["store"])

        site_mean_val = site_means.get(game)
        if site_mean_val is None:
            if mean_instock_offers is not None:
                site_mean_val = mean_instock_offers
            elif mean_all_offers is not None:
                site_mean_val = mean_all_offers

        disc_abs = (site_mean_val - best_in) if (site_mean_val is not None and best_in is not None) else None
        disc_pct = ((disc_abs / site_mean_val) * 100.0) if (disc_abs is not None and site_mean_val not in (None, 0)) else None

        site_disc_mean_pct = site_disc_means.get(game)
        site_low_val = site_lows.get(game)

        site_disc_mean_calc = None
        if site_disc_mean_pct is None and (site_mean_val is not None and site_low_val is not None and site_mean_val != 0):
            site_disc_mean_calc = ((site_mean_val - site_low_val) / site_mean_val) * 100.0

        baseline_disc_mean = site_disc_mean_pct if site_disc_mean_pct is not None else site_disc_mean_calc
        delta_vs_site_disc_mean_pp = ((disc_pct - baseline_disc_mean)
                                      if (disc_pct is not None and baseline_disc_mean is not None) else None)

        summary_rows.append({
            "checked_at": checked_at,
            "game": game,
            "site_mean_nzd": rnd(site_mean_val, 2),
            "best_in_stock_nzd": rnd(best_in, 2),
            "best_in_stock_store": best_store,
            "discount_abs_vs_site_mean": rnd(disc_abs, 2),
            "discount_pct_vs_site_mean": rnd(disc_pct, 2),
            "mean_nzd_all_offers_calc": rnd(mean_all_offers, 2),
            "mean_nzd_in_stock_calc": rnd(mean_instock_offers, 2),
            "site_disc_mean_pct": rnd(site_disc_mean_pct, 2),
            "site_disc_mean_calc_pct": rnd(site_disc_mean_calc, 2),
            "site_low_nzd": rnd(site_low_val, 2),
            "delta_vs_site_disc_mean_pp": rnd(delta_vs_site_disc_mean_pp, 2),
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_df = summary_df.sort_values(
        by=["delta_vs_site_disc_mean_pp", "discount_pct_vs_site_mean"],
        ascending=[False, False],
        na_position="last"
    )
    summary_df.to_csv(summary_out, index=False, encoding="utf-8")
    print(f"Wrote {summary_out}")

    total_duration = (datetime.now() - start_time).total_seconds()
    avg_per_game = total_duration / len(games) if games else 0

    print("\n" + "="*60)
    print("Summary:")
    print(f"- Processed {len(games)} games from Excel")
    print(f"- Found {len(all_offers)} total offers")
    print(f"- Generated 3 output files in {OUT_DIR}")
    print(f"- Total time: {total_duration:.1f}s ({avg_per_game:.1f}s per game)")
    print("="*60)

    # Show top deals
    top_deals = summary_df[
        (summary_df['discount_pct_vs_site_mean'].notna()) &
        (summary_df['discount_pct_vs_site_mean'] > 10) &
        (summary_df['best_in_stock_nzd'].notna())
    ].head(5)

    if not top_deals.empty:
        print(f"\nTop {len(top_deals)} deals found:")
        for _, row in top_deals.iterrows():
            discount = row['discount_pct_vs_site_mean']
            price = row['best_in_stock_nzd']
            store = row['best_in_stock_store']
            game = row['game']
            print(f"  - {game}: ${price:.2f} at {store} ({discount:.1f}% off)")

if __name__ == "__main__":
    asyncio.run(run())