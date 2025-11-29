# Backend Tests

Comprehensive test suite for the Mana & Meeples API backend.

## Structure

```
tests/
├── conftest.py           # Pytest fixtures and configuration
├── test_api/             # API endpoint tests
│   ├── test_public.py    # Public endpoints (/api/public/*)
│   └── test_admin.py     # Admin endpoints (/api/admin/*)
├── test_services/        # Business logic tests (future)
└── test_integration/     # End-to-end tests (future)
```

## Running Tests

### Run all tests
```bash
cd backend
pytest
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Run specific test file
```bash
pytest tests/test_api/test_public.py
```

### Run specific test class
```bash
pytest tests/test_api/test_public.py::TestPublicGamesEndpoint
```

### Run specific test
```bash
pytest tests/test_api/test_public.py::TestPublicGamesEndpoint::test_get_games_empty_database
```

### Run with verbose output
```bash
pytest -v
```

### Run tests matching a pattern
```bash
pytest -k "admin"  # Runs all tests with "admin" in the name
```

## Test Categories

Tests are marked with categories:
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, database required)
- `@pytest.mark.api` - API endpoint tests

Run specific categories:
```bash
pytest -m unit          # Run only unit tests
pytest -m "not slow"    # Skip slow tests
```

## Writing Tests

### Basic Test Structure
```python
def test_something(client, db_session):
    """Test description"""
    # Arrange - set up test data
    game = Game(title="Test Game")
    db_session.add(game)
    db_session.commit()

    # Act - perform the action
    response = client.get("/api/public/games")

    # Assert - verify the result
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
```

### Available Fixtures
- `client` - FastAPI TestClient
- `db_session` - SQLAlchemy database session
- `db_engine` - SQLAlchemy engine
- `sample_game_data` - Single game data dict
- `sample_games_list` - Multiple games data list
- `admin_headers` - Headers with admin authentication

## Test Coverage Goals

- **Public API endpoints**: >90% coverage
- **Admin API endpoints**: >90% coverage
- **Business logic**: >80% coverage
- **Overall**: >70% coverage

## CI/CD Integration

Tests run automatically on:
- Every push to `main` or `claude/*` branches
- Every pull request to `main`

See `.github/workflows/test.yml` for CI configuration.
