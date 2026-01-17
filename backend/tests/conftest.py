"""
Pytest configuration and fixtures for backend tests
"""
import os
import pytest
import pytest_asyncio
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment variables
# Use in-memory SQLite with StaticPool for thread-safe testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ADMIN_TOKEN"] = "test_admin_token"
# Allow test client origin for CORS (http://test is used by async_client)
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://test"
# Disable rate limiting during tests to prevent test failures
os.environ["DISABLE_RATE_LIMITING"] = "true"

from database import Base
from main import app


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the cache and rate limiters before each test to prevent test pollution"""
    from utils.cache import clear_cache as clear_cache_func
    from shared.rate_limiting import admin_attempt_tracker

    clear_cache_func()
    # Clear admin rate limit tracker to prevent 429 errors in tests
    admin_attempt_tracker.clear()

    # Clear BGG rate limiter to prevent test pollution
    try:
        from bgg_service import bgg_rate_limiter
        bgg_rate_limiter.requests.clear()
    except ImportError:
        pass  # bgg_service might not be imported yet

    yield

    # Clear again after test to ensure clean state
    clear_cache_func()
    admin_attempt_tracker.clear()

    # Clear BGG rate limiter after test
    try:
        from bgg_service import bgg_rate_limiter
        bgg_rate_limiter.requests.clear()
    except ImportError:
        pass


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine with shared cache"""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool  # Use StaticPool for thread-safe in-memory SQLite
    )
    Base.metadata.create_all(engine)
    yield engine
    # Safely cleanup - ignore errors if connections are already closed
    try:
        Base.metadata.drop_all(engine)
    except Exception:
        pass
    try:
        engine.dispose()
    except Exception:
        pass


@pytest.fixture(scope="function")
def db_session(db_engine) -> Session:
    """Create a test database session"""
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        # Ensure cleanup even if test fails
        try:
            session.rollback()
        except Exception:
            pass
        try:
            session.close()
        except Exception:
            pass


@pytest.fixture(scope="function")
def client(db_engine):
    """Create a test API client with database override"""
    from database import get_db, get_read_db
    import database as db_module
    from unittest.mock import AsyncMock
    from sqlalchemy.pool import StaticPool

    # Store original engine and SessionLocal
    original_engine = db_module.engine
    original_SessionLocal = db_module.SessionLocal
    original_ReadSessionLocal = db_module.ReadSessionLocal

    # Override the engine with test engine (this is needed for some parts of the app)
    db_module.engine = db_engine

    # Create a NEW session factory for testing that's thread-safe
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    # Override SessionLocal in the database module so any direct usage also works
    db_module.SessionLocal = TestSessionLocal
    db_module.ReadSessionLocal = TestSessionLocal

    def override_get_db():
        """Create a new session for each request (thread-safe)"""
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    # Override both get_db and get_read_db
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_read_db] = override_get_db

    # Mock the db_ping to prevent startup issues
    # Patch them where they're imported (in main.py), not where they're defined
    # Also patch os.makedirs and httpx_client.aclose for lifespan events
    # Note: run_migrations removed - now using Alembic migrations
    with patch('main.db_ping', return_value=True), \
         patch('main.os.makedirs', return_value=None), \
         patch('main.httpx_client.aclose', new_callable=AsyncMock):
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client

    # Restore original engine and SessionLocal
    db_module.engine = original_engine
    db_module.SessionLocal = original_SessionLocal
    db_module.ReadSessionLocal = original_ReadSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
def sample_game_data():
    """Sample game data for testing"""
    import random
    # Use a random BGG ID to avoid conflicts between tests
    # Keep within schema validator limit: 1 <= bgg_id <= 999999
    unique_bgg_id = random.randint(30000, 999999)

    return {
        "title": "Pandemic",
        "year": 2008,
        "players_min": 2,
        "players_max": 4,
        "playtime_min": 45,
        "playtime_max": 45,
        "mana_meeple_category": "COOP_ADVENTURE",
        "complexity": 2.43,
        "average_rating": 7.6,
        "bgg_id": unique_bgg_id,
        "designers": ["Matt Leacock"],
        "mechanics": ["Action Points", "Cooperative Game", "Point to Point Movement"],
        "min_age": 8,
        "is_cooperative": True,
        "status": "OWNED"
    }


