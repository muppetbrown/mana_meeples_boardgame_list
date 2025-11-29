# Testing Guide

Comprehensive guide for running and writing tests for the Mana & Meeples Board Game Library.

## Overview

The project uses a comprehensive testing strategy across both backend and frontend:

- **Backend**: pytest with FastAPI TestClient and SQLAlchemy fixtures
- **Frontend**: Jest and React Testing Library (via Create React App)
- **CI/CD**: GitHub Actions for automated testing on every push

## Backend Testing

### Test Structure

```
backend/tests/
├── conftest.py              # Shared fixtures and configuration
├── pytest.ini               # Pytest settings
├── test_api/                # API endpoint tests
│   ├── test_public.py       # Public endpoints
│   └── test_admin.py        # Admin endpoints
├── test_services/           # Business logic tests (future)
└── test_integration/        # End-to-end tests (future)
```

### Running Backend Tests

```bash
# Navigate to backend directory
cd backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api/test_public.py

# Run with coverage
pytest --cov=. --cov-report=html
# View coverage report at: htmlcov/index.html

# Run specific test class
pytest tests/test_api/test_public.py::TestPublicGamesEndpoint

# Run specific test
pytest tests/test_api/test_public.py::TestPublicGamesEndpoint::test_get_games_empty_database
```

### Backend Test Coverage

Current test coverage:
- ✅ Public game listing (GET /api/public/games)
- ✅ Game detail endpoint (GET /api/public/games/{id})
- ✅ Category counts (GET /api/public/category-counts)
- ✅ Admin authentication
- ✅ Admin CRUD operations
- ✅ Health check endpoints
- 🔄 Search and filtering (in progress)
- 🔄 Bulk operations (planned)
- 🔄 BGG integration (planned)

### Writing Backend Tests

Example test structure:

```python
def test_get_games_with_filters(client, db_session, sample_games_list):
    """Test getting games with category filter"""
    # Arrange - set up test data
    for game_data in sample_games_list:
        game = Game(**game_data)
        db_session.add(game)
    db_session.commit()

    # Act - perform the action
    response = client.get("/api/public/games?category=COOP_ADVENTURE")

    # Assert - verify the result
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Pandemic"
```

### Backend Fixtures

Available fixtures (defined in `conftest.py`):
- `client` - FastAPI TestClient for API requests
- `db_session` - SQLAlchemy session with in-memory SQLite
- `db_engine` - SQLAlchemy engine
- `sample_game_data` - Single game data dictionary
- `sample_games_list` - Multiple games for testing filters
- `admin_headers` - Headers with admin authentication

## Frontend Testing

### Test Structure

```
frontend/src/
├── setupTests.js                              # Jest configuration
├── components/
│   ├── __tests__/
│   │   └── CategoryFilter.test.jsx
│   └── public/
│       └── __tests__/
│           └── GameCardPublic.test.jsx
└── pages/
    └── __tests__/                             # (future)
```

### Running Frontend Tests

```bash
# Navigate to frontend directory
cd frontend

# Run all tests (interactive watch mode)
npm test

# Run all tests once (for CI)
npm run test:ci

# Run with coverage
npm run test:ci
# Coverage report will be in: coverage/

# Run specific test file (in watch mode)
npm test GameCardPublic
```

### Frontend Test Coverage

Current test coverage:
- ✅ GameCardPublic component
- ✅ CategoryFilter component
- 🔄 SearchBox component (planned)
- 🔄 Pagination component (planned)
- 🔄 GameImage component (planned)
- 🔄 Page components (planned)

### Writing Frontend Tests

Example component test:

```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import MyComponent from '../MyComponent';

// Wrapper for components using React Router
const RouterWrapper = ({ children }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('MyComponent', () => {
  it('renders component correctly', () => {
    render(
      <RouterWrapper>
        <MyComponent data="test" />
      </RouterWrapper>
    );

    expect(screen.getByText('test')).toBeInTheDocument();
  });

  it('handles user interaction', () => {
    const mockHandler = jest.fn();
    render(
      <RouterWrapper>
        <MyComponent onClick={mockHandler} />
      </RouterWrapper>
    );

    fireEvent.click(screen.getByRole('button'));
    expect(mockHandler).toHaveBeenCalled();
  });
});
```

## CI/CD Testing

### GitHub Actions Workflow

Tests run automatically on:
- Every push to `main` branch
- Every push to branches starting with `claude/`
- Every pull request to `main`

Workflow file: `.github/workflows/test.yml`

### CI Pipeline Steps

1. **Backend Tests Job**
   - Sets up Python 3.11
   - Installs dependencies
   - Runs pytest with PostgreSQL service
   - Generates coverage report
   - Uploads coverage to Codecov

2. **Frontend Tests Job**
   - Sets up Node.js 18
   - Installs dependencies
   - Runs tests with coverage
   - Builds production bundle
   - Uploads build artifacts

3. **Lint Job**
   - Runs flake8 for Python linting
   - Runs black for Python formatting checks

4. **All Tests Passed Job**
   - Verifies all jobs succeeded
   - Fails if any job failed

### Viewing CI Results

1. Go to the **Actions** tab on GitHub
2. Click on the workflow run
3. View individual job results
4. Download artifacts (e.g., frontend build)

## Test Coverage Goals

### Current Coverage
- Backend: ~60% (tests added in Phase 4)
- Frontend: ~40% (basic component tests)

### Target Coverage
- Backend API: >90%
- Frontend Components: >70%
- Overall: >70%

## Best Practices

### General
- ✅ Write tests for new features
- ✅ Update tests when modifying code
- ✅ Run tests locally before pushing
- ✅ Keep tests simple and focused
- ✅ Use descriptive test names
- ✅ Follow AAA pattern (Arrange, Act, Assert)

### Backend Specific
- ✅ Use fixtures for test data
- ✅ Test both success and error cases
- ✅ Test authentication and authorization
- ✅ Mock external services (BGG API)
- ✅ Use in-memory database for speed

### Frontend Specific
- ✅ Test user interactions, not implementation
- ✅ Use `screen.getByRole()` over `getByTestId()`
- ✅ Test accessibility
- ✅ Mock API calls
- ✅ Test error states

## Troubleshooting

### Backend Tests

**Issue**: `ModuleNotFoundError`
- **Solution**: Run tests from `backend/` directory or use `python -m pytest`

**Issue**: Database errors
- **Solution**: Tests use in-memory SQLite, ensure conftest.py is present

**Issue**: Import errors
- **Solution**: Check Python path, imports should be relative within backend/

### Frontend Tests

**Issue**: `Cannot find module`
- **Solution**: Run `npm install` in frontend/ directory

**Issue**: Router errors in tests
- **Solution**: Wrap components in `<BrowserRouter>`

**Issue**: Tests hang in watch mode
- **Solution**: Press `q` to quit, or use `npm run test:ci` for one-time run

## Adding New Tests

### Backend

1. Create test file in appropriate directory
2. Import necessary fixtures from conftest
3. Write test classes and functions
4. Run `pytest tests/your_test_file.py`

### Frontend

1. Create `__tests__` directory next to component
2. Create `ComponentName.test.jsx`
3. Import testing utilities and component
4. Write test cases
5. Run `npm test ComponentName`

## Continuous Integration

All tests must pass before:
- Merging to `main` branch
- Deploying to production

Failed tests will block the CI pipeline and prevent merges.

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [React Testing Library](https://testing-library.com/react)
- [Jest Documentation](https://jestjs.io/)

---

**Last Updated**: Phase 4 (Testing & CI/CD)
**Maintainer**: Development Team
