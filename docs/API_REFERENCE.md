# API Reference

Complete API reference for the Mana & Meeples Board Game Library API.

**Base URL**: `https://mana-meeples-boardgame-list.onrender.com`
**Interactive Docs**: `/docs` (Swagger UI) or `/redoc` (ReDoc)

---

## Authentication

### Admin Endpoints

Admin endpoints require authentication via one of two methods:

**Method 1: Session Cookie (Recommended)**
```bash
POST /api/admin/login
Content-Type: application/json

{
  "token": "your_admin_token"
}
```

Returns httpOnly session cookie that's automatically included in subsequent requests.

**Method 2: Token Header (Legacy)**
```bash
X-Admin-Token: your_admin_token
```

Include this header in all admin requests.

---

## Public Endpoints

### Get Games List

Get paginated list of games with filtering and search.

```http
GET /api/public/games
```

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `q` | string | Search query (title) | `pandemic` |
| `category` | string | Filter by category | `COOP_ADVENTURE` |
| `designer` | string | Filter by designer name | `Matt Leacock` |
| `nz_designer` | boolean | Filter NZ designers | `true` |
| `page` | integer | Page number (1-indexed) | `1` |
| `page_size` | integer | Items per page (max 1000) | `24` |
| `sort` | string | Sort order | `title_asc` |

**Sort Options:**
- `title_asc` / `title_desc` - Sort by title
- `year_asc` / `year_desc` - Sort by year
- `rating_asc` / `rating_desc` - Sort by BGG rating
- `time_asc` / `time_desc` - Sort by play time

**Example Request:**
```bash
curl "https://mana-meeples-boardgame-list.onrender.com/api/public/games?category=COOP_ADVENTURE&page=1&page_size=12&sort=title_asc"
```

**Response:**
```json
{
  "total": 42,
  "page": 1,
  "page_size": 12,
  "items": [
    {
      "id": 1,
      "title": "Pandemic",
      "year": 2008,
      "players_min": 2,
      "players_max": 4,
      "playtime_min": 45,
      "playtime_max": 60,
      "complexity": 2.43,
      "average_rating": 7.6,
      "mana_meeple_category": "COOP_ADVENTURE",
      "designers": ["Matt Leacock"],
      "mechanics": ["Cooperative Game", "Hand Management"],
      "thumbnail_url": "https://...",
      "image": "https://...",
      "bgg_id": 30549,
      "nz_designer": false
    }
  ]
}
```

---

### Get Single Game

Get detailed information for a specific game.

