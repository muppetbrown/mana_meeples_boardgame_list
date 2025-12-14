# Test Coverage Improvement Plan
**Project:** Mana & Meeples Board Game Library
**Current Coverage:** <10%
**Target Coverage:** 70%+
**Timeline:** 12 weeks (3 phases)

---

## Executive Summary

This plan outlines a systematic approach to increase test coverage from <10% to 70%+ over 12 weeks. The strategy prioritizes critical business logic, follows the testing pyramid, and establishes sustainable testing practices.

**Current State:**
- Backend: ~7 test files, minimal coverage
- Frontend: ~3 test files, minimal coverage
- No integration tests
- No E2E tests
- Basic pytest/vitest infrastructure exists

**Target State:**
- 70%+ code coverage across backend and frontend
- Comprehensive unit tests for all services
- Integration tests for critical API flows
- E2E tests for key user journeys
- Automated coverage reporting in CI/CD

---

## Testing Strategy

### Testing Pyramid

```
        /\
       /E2E\          5% - End-to-End (10-15 tests)
      /------\
     /        \
    /Integration\    15% - Integration (50-75 tests)
   /------------\
  /              \
 /   Unit Tests   \  80% - Unit Tests (200-300 tests)
/------------------\
```

**Rationale:**
- **Unit Tests (80%):** Fast, focused, catch bugs early
- **Integration Tests (15%):** Test component interactions
- **E2E Tests (5%):** Validate critical user flows

---

## Phase 1: Foundation (Weeks 1-4)

**Goal:** Establish testing infrastructure and reach 30% coverage

### Week 1: Infrastructure Setup

**Backend:**
```bash
# Install testing tools
pip install pytest-cov pytest-asyncio pytest-mock faker factory-boy freezegun

# Update pytest.ini
[pytest]
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts =
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=30
    -v
```

**Frontend:**
```bash
# Install testing tools
npm install --save-dev @testing-library/react @testing-library/jest-dom \
  @testing-library/user-event vitest @vitest/ui jsdom msw

# Update vitest.config.js
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: ['node_modules/', 'src/test/'],
      thresholds: {
        lines: 30,
        functions: 30,
        branches: 30,
        statements: 30
      }
    }
  }
})
```

**CI/CD Integration:**
```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    cd backend
    pytest --cov --cov-report=xml

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./backend/coverage.xml
    flags: backend
```

### Week 2: Backend Service Layer Tests (Priority 1)

**Target:** GameService (game_service.py - 638 lines)