@pytest.fixture
def sample_games_list():
    """Multiple sample games for testing lists and filters"""
    return [
        {
            "title": "Pandemic",
            "year": 2008,
            "players_min": 2,
            "players_max": 4,
            "playtime_min": 45,
            "mana_meeple_category": "COOP_ADVENTURE",
            "complexity": 2.43,
            "nz_designer": False,
            "status": "OWNED"
        },
        {
            "title": "Catan",
            "year": 1995,
            "players_min": 3,
            "players_max": 4,
            "playtime_min": 60,
            "mana_meeple_category": "GATEWAY_STRATEGY",
            "complexity": 2.32,
            "nz_designer": False,
            "status": "OWNED"
        },
        {
            "title": "7 Wonders",
            "year": 2010,
            "players_min": 2,
            "players_max": 7,
            "playtime_min": 30,
            "mana_meeple_category": "CORE_STRATEGY",
            "complexity": 2.33,
            "nz_designer": False,
            "status": "OWNED"
        },
        {
            "title": "Codenames",
            "year": 2015,
            "players_min": 2,
            "players_max": 8,
            "playtime_min": 15,
            "mana_meeple_category": "PARTY_ICEBREAKERS",
            "complexity": 1.31,
            "nz_designer": False,
            "status": "OWNED"
        }
    ]


@pytest.fixture
def admin_headers():
    """Headers with admin authentication and CSRF protection"""
    return {
        "X-Admin-Token": "test_admin_token",
        "Origin": "http://localhost:3000"  # Required for CSRF protection
    }


@pytest.fixture
def csrf_headers():
    """Headers with only CSRF protection (for unauthorized tests)"""
    return {
        "Origin": "http://localhost:3000"  # Required for CSRF protection
    }


@pytest.fixture
def sample_game(db_session):
    """Create a sample game in the database for testing"""
    from models import Game
    import random

    # Use a random bgg_id to avoid conflicts between tests
    # This ensures each test gets a unique game even if using shared cache
    # Keep within schema validator limit: 1 <= bgg_id <= 999999
    unique_bgg_id = random.randint(10000, 999999)

    game = Game(
        title="Test Game",
        bgg_id=unique_bgg_id,
        year=2023,
        players_min=2,
        players_max=4,
        playtime_min=30,
        playtime_max=60,
        mana_meeple_category="GATEWAY_STRATEGY",
        complexity=2.5,
        average_rating=7.5,
        status="OWNED",
        designers=["Test Designer"]
    )
    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)
    return game


@pytest.fixture
def large_game_dataset(db_session):
    """Create a large dataset for performance testing"""
    from models import Game

    games = []
    for i in range(500):  # Create 500 games
        game = Game(
            title=f"Performance Test Game {i}",
            bgg_id=100000 + i,
            year=2000 + (i % 25),
            players_min=2,
            players_max=6,
            playtime_min=30,
            playtime_max=120,
            complexity=1.0 + (i % 5),
            average_rating=6.0 + (i % 4),
            mana_meeple_category=['GATEWAY_STRATEGY', 'COOP_ADVENTURE', 'PARTY_ICEBREAKERS', 'KIDS_FAMILIES'][i % 4],
            status="OWNED",
            designers=[f"Designer {i % 100}"],
            nz_designer=(i % 10 == 0)  # Every 10th game is NZ designer
        )
        games.append(game)
        db_session.add(game)

    db_session.commit()
    return games


@pytest_asyncio.fixture
async def async_client(db_engine):
    """
    Create an async test client for integration tests.
    Required for testing async endpoints with @pytest.mark.asyncio.
    """
    from httpx import AsyncClient, ASGITransport
    from database import get_db, get_read_db
    import database as db_module
    from unittest.mock import AsyncMock
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.orm import sessionmaker

    # Store originals
    original_engine = db_module.engine
    original_SessionLocal = db_module.SessionLocal
    original_ReadSessionLocal = db_module.ReadSessionLocal

    # Override with test engine
    db_module.engine = db_engine
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db_module.SessionLocal = TestSessionLocal
    db_module.ReadSessionLocal = TestSessionLocal

    def override_get_db():
        """Create a new session for each request"""
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_read_db] = override_get_db

    # Mock startup/shutdown events
    with patch('main.db_ping', return_value=True), \
         patch('main.os.makedirs', return_value=None), \
         patch('main.httpx_client.aclose', new_callable=AsyncMock):
        # Use ASGITransport to test the ASGI app directly (not real HTTP)
        # This is the proper way to test FastAPI apps with AsyncClient
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac

    # Restore originals
    db_module.engine = original_engine
    db_module.SessionLocal = original_SessionLocal
    db_module.ReadSessionLocal = original_ReadSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
