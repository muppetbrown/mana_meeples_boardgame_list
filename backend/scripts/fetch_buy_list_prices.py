# -*- coding: utf-8 -*-
# fetch_buy_list_prices.py
# BoardGameOracle (en-NZ) price fetcher for GitHub Actions
# Reads from buy_list_export.csv and outputs JSON for API import
#
# One-time setup:
#   pip install playwright beautifulsoup4 lxml pandas python-dateutil
#   playwright install chromium

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
# CONFIG
# =========================
# CSV input file (exported from database buy list)
CSV_FILE = Path(__file__).parent.parent / "price_data" / "buy_list_export.csv"

# JSON output file
OUT_DIR = Path(__file__).parent.parent / "price_data"
OUT_JSON = OUT_DIR / "latest_prices.json"

DELAY_MS = int(os.getenv('DELAY_MS', '800'))            # delay between games
PAGE_WAIT_MS = int(os.getenv('PAGE_WAIT_MS', '800'))    # grace after content appears
QUICK_CHECK_MS = int(os.getenv('QUICK_CHECK_MS', '3000'))  # quick check for content

# Always headless in CI, can be overridden locally
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true' or os.getenv('CI') == 'true'
VIEWPORT = {"width": 1400, "height": 1200}

BASE = "https://www.boardgameoracle.com/en-NZ"
USER_AGENT = os.getenv('USER_AGENT', "ManaMeeplesPriceCheck/2.0 (+contact=automation@github.com)")


def rnd(x, nd=2):
    """Round a number to a specified number of decimal places, handling None values."""
    try:
        return None if x is None else round(float(x), nd)
    except Exception:
        return None


# ---------- CSV reading ----------
def read_games_from_csv(csv_file):
    """Read games from buy list CSV export"""
    csv_path = Path(csv_file) if not isinstance(csv_file, Path) else csv_file
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
        print(f"Read {len(df)} rows from CSV")
        print(f"Columns found: {list(df.columns)}")

        # Expected columns: bgg_id, name, bgo_link
        required_cols = ['bgg_id', 'name', 'bgo_link']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Extract and clean the data
        rows = []
        for idx, row in df.iterrows():
            bgg_id = int(row['bgg_id']) if pd.notna(row['bgg_id']) else None
            name = str(row['name']).strip() if pd.notna(row['name']) else ""
            url = str(row['bgo_link']).strip() if pd.notna(row['bgo_link']) else ""

            # Skip rows with missing essential data
            if not name or not url or url in ['#N/A', 'nan', 'None']:
                continue
            if not url.startswith('http'):
                continue

            rows.append({
                "bgg_id": bgg_id,
                "name": name,
                "url": url,
            })

        if not rows:
            print("No valid games found in CSV file - buy list is empty")
            return []

        print(f"Successfully parsed {len(rows)} games from CSV")
        return rows

    except Exception as e:
        print(f"Error reading CSV file: {e}")
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
    """Fetch a BoardGameOracle product page and return HTML content."""
    page = await context.new_page()
    await page.set_extra_http_headers({"User-Agent": USER_AGENT, "Referer": BASE})
    try:
        # Visit base site first
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
        for _ in range(2):
            await page.mouse.wheel(0, 1500)
            await page.wait_for_timeout(200)

        # Wait for price table or store links to appear
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

        if content_found:
            await page.wait_for_timeout(wait_ms)
        else:
            await page.wait_for_timeout(500)

        html = await page.content()
        status = resp.status if resp else None
        return status, html
    finally:
        await page.close()


# ---------- Parse BGO offers ----------
def parse_offers(html: str, game_name: str, page_url: str):
    """Parse price offers from BoardGameOracle HTML."""
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
            # Determine in_stock status
            in_stock = True
            if availability_text:
                t = availability_text.lower()
                if "out of stock" in t or "sold out" in t:
                    in_stock = False

            offers.append({
                "store": store_text,
                "price_nzd": price_value,
                "availability": availability_text,
                "store_link": store_link,
                "in_stock": in_stock,
            })

    return offers


# ---------- Try to read 'Mean' / 'Disc-mean' from DOM ----------
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
                yield j
                return
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


async def fetch_pricestats_via_page(page, product_url: str) -> dict:
    """Fetch price statistics from BoardGameOracle API using tRPC endpoints."""
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
        games = read_games_from_csv(CSV_FILE)
        print(f"Found {len(games)} games in CSV file")

        # If no games, create empty output and exit gracefully
        if not games:
            print("No games to scrape - creating empty output")
            output = {
                "checked_at": datetime.now(tzlocal()).isoformat(timespec="seconds"),
                "games": [],
            }
            with open(OUT_JSON, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"✓ Wrote empty price data to {OUT_JSON}")
            return

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Make sure to export buy list to: {CSV_FILE}")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    checked_at = datetime.now(tzlocal())
    checked_at_iso = checked_at.isoformat(timespec="seconds")

    game_results = []
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

                    # API stats
                    try:
                        if not api_page.url.startswith(BASE):
                            await api_page.goto(BASE, wait_until="domcontentloaded", timeout=30000)
                            await dismiss_banners(api_page)
                        stats = await fetch_pricestats_via_page(api_page, g["url"])
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

                    # Calculate best in-stock price
                    instock_offers = [o for o in offers if o.get("in_stock", True) and o.get("price_nzd")]
                    best_in_stock = None
                    best_store = None
                    if instock_offers:
                        best_offer = min(instock_offers, key=lambda x: x["price_nzd"])
                        best_in_stock = best_offer["price_nzd"]
                        best_store = best_offer["store"]

                    site_mean_val = site_means.get(g["name"])
                    site_low_val = site_lows.get(g["name"])
                    site_disc_mean_pct = site_disc_means.get(g["name"])

                    # Calculate discount percentage
                    disc_pct = None
                    if site_mean_val and best_in_stock:
                        disc_abs = site_mean_val - best_in_stock
                        if site_mean_val != 0:
                            disc_pct = (disc_abs / site_mean_val) * 100.0

                    # Calculate delta
                    delta = None
                    if site_disc_mean_pct is not None and disc_pct is not None:
                        delta = disc_pct - site_disc_mean_pct
                    elif disc_pct is not None and site_mean_val and site_low_val and site_mean_val != 0:
                        # Fallback: calculate delta using computed disc-mean
                        site_disc_mean_calc = ((site_mean_val - site_low_val) / site_mean_val) * 100.0
                        delta = disc_pct - site_disc_mean_calc

                    # Build game result
                    game_result = {
                        "bgg_id": g["bgg_id"],
                        "name": g["name"],
                        "low_price": rnd(site_low_val, 2),
                        "mean_price": rnd(site_mean_val, 2),
                        "best_price": rnd(best_in_stock, 2),
                        "best_store": best_store,
                        "discount_pct": rnd(disc_pct, 2),
                        "delta": rnd(delta, 2),
                        "offers": offers,
                    }
                    game_results.append(game_result)

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

    # Build JSON output
    output = {
        "checked_at": checked_at_iso,
        "games": game_results,
    }

    # Write JSON file
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Wrote price data to {OUT_JSON}")

    total_duration = (datetime.now() - start_time).total_seconds()
    avg_per_game = total_duration / len(games) if games else 0

    print("\n" + "="*60)
    print("Summary:")
    print(f"- Processed {len(games)} games from CSV")
    print(f"- Generated price data for {len(game_results)} games")
    print(f"- Output: {OUT_JSON}")
    print(f"- Total time: {total_duration:.1f}s ({avg_per_game:.1f}s per game)")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run())