**Test File:** `backend/tests/test_services/test_game_service_comprehensive.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Game
from services import GameService
from exceptions import GameNotFoundError, ValidationError

@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def game_service(test_db):
    """Create GameService instance with test database"""
    return GameService(test_db)

@pytest.fixture
def sample_game(test_db):
    """Create sample game for testing"""
    game = Game(
        title="Test Game",
        bgg_id=12345,
        year=2023,
        players_min=2,
        players_max=4,
        mana_meeple_category="GATEWAY_STRATEGY",
        status="OWNED"
    )
    test_db.add(game)
    test_db.commit()
    test_db.refresh(game)
    return game

class TestGameServiceCRUD:
    """Test basic CRUD operations"""

    def test_get_game_by_id_success(self, game_service, sample_game):
        """Should return game when ID exists"""
        result = game_service.get_game_by_id(sample_game.id)
        assert result is not None
        assert result.id == sample_game.id
        assert result.title == "Test Game"

    def test_get_game_by_id_not_found(self, game_service):
        """Should return None when ID doesn't exist"""
        result = game_service.get_game_by_id(99999)
        assert result is None

    def test_get_game_by_bgg_id_success(self, game_service, sample_game):
        """Should return game when BGG ID exists"""
        result = game_service.get_game_by_bgg_id(12345)
        assert result is not None
        assert result.bgg_id == 12345

    def test_create_game_success(self, game_service):
        """Should create new game with valid data"""
        game_data = {
            "title": "New Game",
            "bgg_id": 54321,
            "year": 2024,
            "players_min": 1,
            "players_max": 6
        }
        game = game_service.create_game(game_data)

        assert game.id is not None
        assert game.title == "New Game"
        assert game.bgg_id == 54321

    def test_create_game_duplicate_bgg_id(self, game_service, sample_game):
        """Should raise ValidationError for duplicate BGG ID"""
        game_data = {"title": "Duplicate", "bgg_id": 12345}

        with pytest.raises(ValidationError, match="already exists"):
            game_service.create_game(game_data)

    def test_update_game_success(self, game_service, sample_game):
        """Should update game with valid data"""
        update_data = {"title": "Updated Title", "year": 2025}
        updated = game_service.update_game(sample_game.id, update_data)

        assert updated.title == "Updated Title"
        assert updated.year == 2025
        assert updated.bgg_id == sample_game.bgg_id  # Unchanged

    def test_update_game_not_found(self, game_service):
        """Should raise GameNotFoundError for non-existent game"""
        with pytest.raises(GameNotFoundError):
            game_service.update_game(99999, {"title": "Nope"})

    def test_delete_game_success(self, game_service, sample_game):
        """Should delete game and return title"""
        title = game_service.delete_game(sample_game.id)
        assert title == "Test Game"

        # Verify deletion
        result = game_service.get_game_by_id(sample_game.id)
        assert result is None

class TestGameServiceFiltering:
    """Test filtering and search logic"""

    @pytest.fixture
    def multiple_games(self, test_db):
        """Create multiple games for filtering tests"""
        games = [
            Game(title="Catan", bgg_id=1, year=1995, players_min=3,
                 players_max=4, mana_meeple_category="GATEWAY_STRATEGY",
                 status="OWNED", designers='["Klaus Teuber"]'),
            Game(title="Pandemic", bgg_id=2, year=2008, players_min=2,
                 players_max=4, mana_meeple_category="COOP_ADVENTURE",
                 status="OWNED", designers='["Matt Leacock"]'),
            Game(title="Wingspan", bgg_id=3, year=2019, players_min=1,
                 players_max=5, mana_meeple_category="GATEWAY_STRATEGY",
                 status="OWNED", nz_designer=False),
            Game(title="Unfathomable", bgg_id=4, year=2021, players_min=3,
                 players_max=6, mana_meeple_category="COOP_ADVENTURE",
                 status="OWNED", nz_designer=False),
        ]
        for game in games:
            test_db.add(game)
        test_db.commit()
        return games

    def test_filter_by_category(self, game_service, multiple_games):
        """Should filter games by category"""
        games, total = game_service.get_filtered_games(
            category="GATEWAY_STRATEGY",
            page=1,
            page_size=10
        )
        assert total == 2
        assert all(g.mana_meeple_category == "GATEWAY_STRATEGY" for g in games)

    def test_filter_by_search_title(self, game_service, multiple_games):
        """Should search games by title"""
        games, total = game_service.get_filtered_games(
            search="pan",  # Should match "Pandemic" and "Wingspan"
            page=1,
            page_size=10
        )
        assert total == 2
        titles = [g.title for g in games]
        assert "Pandemic" in titles
        assert "Wingspan" in titles

    def test_filter_by_search_designer(self, game_service, multiple_games):
        """Should search games by designer name"""
        games, total = game_service.get_filtered_games(
            search="leacock",  # Matt Leacock
            page=1,
            page_size=10
        )
        assert total == 1
        assert games[0].title == "Pandemic"

    def test_filter_by_designer_filter(self, game_service, multiple_games):
        """Should filter games by designer"""
        games, total = game_service.get_filtered_games(
            designer="Klaus Teuber",
            page=1,
            page_size=10
        )
        assert total == 1
        assert games[0].title == "Catan"

    def test_filter_by_nz_designer(self, game_service, multiple_games):
        """Should filter games by NZ designer flag"""
        games, total = game_service.get_filtered_games(
            nz_designer=False,
            page=1,
            page_size=10
        )
        # All games have nz_designer=False in test data
        assert total == 2  # Only games with explicit False

    def test_filter_by_players(self, game_service, multiple_games):
        """Should filter games by player count"""
        # Looking for games that support 5 players
        games, total = game_service.get_filtered_games(
            players=5,
            page=1,
            page_size=10
        )
        # Wingspan (1-5) and Unfathomable (3-6)
        assert total == 2

    def test_filter_combined(self, game_service, multiple_games):
        """Should apply multiple filters together"""
        games, total = game_service.get_filtered_games(
            category="COOP_ADVENTURE",
            players=4,
            page=1,
            page_size=10
        )
        # Pandemic and Unfathomable both support 4 players
        assert total == 2

    def test_pagination(self, game_service, multiple_games):
        """Should paginate results correctly"""
        # Get first page (2 items)
        games, total = game_service.get_filtered_games(
            page=1,
            page_size=2
        )
        assert len(games) == 2
        assert total == 4

        # Get second page
        games, total = game_service.get_filtered_games(
            page=2,
            page_size=2
        )
        assert len(games) == 2
        assert total == 4

    def test_sorting_title_asc(self, game_service, multiple_games):
        """Should sort by title ascending"""
        games, _ = game_service.get_filtered_games(
            sort="title_asc",
            page=1,
            page_size=10
        )
        titles = [g.title for g in games]
        assert titles == sorted(titles)

    def test_sorting_year_desc(self, game_service, multiple_games):
        """Should sort by year descending"""
        games, _ = game_service.get_filtered_games(
            sort="year_desc",
            page=1,
            page_size=10
        )
        years = [g.year for g in games]
        assert years == sorted(years, reverse=True)

class TestGameServiceBGGImport:
    """Test BGG import functionality"""

    def test_create_from_bgg_new_game(self, game_service):
        """Should create new game from BGG data"""
        bgg_data = {
            "title": "Gloomhaven",
            "bgg_id": 174430,
            "year": 2017,
            "categories": ["Adventure", "Fantasy", "Fighting"],
            "players_min": 1,
            "players_max": 4,
            "designers": ["Isaac Childres"],
            "complexity": 3.86
        }

        game, was_cached = game_service.create_or_update_from_bgg(
            bgg_id=174430,
            bgg_data=bgg_data,
            force_update=False
        )

        assert game.title == "Gloomhaven"
        assert game.bgg_id == 174430
        assert game.complexity == 3.86
        assert was_cached is False

    def test_create_from_bgg_existing_no_force(self, game_service, sample_game):
        """Should return cached game without updating"""
        bgg_data = {"title": "Updated Title", "bgg_id": 12345}

        game, was_cached = game_service.create_or_update_from_bgg(
            bgg_id=12345,
            bgg_data=bgg_data,
            force_update=False
        )

        assert game.title == "Test Game"  # Not updated
        assert was_cached is True

    def test_create_from_bgg_force_update(self, game_service, sample_game):
        """Should update existing game with force=True"""
        bgg_data = {"title": "Force Updated", "bgg_id": 12345, "year": 2025}

        game, was_cached = game_service.create_or_update_from_bgg(
            bgg_id=12345,
            bgg_data=bgg_data,
            force_update=True
        )

        assert game.title == "Force Updated"
        assert game.year == 2025
        assert was_cached is True

class TestGameServiceCategoryCounts:
    """Test category counting"""

    def test_category_counts(self, game_service, test_db):
        """Should return accurate category counts"""
        # Create games in different categories
        games = [
            Game(title="G1", bgg_id=1, status="OWNED",
                 mana_meeple_category="GATEWAY_STRATEGY"),
            Game(title="G2", bgg_id=2, status="OWNED",
                 mana_meeple_category="GATEWAY_STRATEGY"),
            Game(title="G3", bgg_id=3, status="OWNED",
                 mana_meeple_category="COOP_ADVENTURE"),
            Game(title="G4", bgg_id=4, status="OWNED",
                 mana_meeple_category=None),  # Uncategorized
        ]
        for game in games:
            test_db.add(game)
        test_db.commit()

        counts = game_service.get_category_counts()

        assert counts["GATEWAY_STRATEGY"] == 2
        assert counts["COOP_ADVENTURE"] == 1
        assert counts["uncategorized"] == 1

# Run with: pytest backend/tests/test_services/test_game_service_comprehensive.py -v --cov
```

