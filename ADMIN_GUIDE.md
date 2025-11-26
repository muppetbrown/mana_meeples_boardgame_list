# Admin Access Guide - Mana & Meeples Board Game Library

## How to Access the Admin Dashboard

### 1. Navigate to the Admin Login Page

Go to: `https://library.manaandmeeples.co.nz/staff/login`

Or click the "Staff Login" link if available on the public site.

### 2. Enter Your Admin Token

The admin token is securely stored in the `ADMIN_TOKEN` environment variable on the Render backend service.

**To find your admin token:**
1. Log into your Render dashboard at https://render.com
2. Navigate to the **mana-meeples-boardgame-list** backend service
3. Go to the "Environment" tab
4. Locate the `ADMIN_TOKEN` value

**Security Note:** The admin token should be at least 32 characters long and contain a mix of letters, numbers, and symbols. Never share this token publicly or commit it to version control.

### 3. Login Security Features

The admin login system includes:
- **Token Validation**: The token is verified against the backend before granting access
- **Rate Limiting**: Maximum 5 failed login attempts per 5 minutes per IP address
- **Auto-Logout**: Invalid or expired tokens automatically redirect you back to login
- **Session Persistence**: Your token is stored locally and validated on each page load

---

## Admin Dashboard Features

Once logged in, you'll see the Staff Dashboard with the following sections:

### 📊 Dashboard Header
- **Game Statistics**: Total games, available games, and average rating
- **Logout Button**: Safely logout and clear your session

### 🎲 Add Game by BGG ID
Add individual games from BoardGameGeek:
1. Enter a BGG ID (e.g., `30549` for Pandemic)
2. Click "Add Game"
3. Game data is automatically imported including:
   - Title, year, player counts, playtime
   - Categories, designers, mechanics
   - BGG ratings and complexity
   - Thumbnail images

**To find BGG IDs:**
- Visit boardgamegeek.com
- Search for the game
- The ID is in the URL: `/boardgame/30549/pandemic` → ID is `30549`

### 📚 Your Library
View and manage all games in your collection:

**Filter by Category:**
- All games
- Co-op & Adventure
- Core Strategy & Epics
- Gateway Strategy
- Kids & Families
- Party & Icebreakers
- Uncategorized

**Per-Game Actions:**
- **Edit Category**: Assign or change the Mana & Meeples category
- **Delete**: Remove game from the library (with confirmation)

### 📥 Bulk Import (CSV)
Import multiple games at once:

**CSV Format:**
```csv
bgg_id,title
30549,Pandemic
174430,Gloomhaven
167791,Terraforming Mars
```

**Process:**
1. Paste CSV data into the text area
2. Click "Import"
3. System will:
   - Add new games from BGG
   - Skip games that already exist
   - Download a log file with results

**Notes:**
- Only `bgg_id` is required; `title` is optional for your reference
- One game import per line
- Games are imported one at a time for maximum data quality

### 🏷️ Bulk Categorize Existing (CSV)
Update categories for multiple existing games:

**CSV Format:**
```csv
bgg_id,category,title
30549,COOP_ADVENTURE,Pandemic
174430,CORE_STRATEGY,Gloomhaven
```

**Category Options:**
- Use category keys: `COOP_ADVENTURE`, `CORE_STRATEGY`, `GATEWAY_STRATEGY`, `KIDS_FAMILIES`, `PARTY_ICEBREAKERS`
- Or use full labels: `Co-op & Adventure`, `Core Strategy & Epics`, etc.

**Process:**
1. Paste CSV data into the text area
2. Click "Categorize"
3. System will update matching games and download a results log

---

## Advanced Admin Tools

### 🇳🇿 Bulk Update NZ Designers
Flag games designed by New Zealand designers:

**CSV Format:**
```csv
bgg_id,nz_designer
12345,true
67890,false
```

