import requests
import csv
import time
import re

INPUT_FILE  = r"C:\Users\Playtech\OneDrive\scryfall_find.csv"
OUTPUT_FILE = r"C:\Users\Playtech\OneDrive\scryfall_find_with_ids.csv"

HEADERS = {"User-Agent": "scryfall-lookup/1.0", "Accept": "application/json"}
DELAY   = 0.12  # stay well under Scryfall's 10 req/s limit

# ── Helpers ────────────────────────────────────────────────────────────────────

def clean_name(raw):
    """Strip annotations like (foil), (JPN), x3, 'silver scroll', etc."""
    s = re.sub(r'\s*\([^)]*\)', '', raw)                          # remove (...)
    s = re.sub(r'\s+(foil|JP\b|JPN\b|x\d+|silver scroll|surge\s+foil'
               r'|promo|alt\s+art)\s*$', '', s, flags=re.IGNORECASE)
    return s.strip()

def is_collector_number(val):
    """True if value looks like a collector number rather than a set code."""
    return bool(re.match(r'^\d+(/\d+)?[a-zA-Z]?$', str(val).strip()))

def get(url, **params):
    resp = requests.get(url, params=params or None, headers=HEADERS)
    time.sleep(DELAY)
    return resp

# ── Build set-name → set-code map from Scryfall ────────────────────────────────

print("Fetching Scryfall set list...")
sets_data = get("https://api.scryfall.com/sets").json()
set_name_map = {s["name"].lower(): s["code"] for s in sets_data["data"]}

def find_set_code(set_name):
    if not set_name:
        return None
    lower = set_name.strip().lower()
    if lower in set_name_map:                          # exact match
        return set_name_map[lower]
    for name, code in set_name_map.items():            # partial match
        if lower in name or name in lower:
            return code
    return None

# ── Lookup logic ───────────────────────────────────────────────────────────────

def lookup(raw_name, set_name, number):
    name     = clean_name(raw_name)
    set_code = find_set_code(set_name)

    # Strategy 1: set code + collector number (most precise)
    if set_code and is_collector_number(number):
        num  = number.split("/")[0]            # handle "195/264"
        resp = get(f"https://api.scryfall.com/cards/{set_code}/{num}")
        if resp.status_code == 200:
            c = resp.json()
            return c["id"], c["name"], "set+number"

    # Strategy 2: fuzzy name + set code
    if set_code:
        resp = get("https://api.scryfall.com/cards/named", fuzzy=name, set=set_code)
        if resp.status_code == 200:
            c = resp.json()
            return c["id"], c["name"], "fuzzy+set"

    # Strategy 3: fuzzy name only
    resp = get("https://api.scryfall.com/cards/named", fuzzy=name)
    if resp.status_code == 200:
        c = resp.json()
        return c["id"], c["name"], "fuzzy"

    return None, None, "not found"

# ── Main ───────────────────────────────────────────────────────────────────────

with open(INPUT_FILE, newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

# Drop empty trailing rows
rows = [r for r in rows if r.get("Card Name", "").strip()]

results = []
not_found = []

for i, row in enumerate(rows, 1):
    raw_name = row["Card Name"].strip()
    number   = row.get("Number", "").strip()
    set_name = row.get("Set", "").strip()

    sid, resolved, method = lookup(raw_name, set_name, number)

    if sid:
        print(f"[{i:>3}/{len(rows)}] ✓ ({method:12}) {resolved}")
    else:
        print(f"[{i:>3}/{len(rows)}] ✗ NOT FOUND       {raw_name} / {set_name}")
        not_found.append(raw_name)

    results.append({
        **row,
        "scryfall_id":   sid      or "",
        "resolved_name": resolved or "",
        "lookup_method": method,
    })

# ── Save output ────────────────────────────────────────────────────────────────

fieldnames = list(rows[0].keys()) + ["scryfall_id", "resolved_name", "lookup_method"]
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

found = sum(1 for r in results if r["scryfall_id"])
print(f"\n── Done: {found}/{len(results)} found, {len(not_found)} not found ──")
if not_found:
    print("Not found:")
    for n in not_found:
        print(f"  • {n}")
print(f"\nSaved to {OUTPUT_FILE}")