**Tests to Add:** ~50 tests covering:
- ✅ CRUD operations (10 tests)
- ✅ Filtering logic (12 tests)
- ✅ BGG import (5 tests)
- ✅ Category counts (3 tests)
- ⏭️ Edge cases (nulls, empty results, malformed data) (10 tests)
- ⏭️ Expansion linking (5 tests)
- ⏭️ Sleeve data handling (5 tests)

### Week 3: Backend API Integration Tests

**Test File:** `backend/tests/test_api/test_public_comprehensive.py`

```python
import pytest
from fastapi.testclient import TestClient
from main import app
from models import Base, Game
from database import engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def test_client(test_db):
    """Create test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    from database import get_db
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()

@pytest.fixture
def sample_games(test_db):
    """Create sample games for API tests"""
    games = [
        Game(title="Catan", bgg_id=13, year=1995, status="OWNED",
             mana_meeple_category="GATEWAY_STRATEGY"),
        Game(title="Pandemic", bgg_id=30549, year=2008, status="OWNED",
             mana_meeple_category="COOP_ADVENTURE"),
    ]
    for game in games:
        test_db.add(game)
    test_db.commit()
    return games

class TestPublicGamesEndpoint:
    """Test GET /api/public/games endpoint"""

    def test_get_games_success(self, test_client, sample_games):
        """Should return paginated games"""
        response = test_client.get("/api/public/games")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_get_games_with_search(self, test_client, sample_games):
        """Should filter by search query"""
        response = test_client.get("/api/public/games?q=pan")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Pandemic"

    def test_get_games_with_category(self, test_client, sample_games):
        """Should filter by category"""
        response = test_client.get(
            "/api/public/games?category=GATEWAY_STRATEGY"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Catan"

    def test_get_games_pagination(self, test_client, sample_games):
        """Should paginate results"""
        response = test_client.get("/api/public/games?page=1&page_size=1")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 1

    def test_get_games_rate_limiting(self, test_client):
        """Should enforce rate limits"""
        # Make 101 requests (limit is 100/minute)
        for i in range(101):
            response = test_client.get("/api/public/games")
            if i < 100:
                assert response.status_code == 200

        # 101st request should be rate limited
        assert response.status_code == 429

class TestPublicGameDetailEndpoint:
    """Test GET /api/public/games/{id} endpoint"""

    def test_get_game_success(self, test_client, sample_games):
        """Should return game details"""
        game_id = sample_games[0].id
        response = test_client.get(f"/api/public/games/{game_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game_id
        assert data["title"] == "Catan"

    def test_get_game_not_found(self, test_client):
        """Should return 404 for non-existent game"""
        response = test_client.get("/api/public/games/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

class TestCategoryCountsEndpoint:
    """Test GET /api/public/category-counts endpoint"""

    def test_get_category_counts(self, test_client, sample_games):
        """Should return category counts"""
        response = test_client.get("/api/public/category-counts")

        assert response.status_code == 200
        data = response.json()
        assert "GATEWAY_STRATEGY" in data
        assert data["GATEWAY_STRATEGY"] == 1
        assert "COOP_ADVENTURE" in data
        assert data["COOP_ADVENTURE"] == 1

# Run with: pytest backend/tests/test_api/test_public_comprehensive.py -v --cov
```