def sample_bgg_xml():
    """Realistic BGG XML for testing BGG service and parser"""
    return '''<?xml version="1.0" encoding="utf-8"?>
<items termsofuse="https://boardgamegeek.com/xmlapi/termsofuse">
  <item type="boardgame" id="174430">
    <thumbnail>//cf.geekdo-images.com/sZYp_3BTDGjh2unaZfZmuQ__thumb/img/pBuvi1_NpmNjw6VPgaSaMVrpJ_c=/fit-in/200x150/filters:strip_icc()/pic2437871.jpg</thumbnail>
    <image>//cf.geekdo-images.com/sZYp_3BTDGjh2unaZfZmuQ__original/img/EvIlyAL_MxmejAPKVAFDVKPVo_8=/0x0/filters:format(jpeg)/pic2437871.jpg</image>
    <name type="primary" value="Gloomhaven"/>
    <name type="alternate" value="גלומהייבן"/>
    <description>Gloomhaven is a game of Euro-inspired tactical combat in a persistent world of shifting motives.</description>
    <yearpublished value="2017"/>
    <minplayers value="1"/>
    <maxplayers value="4"/>
    <minplaytime value="60"/>
    <maxplaytime value="120"/>
    <minage value="14"/>
    <link type="boardgamecategory" id="1022" value="Adventure"/>
    <link type="boardgamecategory" id="1020" value="Exploration"/>
    <link type="boardgamecategory" id="1010" value="Fantasy"/>
    <link type="boardgamemechanic" id="2018" value="Campaign / Battle Card Driven"/>
    <link type="boardgamemechanic" id="2023" value="Cooperative Game"/>
    <link type="boardgamemechanic" id="2040" value="Hand Management"/>
    <link type="boardgamedesigner" id="69802" value="Isaac Childres"/>
    <link type="boardgamepublisher" id="23202" value="Cephalofair Games"/>
    <link type="boardgameartist" id="69802" value="Isaac Childres"/>
    <statistics page="1">
      <ratings>
        <usersrated value="93420"/>
        <average value="8.67883"/>
        <bayesaverage value="8.36264"/>
        <averageweight value="3.87"/>
        <ranks>
          <rank type="subtype" id="1" name="boardgame" friendlyname="Board Game Rank" value="1"/>
          <rank type="family" id="5497" name="strategygames" friendlyname="Strategy Game Rank" value="1"/>
          <rank type="family" id="5499" name="thematic" friendlyname="Thematic Rank" value="1"/>
        </ranks>
      </ratings>
    </statistics>
  </item>
</items>'''


@pytest.fixture
def sample_bgg_xml_expansion():
    """BGG XML for an expansion (for testing expansion detection)"""
    return '''<?xml version="1.0" encoding="utf-8"?>
<items termsofuse="https://boardgamegeek.com/xmlapi/termsofuse">
  <item type="boardgameexpansion" id="239188">
    <thumbnail>//cf.geekdo-images.com/thumb/img/test.jpg</thumbnail>
    <image>//cf.geekdo-images.com/original/img/test.jpg</image>
    <name type="primary" value="Gloomhaven: Forgotten Circles"/>
    <description>An expansion for Gloomhaven featuring a new campaign.</description>
    <yearpublished value="2019"/>
    <minplayers value="1"/>
    <maxplayers value="4"/>
    <minplaytime value="60"/>
    <maxplaytime value="120"/>
    <minage value="14"/>
    <link type="boardgamecategory" id="1022" value="Adventure"/>
    <link type="boardgamemechanic" id="2023" value="Cooperative Game"/>
    <link type="boardgamedesigner" id="69802" value="Isaac Childres"/>
    <link type="boardgamepublisher" id="23202" value="Cephalofair Games"/>
    <link type="boardgameexpansion" id="174430" value="Gloomhaven" inbound="true"/>
    <statistics page="1">
      <ratings>
        <usersrated value="5000"/>
        <average value="7.5"/>
        <averageweight value="3.8"/>
        <ranks>
          <rank type="subtype" id="1" name="boardgame" value="500"/>
        </ranks>
      </ratings>
    </statistics>
  </item>
</items>'''


@pytest.fixture
def sample_bgg_xml_minimal():
    """Minimal BGG XML with missing optional fields (for testing parser robustness)"""
    return '''<?xml version="1.0" encoding="utf-8"?>
<items termsofuse="https://boardgamegeek.com/xmlapi/termsofuse">
  <item type="boardgame" id="999">
    <name type="primary" value="Minimal Game"/>
    <yearpublished value="2020"/>
  </item>
</items>'''


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for BGG service testing"""
    from unittest.mock import AsyncMock, MagicMock

    mock = MagicMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)

    return mock


@pytest.fixture
def mock_cloudinary_service():
    """Mock Cloudinary service for image testing"""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.enabled = True
    mock.upload_from_url.return_value = {
        'public_id': 'test_public_id',
        'secure_url': 'https://cloudinary.com/test.jpg',
        'format': 'jpg',
        'width': 500,
        'height': 500
    }
    mock.get_image_url.return_value = 'https://cloudinary.com/test_optimized.jpg'

    return mock
