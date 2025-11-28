# Scripts

Utility scripts and data files for maintenance and operations.

## Files

### `thumbs.py`
Utility module for downloading and managing game thumbnail images.

**Features:**
- Downloads thumbnails from external URLs
- File validation (size, content type, extension)
- Safe filename generation
- Ephemeral storage support (Render compatible)

**Usage:**
```python
from scripts.thumbs import download_thumbnail

# Download a thumbnail
filename = await download_thumbnail(
    url="https://example.com/image.jpg",
    basename="game-123"
)
```

**Configuration:**
- `THUMBS_DIR`: Directory for thumbnail storage (default: `/tmp/thumbs`)
- `MAX_FILE_SIZE`: Maximum file size (5MB)
- Allowed formats: JPEG, PNG, WebP

### `game_cats.csv`
CSV data file for bulk game categorization.

**Format:**
```csv
bgg_id,category
68448,GATEWAY_STRATEGY
173346,GATEWAY_STRATEGY
177736,CORE_STRATEGY
```

**Usage:**
Use with the bulk categorization API endpoint:
```bash
POST /api/admin/bulk-categorize-csv
```

See [Admin Guide](../docs/admin/ADMIN_GUIDE.md) for details.

## Adding New Scripts

When adding utility scripts:
1. Include clear docstrings and comments
2. Add usage examples in this README
3. Follow existing code style and patterns
4. Consider if the script should be in `services/` instead (if it's core application logic)
