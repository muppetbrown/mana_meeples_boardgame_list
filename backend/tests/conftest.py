"""
Pytest configuration and fixtures for backend tests
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ADMIN_TOKEN"] = "test_admin_token"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

from database import Base
from main import app


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
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
def client(db_session):
    """Create a test API client with database override"""
    from database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

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
