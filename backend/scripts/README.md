# Backend Scripts

Utility scripts for database maintenance and operations.

## Backfill Cloudinary URLs

**Script:** `backfill_cloudinary_urls.py`

### Purpose

Populates the `cloudinary_url` column for existing games that don't have it cached. This eliminates 50-150ms redirect overhead per image request.

### Usage

**Important:** Run from the project root directory (where `backend/` is located)

#### 1. Dry Run (Recommended First)

Test what will be updated without making changes:

```bash
python backend/scripts/backfill_cloudinary_urls.py --dry-run
```

Or using module syntax:
```bash
python -m backend.scripts.backfill_cloudinary_urls --dry-run
```

#### 2. Test with Limited Games

Process only a few games for testing:

```bash
python backend/scripts/backfill_cloudinary_urls.py --dry-run --limit 10
```

#### 3. Run Full Backfill

After testing, run the full backfill:

```bash
python backend/scripts/backfill_cloudinary_urls.py
```

This will prompt for confirmation before making changes.

#### 4. Force Regenerate All URLs

Re-generate URLs even for games that already have them:

```bash
python backend/scripts/backfill_cloudinary_urls.py --force
```

### Options

- `--dry-run` - Show what would be updated without making changes
- `--limit N` - Only process N games (useful for testing)
- `--force` - Re-generate URLs even if they already exist

### Running in Production (Render)

#### Option 1: Via Render Shell

1. Go to https://dashboard.render.com
2. Select your `mana-meeples-boardgame-list` service
3. Click "Shell" tab
4. Navigate to project root and run the script:

```bash
# You should be in /opt/render/project/src by default
# Test first with a small sample
python backend/scripts/backfill_cloudinary_urls.py --dry-run --limit 5

# Review the output, then run full backfill
python backend/scripts/backfill_cloudinary_urls.py
```

#### Option 2: Via SSH (if enabled)

```bash
# Connect to Render shell
render shell mana-meeples-boardgame-list

# Navigate to project root
cd /opt/render/project/src

# Run backfill
python backend/scripts/backfill_cloudinary_urls.py --dry-run
python backend/scripts/backfill_cloudinary_urls.py
```

### Expected Output

```
======================================================================
Cloudinary URL Backfill - DRY RUN
======================================================================
Found 387 games to process
Force regenerate: False
⚠️  Cloudinary is NOT configured!
URLs will be generated but won't work without Cloudinary credentials.
Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
----------------------------------------------------------------------
[10/387] ✓ Updated game 142: 7 Wonders
[20/387] ✓ Updated game 256: Azul
[30/387] ✓ Updated game 89: Catan
...
----------------------------------------------------------------------
DRY RUN - No changes committed
======================================================================
BACKFILL SUMMARY
======================================================================
Total games found:     387
Games processed:       387
Games updated:         387
Games skipped:         0
Games failed:          0
======================================================================
✓ Dry run completed - no changes made

Performance Impact:
  - Image load time improvement: ~50-150ms per game
  - Total time saved per page load: ~38.7s (assuming 10 games/page)
```

### When to Run

Run this script when:

1. **After migration** - When you first add the `cloudinary_url` column
2. **After Cloudinary setup** - When you configure Cloudinary credentials
3. **Force regenerate** - If Cloudinary URLs change (rare)
4. **Periodic maintenance** - To catch any games that were missed

### How It Works

1. Queries all games with `image` or `thumbnail_url` set
2. Skips games that already have `cloudinary_url` (unless `--force`)
3. Generates optimized Cloudinary URL using same settings as imports:
   - Width: 800px
   - Height: 800px
   - Quality: `auto:best`
   - Format: `auto` (WebP/AVIF)
4. Updates database with pre-generated URLs
5. Commits all changes in a single transaction

### Cloudinary Configuration

The script will work with or without Cloudinary configured:

- **With Cloudinary** - Generates real Cloudinary CDN URLs
- **Without Cloudinary** - Generates fallback URLs (returns original BGG URLs)

To check if Cloudinary is configured, look for this in the output:

```
⚠️  Cloudinary is NOT configured!
```

If you see this, set the environment variables:
```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

See `CLOUDINARY_SETUP.md` for full configuration guide.

### Performance Impact

For a catalogue with 387 games:

- **Before backfill:** Each image triggers 302 redirect (50-150ms overhead)
- **After backfill:** Direct Cloudinary URLs (no redirect)
- **Page load improvement:** ~0.5-1.5 seconds per page (10 games/page)

### Troubleshooting

**Script fails with import errors:**
- Make sure you're in the correct directory: `/home/user/mana_meeples_boardgame_list`
- Check that dependencies are installed: `pip install -r backend/requirements.txt`

**"Cloudinary is NOT configured" warning:**
- This is informational - script will still work
- Set Cloudinary environment variables if you want real CDN URLs
- See `CLOUDINARY_SETUP.md` for setup instructions

**Database connection errors:**
- Check `DATABASE_URL` environment variable
- Verify database is accessible

**No games found:**
- Check that games have `image` or `thumbnail_url` set
- Use `--force` to regenerate existing URLs
- Verify games exist: `SELECT COUNT(*) FROM boardgames WHERE image IS NOT NULL;`

### Safety

The script is designed to be safe:

- ✅ Idempotent - Safe to run multiple times
- ✅ Dry run mode - Test before making changes
- ✅ Confirmation prompt - Prevents accidental runs
- ✅ Transaction-based - All changes committed together or rolled back
- ✅ Error handling - Continues on individual game failures
- ✅ Detailed logging - Shows exactly what's happening

### Related Documentation

- `CLOUDINARY_SETUP.md` - How to configure Cloudinary
- `backend/migrations/add_cloudinary_url.py` - Migration that added the column
- `backend/services/cloudinary_service.py` - Cloudinary service implementation