**Tests to Add:** ~40 integration tests

### Week 4: Frontend Component Tests

**Test File:** `frontend/src/components/public/__tests__/GameCardPublic.test.jsx`

```jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import GameCardPublic from '../GameCardPublic'

const mockGame = {
  id: 1,
  title: 'Test Game',
  year: 2023,
  players_min: 2,
  players_max: 4,
  playtime_min: 30,
  playtime_max: 60,
  complexity: 2.5,
  average_rating: 7.8,
  thumbnail_url: 'https://example.com/image.jpg',
  mana_meeple_category: 'GATEWAY_STRATEGY',
  designers: ['Test Designer'],
}

const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('GameCardPublic', () => {
  it('renders game title', () => {
    renderWithRouter(<GameCardPublic game={mockGame} />)
    expect(screen.getByText('Test Game')).toBeInTheDocument()
  })

  it('renders game year', () => {
    renderWithRouter(<GameCardPublic game={mockGame} />)
    expect(screen.getByText('2023')).toBeInTheDocument()
  })

  it('renders player count', () => {
    renderWithRouter(<GameCardPublic game={mockGame} />)
    expect(screen.getByText(/2-4 players/i)).toBeInTheDocument()
  })

  it('renders playtime', () => {
    renderWithRouter(<GameCardPublic game={mockGame} />)
    expect(screen.getByText(/30-60 min/i)).toBeInTheDocument()
  })

  it('renders complexity rating', () => {
    renderWithRouter(<GameCardPublic game={mockGame} />)
    expect(screen.getByText(/2\.5/)).toBeInTheDocument()
  })

  it('renders designer names', () => {
    renderWithRouter(<GameCardPublic game={mockGame} />)
    expect(screen.getByText(/Test Designer/)).toBeInTheDocument()
  })

  it('renders image with correct src', () => {
    renderWithRouter(<GameCardPublic game={mockGame} />)
    const img = screen.getByRole('img', { name: /Test Game/i })
    expect(img).toHaveAttribute('src')
  })

  it('navigates to game details on click', () => {
    renderWithRouter(<GameCardPublic game={mockGame} />)
    const card = screen.getByRole('article')
    fireEvent.click(card)
    // Could use router spy to verify navigation
  })

  it('handles missing complexity gracefully', () => {
    const gameWithoutComplexity = { ...mockGame, complexity: null }
    renderWithRouter(<GameCardPublic game={gameWithoutComplexity} />)
    // Should not crash, may show N/A or hide complexity
  })

  it('handles missing image gracefully', () => {
    const gameWithoutImage = { ...mockGame, thumbnail_url: null }
    renderWithRouter(<GameCardPublic game={gameWithoutImage} />)
    // Should show placeholder or no image
  })
})

// Run with: npm test GameCardPublic
```

