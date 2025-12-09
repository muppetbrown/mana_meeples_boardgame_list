# Buy List Feature Documentation

## Overview

The buy list feature helps Mana & Meeples track games they want to purchase by:
- Managing a list of target games with BoardGameOracle links
- Automatically scraping NZ prices via GitHub Actions
- Computing buy recommendations based on RRP and online prices
- Tracking Lets Play Games (LPG) stock status manually

## Architecture

### Database Tables

1. **buy_list_games** - Tracks games on the buy list
   - `game_id` - Links to boardgames table
   - `rank` - Priority ordering
   - `bgo_link` - BoardGameOracle product URL
   - `lpg_rrp` - Lets Play Games recommended retail price
   - `lpg_status` - Manual stock status (AVAILABLE, BACK_ORDER, NOT_FOUND, BACK_ORDER_OOS)

2. **price_snapshots** - Aggregated pricing data per game per scrape
   - `low_price`, `mean_price`, `best_price` - Price statistics
   - `best_store` - Retailer with best price
   - `discount_pct`, `delta` - Discount calculations
   - `checked_at` - Timestamp of price check

3. **price_offers** - Individual offers from retailers
   - `store`, `price_nzd`, `availability`, `in_stock`
   - Detailed records for price history

### Buy Filter Logic

The "Buy Filter" column uses Excel-like logic to highlight purchase recommendations:

```python
if lpg_status in ['AVAILABLE', 'BACK_ORDER']:
    if best_price * 2 <= lpg_rrp:
        return True  # Great deal!

if lpg_status in ['NOT_FOUND', 'BACK_ORDER_OOS']:
    if discount_pct > 30:
        return True  # Consider buying online
```

## Workflow

### 1. Add Games to Buy List (Manual)

**Admin UI** → Buy List tab → "Add Game" button
- Search for games in your library
- Add to buy list with optional rank, BGO link, LPG RRP, LPG status

### 2. Price Scraping (Automated - GitHub Actions)

**Schedule:** Daily at 2 AM NZT via GitHub Actions

**Process:**
1. Export buy list from database → `buy_list_export.csv`
2. Run Playwright scraper on BoardGameOracle
3. Generate `latest_prices.json` with pricing data
4. Commit JSON back to repo
5. Render picks up changes automatically

**Manual Trigger:**
```bash
# Trigger GitHub Actions workflow manually
gh workflow run fetch-buy-list-prices.yml
```

**Local Testing:**
```bash
cd backend

# Export buy list
python scripts/export_buy_list.py

# Run price scraper (requires Playwright + Chromium)
pip install playwright beautifulsoup4 lxml pandas python-dateutil
playwright install chromium
python scripts/fetch_buy_list_prices.py
```

### 3. Import Prices (Manual)

**Admin UI** → Buy List tab → "Import Prices" button
- Imports `latest_prices.json` into database
- Updates price_snapshots and price_offers tables
- Refreshes buy list with latest pricing

### 4. Update LPG Status (Manual)

**Admin UI** → Buy List tab → Click "Edit" on any game
- Manually update LPG status by checking their website
- Update LPG RRP if prices change
- Save changes

## API Endpoints

All endpoints require admin authentication (`X-Admin-Token` header or admin session cookie).

### Buy List Management

- `GET /api/admin/buy-list/games` - List buy list with filters
  - Query params: `lpg_status`, `buy_filter`, `sort_by`, `sort_desc`
- `POST /api/admin/buy-list/games` - Add game to buy list
- `PUT /api/admin/buy-list/games/{id}` - Update buy list entry
- `DELETE /api/admin/buy-list/games/{id}` - Remove from buy list

### Price Data

- `POST /api/admin/buy-list/import-prices?source_file={filename}` - Import prices from JSON
- `GET /api/admin/buy-list/last-updated` - Get last price update timestamp

## GitHub Actions Configuration

**Workflow:** `.github/workflows/fetch-buy-list-prices.yml`

**Required Secrets:**
- `DATABASE_URL` - PostgreSQL connection string

**Outputs:**
- `backend/price_data/latest_prices.json` - Latest pricing data
- `backend/price_data/buy_list_export.csv` - Buy list export

**Customization:**
Edit workflow file to change:
- Schedule (default: daily at 2 AM NZT)
- Scraping delays (env vars: `DELAY_MS`, `PAGE_WAIT_MS`)

## LPG Status Management

The LPG (Lets Play Games) status field requires manual updates because:
1. Anti-scraping measures on their website
2. Different product names make matching difficult
3. Requires human judgment for verification

**Status Values:**
- `AVAILABLE` - In stock at LPG
- `BACK_ORDER` - LPG can order but not in stock
- `NOT_FOUND` - Not listed on LPG website
- `BACK_ORDER_OOS` - Back order but currently out of stock

## Troubleshooting

### GitHub Actions fails with 403 on git push
**Fix:** Ensure branch name starts with `claude/` and ends with matching session ID

### Price scraping returns no data
**Fix:**
- Check BGO links are valid
- Increase `PAGE_WAIT_MS` env var (default 1000ms)
- Check GitHub Actions logs for errors

### Import prices fails with "Price data file not found"
**Fix:**
- Ensure GitHub Actions workflow ran successfully
- Check `backend/price_data/latest_prices.json` exists in repo
- Manually trigger workflow if needed

### Database migration fails
**Fix:**
- Check PostgreSQL connection
- Ensure `DATABASE_URL` environment variable is set
- Migration runs automatically on app startup

## Future Enhancements

- [ ] Email notifications for high-priority buy opportunities
- [ ] Price history charts and trends
- [ ] Automated LPG status checking (if API available)
- [ ] Price drop alerts
- [ ] Budget tracking and purchase history