**Accepted Values for `nz_designer`:**
- `true`, `1`, `yes` → Mark as NZ designer
- `false`, `0`, `no` → Remove NZ designer flag

### 🔄 Advanced Operations

**Re-import All Games:**
- Fetches latest BGG data for ALL games in your library
- Updates ratings, complexity, mechanics, and other metadata
- **Warning**: This process can take several minutes
- Use when you need to refresh all game data

**Export Games CSV:**
- Downloads a complete CSV backup of all game data
- Includes all fields: title, categories, ratings, designers, etc.
- Useful for data analysis or migration

### 🔍 Debug & Monitoring

**System Health:**
- API connectivity status
- Database connection health
- Game count verification

**Performance Stats:**
- Average response time
- Slowest endpoints
- Request counts and error rates

**Database Info:**
- Schema structure
- Sample game records
- Data integrity checks

**BGG Categories:**
- View all unique BGG categories in your database
- Useful for understanding category mapping

---

## Admin API Endpoints

All admin endpoints require the `X-Admin-Token` header for authentication.

### Authentication
- **GET** `/api/admin/validate` - Validate admin token

### Game Management
- **GET** `/api/admin/games` - List all games (admin view)
- **GET** `/api/admin/games/{id}` - Get single game
- **POST** `/api/admin/games` - Create new game manually
- **PUT** `/api/admin/games/{id}` - Update game (full update)
- **POST** `/api/admin/games/{id}/update` - Update game (partial update, proxy-compatible)
- **DELETE** `/api/admin/games/{id}` - Delete game

### BGG Integration
- **POST** `/api/admin/import/bgg?bgg_id={id}&force={bool}` - Import from BoardGameGeek

### Bulk Operations
- **POST** `/api/admin/bulk-import-csv` - Bulk import games from CSV
- **POST** `/api/admin/bulk-categorize-csv` - Bulk categorize existing games
- **POST** `/api/admin/bulk-update-nz-designers` - Bulk update NZ designer flags
- **POST** `/api/admin/reimport-all-games` - Re-import all games with enhanced data

### Debug & Monitoring
- **GET** `/api/debug/categories` - View all BGG categories (admin only)
- **GET** `/api/debug/database-info?limit={n}` - Database structure and samples
- **GET** `/api/debug/performance` - Performance monitoring stats (admin only)
- **GET** `/api/debug/export-games-csv?limit={n}` - Export games as CSV

---

## Troubleshooting

### "Invalid admin token"
- Verify you copied the complete token from Render dashboard
- Check for extra spaces or line breaks
- Ensure the `ADMIN_TOKEN` environment variable is set in Render

### "Too many attempts. Please try again later."
- Wait 5 minutes before trying again
- Rate limiting protects against brute force attacks
- Resets automatically after the time window

### Session expires unexpectedly
- Token is validated on each page load
- If the token changes in Render, existing sessions will be invalidated
- Clear browser cache and log in again with the new token

### Cannot connect to API
- Check that the backend service is running on Render
- Verify CORS settings allow your frontend domain
- Check browser console for detailed error messages

### Game import fails
- Verify the BGG ID is correct (visit boardgamegeek.com)
- Check if game already exists (use force=true to reimport)
- Review backend logs in Render dashboard for BGG API issues

---

## Security Best Practices

1. **Never share the admin token** publicly or in screenshots
2. **Use a strong token** (32+ characters with mixed character types)
3. **Rotate the token periodically** by updating the Render environment variable
4. **Logout when finished** to clear the local session
5. **Monitor access logs** in Render dashboard for unauthorized attempts
6. **Use HTTPS only** - never access admin over insecure connections

---

## Getting Help

If you encounter issues:

1. Check the browser console for error messages
2. Review Render service logs for backend errors
3. Verify environment variables are configured correctly
4. Test the `/api/health` endpoint to verify API connectivity
5. Contact the development team with specific error messages

---

**Last Updated:** 2025-11-26
**Admin System Version:** 2.0.0