**Tests to Add:** ~30 component tests

---

## Phase 2: Expansion (Weeks 5-8)

**Goal:** Reach 55% coverage with integration and E2E tests

### Week 5: Backend Admin & BGG Service Tests

**Priority Tests:**
1. **Admin Authentication Tests** (`test_api/test_admin_auth.py`)
   - Session creation and validation
   - Rate limiting on login attempts
   - Token-based auth fallback
   - Session expiration handling
   - Logout functionality

2. **BGG Service Tests** (`test_services/test_bgg_service.py`)
   - XML parsing logic
   - Retry mechanism with exponential backoff
   - Error handling for invalid IDs
   - Timeout handling
   - Response validation

```python
# test_bgg_service.py
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from bgg_service import fetch_bgg_thing, BGGServiceError

@pytest.mark.asyncio
class TestBGGService:

    async def test_fetch_valid_game(self):
        """Should parse valid BGG XML response"""
        mock_xml = '''<?xml version="1.0"?>
        <items>
          <item type="boardgame" id="13">
            <name type="primary" value="Catan"/>
            <yearpublished value="1995"/>
          </item>
        </items>'''

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = mock_xml
            mock_response.headers = {'content-type': 'text/xml'}
            mock_get.return_value = mock_response

            result = await fetch_bgg_thing(13)

            assert result['title'] == 'Catan'
            assert result['year'] == 1995

    async def test_fetch_invalid_id(self):
        """Should raise error for invalid game ID"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_get.return_value = mock_response

            with pytest.raises(BGGServiceError, match="Invalid BGG ID"):
                await fetch_bgg_thing(99999999)

    async def test_retry_on_rate_limit(self):
        """Should retry on 202 status with exponential backoff"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # First two calls return 202, third succeeds
            responses = [
                AsyncMock(status_code=202),
                AsyncMock(status_code=202),
                AsyncMock(
                    status_code=200,
                    text='<?xml version="1.0"?><items><item id="1"/></items>',
                    headers={'content-type': 'text/xml'}
                )
            ]
            mock_get.side_effect = responses

            result = await fetch_bgg_thing(1)

            assert mock_get.call_count == 3  # Retried twice

    async def test_timeout_handling(self):
        """Should handle timeout errors with retries"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")

            with pytest.raises(BGGServiceError, match="Timeout"):
                await fetch_bgg_thing(1)
```

### Week 6: Frontend API Client & Hooks Tests

**Priority Tests:**
1. **API Client Tests** (`src/api/__tests__/client.test.js`)
   - Request formation
   - Error handling
   - Authentication headers
   - Response parsing

2. **Custom Hooks Tests** (`src/hooks/__tests__/`)
   - useAuth hook
   - useToast hook
   - Potential new hooks extracted from PublicCatalogue

