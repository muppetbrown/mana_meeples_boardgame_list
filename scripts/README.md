# Scripts (repo level)

Utility scripts and data files. Backend maintenance scripts live in
[`backend/scripts/`](../backend/scripts/README.md).

## Files

### `fetch_all_sleeves.py`
Scrapes sleeve requirements from BoardGameGeek and writes them to the database. Run by the
**Fetch Sleeves** GitHub Actions workflow (`.github/workflows/fetch_sleeves.yml`), triggered from
Manage Library -> *Fetch Sleeve Data* (or by hand). See [Sleeve fetch setup](../docs/admin/SLEEVE_FETCH_SETUP.md).

### `game_cats.csv`
Reference data for bulk categorisation.

```csv
bgg_id,category
68448,GATEWAY_STRATEGY
173346,GATEWAY_STRATEGY
```

Paste/load it into **Categories -> Bulk Categorize from CSV** (`POST /api/admin/bulk-categorize-csv`).

## Adding scripts

1. Give it a docstring explaining what it does and when to run it.
2. Prefer an admin endpoint or `backend/services/` if it is core application logic.
3. One-off data fixes do not belong here once they have been run: Alembic migrations handle
   schema changes, and git history keeps the old fixes.
