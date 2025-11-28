# Tests

Test suite for Mana & Meeples Board Game Library API.

## Test Files

- **test_main.py** - Main application endpoint tests
- **test_db_connection.py** - Database connection and health tests

## Running Tests

### Prerequisites
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_main.py
pytest tests/test_db_connection.py
```

### Run with Coverage
```bash
pytest --cov=. tests/
```

## Test Structure

Tests are organized to match the application structure:
- API endpoint tests
- Database connectivity tests
- Integration tests

## Adding New Tests

When adding new tests:
1. Follow existing test file naming: `test_*.py`
2. Use descriptive test function names: `test_feature_description`
3. Include docstrings explaining what the test validates
4. Mock external dependencies (BGG API, database when appropriate)

## CI/CD Integration

These tests should be run:
- Before each commit (pre-commit hook)
- On pull request creation
- Before deployment to production
