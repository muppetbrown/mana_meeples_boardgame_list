# Priority 1 Enhancements - Implementation Guide

This document describes the Priority 1 enhancements implemented as part of the comprehensive code review.

## Table of Contents

1. [Integration Tests](#1-integration-tests)
2. [Coverage Reports](#2-coverage-reports)
3. [API Versioning](#3-api-versioning)

---

## 1. Integration Tests

### Overview

Comprehensive integration test suite covering complete workflows from BGG import to public display.

### Location

- **Backend**: `backend/tests/test_integration/`
  - `test_game_workflow.py` - Game CRUD and BGG import workflows
  - `test_api_endpoints.py` - Complete HTTP request/response testing

### Test Coverage

#### Game Import Workflow
```python
# Complete workflow: BGG fetch → create → categorize → verify
test_complete_bgg_import_workflow()
test_import_update_workflow()
test_expansion_linking_workflow()
```

#### Public API Workflow
```python
# Filter, pagination, search testing
test_filter_and_pagination_workflow()
test_nz_designer_filter_workflow()
test_player_count_filter_workflow()
```

#### Admin Workflow
```python
# CRUD operations with authentication
test_create_update_delete_workflow()
test_bulk_categorization_workflow()
```

#### API Endpoints Integration
```python
# Full HTTP cycle testing
test_games_list_to_detail_workflow()
test_search_and_filter_workflow()
test_admin_create_update_delete_workflow()
test_bgg_import_workflow()
```

### Running Integration Tests

```bash
# Run all tests
cd backend
pytest

# Run only integration tests
pytest -m integration

# Run with verbose output
pytest tests/test_integration/ -v

# Run specific test file
pytest tests/test_integration/test_game_workflow.py
```

### Key Features

- **Async support**: Uses `@pytest.mark.asyncio` for async endpoints
- **Fixtures**: Leverages `async_client`, `db_session`, `admin_headers`
- **Real workflows**: Tests actual user scenarios end-to-end
- **Mocked BGG**: Uses mocked BGG responses for reliability

---

## 2. Coverage Reports

### Backend Coverage

#### Configuration Files

- **`.coveragerc`**: Coverage settings with exclusions and thresholds
- **`pytest.ini`**: Automatic coverage collection on test runs
- **`run_tests_with_coverage.sh`**: Convenient test runner script

#### Running Backend Coverage

```bash
cd backend

# Run tests with coverage (automatic)
pytest

# Run with custom options
./run_tests_with_coverage.sh

# Run without coverage
./run_tests_with_coverage.sh --no-cov

# Run only integration tests with coverage
./run_tests_with_coverage.sh --integration

# Open HTML report in browser
./run_tests_with_coverage.sh --open
```

#### Coverage Reports Generated

1. **HTML Report**: `backend/htmlcov/index.html`
   - Interactive web interface
   - Line-by-line coverage
   - Sortable by file/coverage percentage

2. **Terminal Report**: Console output with missing lines

3. **JSON Report**: `backend/coverage.json`
   - Machine-readable format
   - CI/CD integration support

#### Coverage Thresholds

- **Minimum**: 80% (build fails below this)
- **Excluded**:
  - Test files
  - Alembic migrations
  - Virtual environment
  - `__pycache__`

### Frontend Coverage

#### Configuration

- **`vite.config.js`**: Vitest coverage configuration with V8 provider
- **`package.json`**: npm scripts for coverage

#### Running Frontend Coverage

```bash
cd frontend

# Run tests with coverage
npm run test:coverage

# Watch mode with coverage
npm run test:coverage:watch

# Coverage with UI
npm run test:coverage:ui

# CI mode (run once)
npm run test:ci
```

#### Coverage Reports Generated

1. **HTML Report**: `frontend/coverage/index.html`
2. **Terminal Report**: Console output
3. **JSON Report**: `frontend/coverage/coverage-final.json`
4. **LCOV Report**: `frontend/coverage/lcov.info` (for CI tools)

#### Coverage Thresholds

- **Statements**: 80%
- **Branches**: 75%
- **Functions**: 80%
- **Lines**: 80%

#### Excluded Files

- `node_modules/`
- Test files (`**/*.test.{js,jsx}`)
- Test directories (`__tests__/`, `__mocks__/`)
- Build output (`build/`, `dist/`, `coverage/`)
- Configuration files

---

## 3. API Versioning

### Overview

Implements `/api/v1` versioning with backward compatibility for legacy `/api` endpoints.

### Architecture

```
/api/v1/public/games    → Versioned endpoint (recommended)
/api/public/games       → Legacy endpoint (maps to v1)
```

### Backend Implementation

#### Version Configuration

**File**: `backend/api/versioning.py`

```python
from api.versioning import version_info

# Current version
CURRENT_API_VERSION = "v1"

# Version info for clients
version_info.to_dict()
# {
#   "current_version": "v1",
#   "supported_versions": ["v1"],
#   "deprecated_versions": [],
#   "version_prefix_format": "/api/{version}",
#   "legacy_prefix": "/api (maps to /api/v1)"
# }
```

#### Router Registration

**File**: `backend/main.py`

```python
# V1 endpoints (recommended)
v1_router = FastAPI(title="API v1")
v1_router.include_router(public_router)
v1_router.include_router(admin_router)
# ... other routers
app.mount("/api/v1", v1_router)

# Legacy endpoints (backward compatibility)
app.include_router(public_router)  # Maps to v1
app.include_router(admin_router)
# ... other routers
```

#### Root Endpoint

```bash
curl http://localhost:8000/
```

Response:
```json
{
  "message": "Mana & Meeples Board Game Library API",
  "app_version": "2.0.0",
  "api_versioning": {
    "current_version": "v1",
    "supported_versions": ["v1"],
    "deprecated_versions": [],
    "version_prefix_format": "/api/{version}",
    "legacy_prefix": "/api (maps to v1)"
  },
  "endpoints": {
    "documentation": "/docs",
    "health_check": "/api/health",
    "api_v1": "/api/v1",
    "legacy_api": "/api (maps to v1)"
  },
  "recommended_base_url": "/api/v1"
}
```

### Frontend Implementation

#### Configuration

**File**: `frontend/src/config/api.js`

```javascript
// API version configuration
export const API_VERSION = "v1";  // Set to null for legacy

// Helper function for versioned URLs
export function getApiUrl(path) {
  const cleanPath = path.replace(/^\/+/, "");
  if (API_VERSION) {
    return `${API_BASE}/api/${API_VERSION}/${cleanPath}`;
  }
  return `${API_BASE}/api/${cleanPath}`;
}
```

#### API Client

**File**: `frontend/src/api/client.js`

```javascript
// Axios instance with versioned base URL
export const api = axios.create({
  baseURL: getApiUrl(''),  // Returns: http://example.com/api/v1
  withCredentials: true,
});

// All API calls automatically use v1
api.get("/public/games");  // → GET /api/v1/public/games
api.post("/admin/games");  // → POST /api/v1/admin/games
```

### Migration Path

#### For New Clients

Use versioned endpoints:
```bash
GET /api/v1/public/games
POST /api/v1/admin/games
```

#### For Existing Clients

Legacy endpoints continue to work:
```bash
GET /api/public/games  # Maps to /api/v1/public/games
POST /api/admin/games  # Maps to /api/v1/admin/games
```

#### Version Detection

Clients can query the root endpoint to discover supported versions:

```javascript
fetch('http://api.example.com/')
  .then(r => r.json())
  .then(data => {
    console.log('Current version:', data.api_versioning.current_version);
    console.log('Supported:', data.api_versioning.supported_versions);
  });
```

### Future Versioning

When introducing v2:

1. **Add v2 router** in `main.py`:
   ```python
   v2_router = FastAPI(title="API v2")
   # ... configure v2 endpoints
   app.mount("/api/v2", v2_router)
   ```

2. **Update version_info**:
   ```python
   CURRENT_API_VERSION = "v2"
   SUPPORTED_VERSIONS = ["v1", "v2"]
   ```

3. **Deprecate v1** (optional):
   ```python
   deprecated = ["v1"]
   ```

4. **Frontend update**:
   ```javascript
   export const API_VERSION = "v2";
   ```

### Testing Versioned Endpoints

```bash
# V1 endpoint
curl http://localhost:8000/api/v1/public/games

# Legacy endpoint (maps to v1)
curl http://localhost:8000/api/public/games

# Both should return identical results
```

---

## Benefits Summary

### Integration Tests
- ✅ **Confidence**: Tests real user workflows
- ✅ **Regression Prevention**: Catches breaking changes
- ✅ **Documentation**: Tests serve as usage examples
- ✅ **Faster Debugging**: Pinpoints issues across components

### Coverage Reports
- ✅ **Quality Metrics**: Quantifiable code quality
- ✅ **Missing Coverage**: Identifies untested code paths
- ✅ **CI/CD Integration**: Automated quality gates
- ✅ **Team Accountability**: Coverage trends over time

### API Versioning
- ✅ **Backward Compatibility**: No breaking changes for existing clients
- ✅ **Future-Proof**: Can introduce breaking changes in v2
- ✅ **Clear Communication**: Clients know what version they're using
- ✅ **Gradual Migration**: Clients can upgrade on their schedule

---

## Maintenance

### Integration Tests

- Add new tests when adding features
- Update mocks when BGG API changes
- Review test coverage quarterly

### Coverage Reports

- Monitor coverage trends in CI/CD
- Address low-coverage files
- Update thresholds as code matures

### API Versioning

- Document version differences in CHANGELOG
- Provide migration guides for major versions
- Announce deprecations 6 months in advance

---

## Related Documentation

- [Backend Testing Guide](backend/tests/README.md)
- [Frontend Testing Guide](frontend/README.md)
- [API Documentation](https://library.manaandmeeples.co.nz/docs)
- [Code Review Report](CODE_REVIEW_REPORT.md)

---

## Questions?

For questions or issues:
1. Check the test files for examples
2. Review this documentation
3. Open an issue on GitHub
4. Contact the development team

**Last Updated**: December 2025
**Version**: 1.0.0
