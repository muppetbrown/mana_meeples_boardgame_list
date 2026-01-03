# E2E Tests - Playwright

End-to-end tests for the Mana & Meeples Board Game Library using Playwright.

## Setup

### 1. Install Dependencies

```bash
cd e2e
npm install
```

### 2. Install Playwright Browsers

**Important:** This step requires network access to download browser binaries (~400MB).

```bash
# Install all browsers (Chromium, Firefox, WebKit)
npm run install:browsers

# OR install only Chromium (faster, smaller download)
npm run install:chromium
```

**Network Restrictions:**
If you encounter 403 errors during browser installation, you're in an environment with network restrictions. You'll need to:
- Run the installation from a different network/environment with internet access
- OR use your local machine to install browsers
- OR configure a proxy if your organization requires one

### 3. Verify Installation

Check that Playwright is installed correctly:

```bash
npx playwright --version
```

## Running Tests

```bash
# Run all tests (headless)
npm test

# Run tests with UI mode (interactive)
npm run test:ui

# Run tests in headed mode (see the browser)
npm run test:headed

# Run only Chromium tests
npm run test:chromium

# View test report
npm run report
```

## Test Files

All test files are located in the `tests/` directory:

- `tests/admin-login-management.spec.js` - Admin authentication and session management
- `tests/bgg-import-workflow.spec.js` - BoardGameGeek import functionality
- `tests/game-detail-view.spec.js` - Game details page
- `tests/public-browsing.spec.js` - Public catalogue browsing and filtering

## Configuration

- `playwright.config.js` - Playwright configuration
- Tests run against `http://localhost:5173` (Vite dev server) by default
- The frontend dev server is automatically started before tests run

## Troubleshooting

### Browser Download Fails (403 Error)

This happens in environments with network restrictions. Solutions:
1. Use a different network without restrictions
2. Install on your local machine instead
3. Contact your network administrator about allowing:
   - `cdn.playwright.dev`
   - `playwright.download.prss.microsoft.com`

### Tests Fail to Start

Make sure the frontend dev server is running on port 5173:
```bash
cd ../frontend
npm run dev
```

### Port Already in Use

If port 5173 is already in use, the tests will reuse the existing server automatically.
