"""
Pytest configuration and fixtures for backend tests
"""
import os
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment variables
# Use shared cache mode for in-memory SQLite to share data across connections
os.environ["DATABASE_URL"] = "sqlite:///file:testdb?mode=memory&cache=shared&uri=true"
os.environ["ADMIN_TOKEN"] = "test_admin_token"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

from database import Base
from main import app


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine with shared cache"""
    engine = create_engine(
        "sqlite:///file:testdb?mode=memory&cache=shared",
        connect_args={"check_same_thread": False, "uri": True}
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Session:
    """Create a test database session"""
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine
    )
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(db_session, db_engine):
    """Create a test API client with database override"""
    from database import get_db
    import database as db_module

    # Store original engine
    original_engine = db_module.engine

    # Override the engine with test engine
    db_module.engine = db_engine

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Mock the db_ping and run_migrations to prevent startup issues
    # Patch them where they're imported (in main.py), not where they're defined
    with patch('main.db_ping', return_value=True), \
         patch('main.run_migrations', return_value=None):
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client

    # Restore original engine
    db_module.engine = original_engine
    app.dependency_overrides.clear()


@pytest.fixture
def sample_game_data():
    """Sample game data for testing"""
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
        "bgg_id": 30549,
        "designers": ["Matt Leacock"],
        "mechanics": ["Action Points", "Cooperative Game", "Point to Point Movement"],
        "min_age": 8,
        "is_cooperative": True
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
            "mana_meeple_category": "COOP_ADVENTURE",
            "complexity": 2.43,
            "nz_designer": False
        },
        {
            "title": "Catan",
            "year": 1995,
            "players_min": 3,
            "players_max": 4,
            "mana_meeple_category": "GATEWAY_STRATEGY",
            "complexity": 2.32,
            "nz_designer": False
        },
        {
            "title": "7 Wonders",
            "year": 2010,
            "players_min": 2,
            "players_max": 7,
            "mana_meeple_category": "CORE_STRATEGY",
            "complexity": 2.33,
            "nz_designer": False
        },
        {
            "title": "Codenames",
            "year": 2015,
            "players_min": 2,
            "players_max": 8,
            "mana_meeple_category": "PARTY_ICEBREAKERS",
            "complexity": 1.31,
            "nz_designer": False
        }
    ]


@pytest.fixture
def admin_headers():
    """Headers with admin authentication"""
    return {"X-Admin-Token": "test_admin_token"}


@pytest.fixture
def sample_game(db_session):
    """Create a sample game in the database for testing"""
    from models import Game

    game = Game(
        title="Test Game",
        bgg_id=12345,
        year=2023,
        players_min=2,
        players_max=4,
        playtime_min=30,
        playtime_max=60,
        mana_meeple_category="GATEWAY_STRATEGY",
        complexity=2.5,
        average_rating=7.5,
        status="OWNED",
        designers='["Test Designer"]'
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
            designers=f'["Designer {i % 100}"]',
            nz_designer=(i % 10 == 0)  # Every 10th game is NZ designer
        )
        games.append(game)
        db_session.add(game)

    db_session.commit()
    return games