```jsx
// src/api/__tests__/client.test.js
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setupServer } from 'msw/node'
import { rest } from 'msw'
import { getPublicGames, getPublicGame } from '../client'

const server = setupServer()

beforeEach(() => server.listen())
afterEach(() => server.resetHandlers())

describe('API Client', () => {
  describe('getPublicGames', () => {
    it('fetches games successfully', async () => {
      server.use(
        rest.get('*/api/public/games', (req, res, ctx) => {
          return res(ctx.json({
            total: 2,
            page: 1,
            page_size: 24,
            items: [
              { id: 1, title: 'Game 1' },
              { id: 2, title: 'Game 2' }
            ]
          }))
        })
      )

      const result = await getPublicGames()

      expect(result.total).toBe(2)
      expect(result.items).toHaveLength(2)
    })

    it('handles network errors', async () => {
      server.use(
        rest.get('*/api/public/games', (req, res, ctx) => {
          return res.networkError('Failed to connect')
        })
      )

      await expect(getPublicGames()).rejects.toThrow()
    })

    it('sends query parameters correctly', async () => {
      let capturedParams = {}

      server.use(
        rest.get('*/api/public/games', (req, res, ctx) => {
          capturedParams = Object.fromEntries(req.url.searchParams)
          return res(ctx.json({ total: 0, items: [] }))
        })
      )

      await getPublicGames({ q: 'test', category: 'GATEWAY_STRATEGY' })

      expect(capturedParams.q).toBe('test')
      expect(capturedParams.category).toBe('GATEWAY_STRATEGY')
    })
  })
})
```

### Week 7-8: Integration Tests for Critical Flows

**Critical User Flows:**

1. **Game Search & Filter Flow**
   ```python
   # test_api/test_integration_search.py
   def test_search_filter_flow(test_client, test_db):
       """Integration test: Search → Filter → Sort → Paginate"""
       # Setup: Create diverse test data
       # Execute: Complex query with multiple filters
       # Assert: Correct games returned in correct order
   ```

2. **BGG Import Flow**
   ```python
   # test_api/test_integration_bgg_import.py
   @pytest.mark.asyncio
   async def test_full_bgg_import_flow(test_client):
       """Integration test: BGG search → Import → Thumbnail download → DB save"""
       # Mock BGG API responses
       # Execute import
       # Verify game created with all data
       # Verify thumbnail downloaded
   ```

3. **Admin Management Flow**
   ```python
   # test_api/test_integration_admin.py
   def test_admin_game_management_flow(test_client):
       """Integration test: Login → Create → Update → Delete"""
       # Login
       # Create game
       # Update game
       # Delete game
       # Verify at each step
   ```

---

## Phase 3: Refinement (Weeks 9-12)

**Goal:** Reach 70%+ coverage and establish best practices

### Week 9: E2E Tests for Critical Paths

**Setup:**
```bash
npm install --save-dev @playwright/test
npx playwright install
```

**Test File:** `e2e/critical-paths.spec.js`

```javascript
import { test, expect } from '@playwright/test'

test.describe('Critical User Journeys', () => {
  test('Public user can browse and filter games', async ({ page }) => {
    // Navigate to home page
    await page.goto('http://localhost:3000')

    // Wait for games to load
    await expect(page.locator('[data-testid="game-card"]')).toHaveCount.greaterThan(0)

    // Filter by category
    await page.click('text=Gateway Strategy')
    await page.waitForLoadState('networkidle')

    // Verify filtered results
    const cards = page.locator('[data-testid="game-card"]')
    const count = await cards.count()
    expect(count).toBeGreaterThan(0)

    // Search for specific game
    await page.fill('[placeholder="Search games..."]', 'Catan')
    await page.waitForTimeout(200) // Debounce

    // Click on game to view details
    await page.click('text=Catan')

    // Verify game details page
    await expect(page).toHaveURL(/\/game\/\d+/)
    await expect(page.locator('h1')).toContainText('Catan')
  })

  test('Admin can log in and manage games', async ({ page }) => {
    // Navigate to admin login
    await page.goto('http://localhost:3000/staff/login')

    // Enter credentials
    await page.fill('[name="token"]', process.env.TEST_ADMIN_TOKEN)
    await page.click('button[type="submit"]')

    // Verify successful login
    await expect(page).toHaveURL(/\/staff/)

    // Navigate to manage library
    await page.click('text=Manage Library')

    // Edit a game
    await page.click('[data-testid="edit-game"]:first-of-type')
    await page.fill('[name="title"]', 'Updated Title')
    await page.click('text=Save')

    // Verify update
    await expect(page.locator('text=Updated Title')).toBeVisible()
  })

  test('BGG import workflow', async ({ page }) => {
    // Login as admin
    await page.goto('http://localhost:3000/staff/login')
    await page.fill('[name="token"]', process.env.TEST_ADMIN_TOKEN)
    await page.click('button[type="submit"]')

    // Navigate to import
    await page.click('text=Add Games')

    // Enter BGG ID
    await page.fill('[name="bgg_id"]', '13')  // Catan
    await page.click('text=Import from BGG')

    // Wait for import to complete
    await expect(page.locator('text=Import successful')).toBeVisible({ timeout: 10000 })

    // Verify game appears in library
    await page.click('text=Manage Library')
    await expect(page.locator('text=Catan')).toBeVisible()
  })
})

// Run with: npx playwright test
```