```http
GET /api/public/games/{id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Game ID |

**Example Request:**
```bash
curl "https://mana-meeples-boardgame-list.onrender.com/api/public/games/1"
```

**Response:**
```json
{
  "id": 1,
  "title": "Pandemic",
  "year": 2008,
  "description": "<p>In Pandemic, several virulent diseases...</p>",
  "players_min": 2,
  "players_max": 4,
  "playtime_min": 45,
  "playtime_max": 60,
  "min_age": 8,
  "complexity": 2.43,
  "average_rating": 7.6,
  "bgg_rank": 100,
  "users_rated": 50000,
  "mana_meeple_category": "COOP_ADVENTURE",
  "designers": ["Matt Leacock"],
  "publishers": ["Z-Man Games"],
  "mechanics": ["Cooperative Game", "Hand Management", "Action Points"],
  "artists": ["Joshua Cappel"],
  "is_cooperative": true,
  "thumbnail_url": "https://...",
  "image": "https://...",
  "bgg_id": 30549,
  "nz_designer": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### Get Category Counts

Get count of games in each category.

```http
GET /api/public/category-counts
```

**Example Request:**
```bash
curl "https://mana-meeples-boardgame-list.onrender.com/api/public/category-counts"
```

**Response:**
```json
{
  "COOP_ADVENTURE": 42,
  "GATEWAY_STRATEGY": 58,
  "CORE_STRATEGY": 35,
  "KIDS_FAMILIES": 67,
  "PARTY_ICEBREAKERS": 28,
  "uncategorized": 5
}
```

---

### Get Games by Designer

Get all games by a specific designer.

```http
GET /api/public/games/by-designer/{designer_name}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `designer_name` | string | Designer name (URL encoded) |

**Example Request:**
```bash
curl "https://mana-meeples-boardgame-list.onrender.com/api/public/games/by-designer/Matt%20Leacock"
```

**Response:**
```json
{
  "designer": "Matt Leacock",
  "games": [
    {
      "id": 1,
      "title": "Pandemic",
      "year": 2008,
      ...
    }
  ]
}
```

---

### Image Proxy

Proxy external images with caching.

```http
GET /api/public/image-proxy
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | string | External image URL (URL encoded) |

**Example Request:**
```bash
curl "https://mana-meeples-boardgame-list.onrender.com/api/public/image-proxy?url=https%3A%2F%2Fexample.com%2Fimage.jpg"
```

**Response:** Image binary data with cache headers

---

## Admin Endpoints

All admin endpoints require authentication via session cookie or `X-Admin-Token` header.

### Login

Create admin session.

```http
POST /api/admin/login
```

**Request Body:**
```json
{
  "token": "your_admin_token"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful"
}
```

Sets httpOnly session cookie.

---

### Validate Token

Check if current session is valid.

```http
GET /api/admin/validate
```

**Headers:**
```
X-Admin-Token: your_admin_token
```

**Response:**
```json
{
  "valid": true
}
```

---

### Get All Games (Admin)

Get all games with admin-specific fields.

```http
GET /api/admin/games
```

**Query Parameters:** Same as public games endpoint

---

### Create Game

Create a new game manually.

```http
POST /api/admin/games
```

**Request Body:**
```json
{
  "title": "New Game",
  "year": 2024,
  "players_min": 2,
  "players_max": 4,
  "playtime_min": 30,
  "playtime_max": 60,
  "mana_meeple_category": "GATEWAY_STRATEGY",
  "description": "Game description",
  "designers": ["Designer Name"],
  "bgg_id": 12345
}
```

**Response:** Created game object

---

### Update Game

Update an existing game.

```http
PUT /api/admin/games/{id}
```

**Request Body:** Partial game object with fields to update

**Response:** Updated game object

---

### Delete Game

Delete a game.

```http
DELETE /api/admin/games/{id}
```

**Response:**
```json
{
  "success": true,
  "message": "Game deleted"
}
```

---

### Import from BoardGameGeek

Import game data from BGG.

```http
POST /api/admin/import/bgg
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `bgg_id` | integer | BoardGameGeek game ID |
| `force` | boolean | Force re-import if exists |

**Example Request:**
```bash
curl -X POST \
  -H "X-Admin-Token: your_token" \
  "https://mana-meeples-boardgame-list.onrender.com/api/admin/import/bgg?bgg_id=30549&force=false"
```

**Response:** Imported game object

---

### Bulk Import from CSV

Import multiple games from CSV.

```http
POST /api/admin/bulk-import-csv
```

**Request Body:**
```json
{
  "csv_text": "bgg_id,title\n30549,Pandemic\n68448,7 Wonders"
}
```

**Response:**
```json
{
  "success": true,
  "imported": 2,
  "failed": 0,
  "results": [...]
}
```

---

### Bulk Categorize from CSV

Update categories for multiple games.

```http
POST /api/admin/bulk-categorize-csv
```

**Request Body:**
```json
{
  "csv_text": "game_id,category\n1,COOP_ADVENTURE\n2,GATEWAY_STRATEGY"
}
```

**Response:**
```json
{
  "success": true,
  "updated": 2,
  "failed": 0
}
```

---

### Bulk Update NZ Designers

Mark games with NZ designers.

```http
POST /api/admin/bulk-update-nz-designers
```

**Request Body:**
```json
{
  "csv_text": "designer_name\nDesigner 1\nDesigner 2"
}
```

**Response:**
```json
{
  "success": true,
  "updated_games": 5
}
```

---

### Re-import All Games

Re-fetch data from BGG for all games.

```http
POST /api/admin/reimport-all-games
```

**Response:**
```json
{
  "success": true,
  "message": "Re-import started for 100 games"
}
```

---

## Health & Debug Endpoints

### Health Check

Basic health check.

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Database Health Check

Check database connectivity.

```http
GET /api/health/db
```

**Response:**
```json
{
  "status": "healthy",
  "game_count": 235,
  "database": "connected"
}
```

---

### Debug Endpoints

Various debug endpoints (some admin-only):

- `GET /api/debug/categories` - List all BGG categories
- `GET /api/debug/database-info` - Database schema info
- `GET /api/debug/export-games-csv` - Export games as CSV
- `GET /api/debug/performance` - Performance statistics (admin only)

---

## Rate Limiting

**Public Endpoints:**
- 100 requests per minute per IP address

**Admin Endpoints:**
- 5 failed login attempts per minute per IP
- No limit on authenticated requests

**Headers:**
- `X-RateLimit-Limit` - Request limit
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Reset timestamp

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "details": {}
}
```

**Common HTTP Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (missing/invalid admin token) |
| 404 | Not Found (game doesn't exist) |
| 429 | Too Many Requests (rate limit exceeded) |
| 500 | Internal Server Error |
| 503 | Service Unavailable (BGG API error) |

---

## Categories

Valid category values for filtering:

- `COOP_ADVENTURE` - Co-op & Adventure
- `GATEWAY_STRATEGY` - Gateway Strategy
- `CORE_STRATEGY` - Core Strategy & Epics
- `KIDS_FAMILIES` - Kids & Families
- `PARTY_ICEBREAKERS` - Party & Icebreakers

---

## Examples

### JavaScript/Axios

```javascript
import axios from 'axios';

const API_BASE = 'https://mana-meeples-boardgame-list.onrender.com';

// Get games
const games = await axios.get(`${API_BASE}/api/public/games`, {
  params: { category: 'COOP_ADVENTURE', page_size: 12 }
});

// Get single game
const game = await axios.get(`${API_BASE}/api/public/games/1`);

// Admin: Import from BGG
await axios.post(`${API_BASE}/api/admin/import/bgg?bgg_id=30549`, null, {
  headers: { 'X-Admin-Token': 'your_token' }
});
```

### Python

```python
import requests

API_BASE = 'https://mana-meeples-boardgame-list.onrender.com'

# Get games
response = requests.get(f'{API_BASE}/api/public/games', params={
    'category': 'COOP_ADVENTURE',
    'page_size': 12
})
games = response.json()

# Get single game
game = requests.get(f'{API_BASE}/api/public/games/1').json()

# Admin: Import from BGG
requests.post(
    f'{API_BASE}/api/admin/import/bgg',
    params={'bgg_id': 30549},
    headers={'X-Admin-Token': 'your_token'}
)
```

---

**Last Updated**: Phase 5 (Documentation & Polish)
**API Version**: 2.0.0
**Documentation**: `/docs` (Swagger UI) or `/redoc` (ReDoc)