**E2E Tests to Add:** 10-15 critical path tests

### Week 10: Edge Cases & Error Scenarios

**Focus Areas:**
1. **Boundary Conditions**
   - Empty results
   - Large datasets (1000+ games)
   - Special characters in titles
   - Null/undefined values

2. **Error Scenarios**
   - Network failures
   - Database connection loss
   - Invalid input data
   - Concurrent requests

3. **Security Tests**
   - SQL injection attempts
   - XSS attempts
   - CSRF validation
   - Rate limiting enforcement

### Week 11: Performance & Load Testing

**Backend Performance Tests:**
```python
# test_api/test_performance.py
import pytest
import time

def test_game_list_performance(test_client, benchmark_games):
    """Should return results in <200ms with 1000 games"""
    # Create 1000 test games

    start = time.time()
    response = test_client.get("/api/public/games?page_size=24")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 0.2  # 200ms threshold

def test_search_performance(test_client, benchmark_games):
    """Should search 1000 games in <300ms"""
    start = time.time()
    response = test_client.get("/api/public/games?q=test")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 0.3  # 300ms threshold
```

**Frontend Performance Tests:**
```javascript
// src/pages/__tests__/PublicCatalogue.performance.test.jsx
import { test, expect } from '@playwright/test'

test('Catalogue renders 100 games in <2s', async ({ page }) => {
  const startTime = Date.now()

  await page.goto('http://localhost:3000')
  await page.waitForSelector('[data-testid="game-card"]:nth-child(24)')

  const loadTime = Date.now() - startTime
  expect(loadTime).toBeLessThan(2000)
})
```

### Week 12: Documentation & CI/CD Integration

**Documentation:**
1. Create `TESTING_GUIDE.md` with:
   - How to run tests locally
   - How to write new tests
   - Testing conventions
   - Mocking strategies
   - Fixtures and factories

2. Update `CONTRIBUTING.md` with:
   - Test coverage requirements for PRs
   - Testing checklist

**CI/CD Enhancements:**
```yaml
# .github/workflows/test.yml
name: Test Coverage

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest-cov
      - name: Run tests with coverage
        run: |
          cd backend
          pytest --cov --cov-report=xml --cov-fail-under=70
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
          flags: backend
          fail_ci_if_error: true

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests with coverage
        run: |
          cd frontend
          npm test -- --coverage --run
      - name: Check coverage thresholds
        run: |
          cd frontend
          npm run test:coverage-check
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./frontend/coverage/lcov.info
          flags: frontend
          fail_ci_if_error: true

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Start backend
        run: |
          cd backend
          uvicorn main:app &
      - name: Start frontend
        run: |
          cd frontend
          npm run dev &
      - name: Run E2E tests
        run: npx playwright test
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

**Coverage Badges:**
```markdown
# README.md
[![Backend Coverage](https://codecov.io/gh/your-org/your-repo/branch/main/graph/badge.svg?flag=backend)](https://codecov.io/gh/your-org/your-repo)
[![Frontend Coverage](https://codecov.io/gh/your-org/your-repo/branch/main/graph/badge.svg?flag=frontend)](https://codecov.io/gh/your-org/your-repo)
```

---

## Coverage Targets by Module

| Module | Current | Week 4 | Week 8 | Week 12 | Priority |
|--------|---------|--------|--------|---------|----------|
| **Backend Services** | <5% | 60% | 80% | 85% | 🔴 Critical |
| **Backend API Routes** | <5% | 40% | 65% | 75% | 🔴 Critical |
| **Backend Utils** | <5% | 50% | 70% | 80% | 🟡 Medium |
| **Frontend Components** | <5% | 45% | 60% | 70% | 🟠 High |
| **Frontend Pages** | 0% | 35% | 55% | 70% | 🟠 High |
| **Frontend Utils** | <5% | 50% | 70% | 75% | 🟡 Medium |
| **Integration Tests** | 0% | N/A | 40% | 60% | 🟠 High |
| **E2E Tests** | 0% | N/A | N/A | 15 tests | 🟡 Medium |

---

## Testing Tools & Dependencies

### Backend
```txt
# requirements-test.txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
pytest-mock==3.12.0
faker==20.1.0
factory-boy==3.3.0
freezegun==1.4.0
responses==0.24.1
```

### Frontend
```json
{
  "devDependencies": {
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.1.5",
    "@testing-library/user-event": "^14.5.1",
    "@vitest/ui": "^1.0.4",
    "vitest": "^1.0.4",
    "jsdom": "^23.0.1",
    "msw": "^2.0.11",
    "@playwright/test": "^1.40.1"
  }
}
```

---

## Success Metrics

### Quantitative Metrics
- ✅ Backend coverage: 70%+ (from <10%)
- ✅ Frontend coverage: 70%+ (from <5%)
- ✅ Unit tests: 250-300 tests
- ✅ Integration tests: 60-75 tests
- ✅ E2E tests: 10-15 critical paths
- ✅ Test execution time: <5 minutes for full suite
- ✅ CI/CD pass rate: >95%

### Qualitative Metrics
- ✅ Tests serve as living documentation
- ✅ Confidence in refactoring without breaking changes
- ✅ Faster onboarding for new developers
- ✅ Reduced production bugs
- ✅ Easier debugging with test isolation

---

## Maintenance & Best Practices

### Test Hygiene
1. **Keep tests simple and focused** - One assertion per test when possible
2. **Use descriptive test names** - "Should return 404 when game not found"
3. **Avoid test interdependencies** - Each test should be independent
4. **Use factories for test data** - Don't duplicate setup code
5. **Mock external services** - Don't hit real BGG API in tests

### Code Review Checklist
- [ ] New features include tests
- [ ] Tests cover happy path and edge cases
- [ ] Test names clearly describe what's being tested
- [ ] No hardcoded values (use fixtures/factories)
- [ ] Tests are fast (<100ms per unit test)
- [ ] Integration tests clean up after themselves

### Continuous Improvement
- **Weekly:** Review test failures and flaky tests
- **Monthly:** Review coverage reports for gaps
- **Quarterly:** Update test infrastructure and dependencies
- **Yearly:** Re-evaluate testing strategy and tools

---

## Resources & References

### Testing Guides
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [React Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Testing Trophy](https://kentcdodds.com/blog/write-tests) by Kent C. Dodds

### Internal Documentation
- See `CODE_REVIEW_COMPREHENSIVE.md` for code quality context
- See `ARCHITECTURE.md` for system design
- See `API_REFERENCE.md` for endpoint specifications

---

## Appendix: Quick Reference Commands

### Run All Tests
```bash
# Backend
cd backend && pytest --cov --cov-report=html

# Frontend
cd frontend && npm test -- --coverage

# E2E
npx playwright test

# Full suite
./scripts/run_all_tests.sh
```

### Coverage Reports
```bash
# Backend HTML report
cd backend && pytest --cov --cov-report=html
open backend/htmlcov/index.html

# Frontend coverage
cd frontend && npm test -- --coverage
open frontend/coverage/index.html
```

### Watch Mode (Development)
```bash
# Backend watch
cd backend && pytest-watch

# Frontend watch
cd frontend && npm test -- --watch
```

---

**End of Test Coverage Improvement Plan**

*Next Steps:*
1. Review and approve this plan
2. Begin Week 1 infrastructure setup
3. Schedule weekly coverage review meetings
4. Celebrate hitting 30% coverage milestone! 🎉

*Questions or Clarifications:* Contact dev team leads
