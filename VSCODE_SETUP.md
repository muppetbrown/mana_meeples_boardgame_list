# VSCode Setup Guide for Mana & Meeples

This guide helps you set up VSCode for optimal development experience with Python (pytest) and Playwright tests.

## Quick Troubleshooting

**Got an error?** Jump to the solution:

| Error Message | Quick Fix | Section |
|--------------|-----------|---------|
| `command 'python.configureTests' not found` | Install Python extension (`ms-python.python`) | [Python Extension Error](#vscode-python-extension-command-not-found-error) |
| `Cannot redefine property: Symbol($$jest-matchers-object)` | ✅ FIXED - Pull latest changes | [Playwright/Vitest Conflict](#playwright-running-vitest-tests-typeerror-cannot-redefine-property) |
| `describe is not defined` | ✅ FIXED - Pull latest changes | [Playwright/Vitest Conflict](#playwright-running-vitest-tests-typeerror-cannot-redefine-property) |
| Tests don't appear in VSCode | Select Python interpreter + install deps | [Pytest Discovery](#pytest-discovery-fails-with-import-errors) |
| Coverage errors during discovery | ✅ FIXED - `--no-cov` in settings | [Coverage Issues](#coverage-shows-in-terminal-but-not-vscode) |
| Tailwind CSS PostCSS error | ✅ FIXED - Updated to v4 syntax | [Playwright Timeout](#playwright-tests-timeout) |

## Quick Start

The `.vscode` directory has been created locally with optimal settings. Since it's in `.gitignore`, you'll need to keep it locally or share it with your team manually.

## Issues Fixed

### 1. Pytest Discovery Not Working
**Problem**: Tests don't appear in VSCode Test Explorer on startup, require manual "Configure Tests" which errors out.

**Root Causes**:
- Coverage plugin (`pytest-cov`) runs during test discovery, causing failures
- Missing `__init__.py` in `backend/tests/test_scripts/` directory
- No VSCode pytest configuration

**Solution**:
- Created `.vscode/settings.json` with `--no-cov` flag to disable coverage during discovery
- Added missing `__init__.py` file to `test_scripts` directory
- Configured proper test paths and working directory

### 2. Playwright Tailwind CSS Error
**Problem**: Playwright web server fails with PostCSS/Tailwind CSS error:
```
The PostCSS plugin has moved to a separate package...
Error: Timed out waiting 120000ms from config.webServer.
```

**Root Cause**: Project uses Tailwind CSS v4, but configuration used old v3 syntax

**Solution**:
- Updated `frontend/src/index.css` to use `@import "tailwindcss"` (v4 syntax)
- Updated `frontend/postcss.config.cjs` to remove old Tailwind plugin
- Kept `autoprefixer` plugin for browser compatibility

## Files Created

### `.vscode/settings.json`
Configures Python testing with pytest, including:
- Test discovery paths (`backend/tests`)
- Coverage disabled during discovery (`--no-cov`)
- Auto-discovery on file save
- File exclusions for cleaner explorer
- Python and Playwright settings

### `.vscode/launch.json`
Debug configurations for:
- Debug current test file
- Debug all tests
- Debug specific test (with prompt)
- Debug FastAPI backend

### `.vscode/extensions.json`
Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Playwright (ms-playwright.playwright)
- ESLint, Prettier, GitLens, etc.

## Using the Test Explorer

### Pytest Tests (Python Backend)

1. **Initial Setup**:
   - Open VSCode in the project root
   - Install recommended extensions (VSCode will prompt)
   - Select Python interpreter (look for your virtual environment)
   - Test Explorer should auto-discover tests

2. **If Tests Don't Appear**:
   - Open Command Palette (`Cmd/Ctrl+Shift+P`)
   - Run `Python: Configure Tests`
   - Select `pytest`
   - Select `backend/tests` as the directory
   - Tests should now appear in Test Explorer

3. **Running Tests**:
   - Click the beaker icon in the sidebar
   - Click play button next to any test/folder
   - Or use debug icon to debug with breakpoints

4. **Running from Terminal** (with coverage):
   ```bash
   cd backend
   pytest -v
   # Coverage is enabled by default in pytest.ini
   ```

### Playwright Tests (E2E Frontend)

1. **Initial Setup**:
   - Install Playwright extension
   - Playwright tests will appear in Test Explorer

2. **Running Tests**:
   - Tests are in `e2e/tests/` directory
   - Click play button in Test Explorer
   - Or run from terminal:
     ```bash
     cd frontend
     npm run test:e2e
     npm run test:e2e:ui  # Interactive UI mode
     ```

## Troubleshooting

### VSCode Python Extension "Command Not Found" Error

**Problem**: When trying to configure tests, you see:
```
Command 'Python: Configure Tests' resulted in an error
command 'python.configureTests' not found
```

**Cause**: Python extension isn't installed or properly activated

**Solutions**:
1. **Install Python Extension**:
   - Open Extensions panel (`Ctrl+Shift+X`)
   - Search for "Python" by Microsoft (`ms-python.python`)
   - Click Install
   - Also install "Pylance" extension for better IntelliSense

2. **Reload VSCode**:
   - Press `Ctrl+Shift+P`
   - Type "Developer: Reload Window"
   - Press Enter

3. **Select Python Interpreter**:
   - Press `Ctrl+Shift+P`
   - Type "Python: Select Interpreter"
   - Choose your Python installation or virtual environment
   - For virtual env, look for paths like `./backend/venv/bin/python`

4. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

5. **Verify Extension is Active**:
   - Look for Python version in bottom-left status bar
   - Click it to change interpreter if needed

### Playwright Running Vitest Tests (TypeError: Cannot redefine property)

**Problem**: Running `npm run test:e2e` shows errors like:
```
TypeError: Cannot redefine property: Symbol($$jest-matchers-object)
ReferenceError: describe is not defined
```

**Cause**: Playwright is trying to run Vitest test files (`.test.jsx`) instead of only Playwright tests (`.spec.js`)

**Solution**: ✅ FIXED - Updated `playwright.config.ts` and `e2e/playwright.config.js` to:
- Only match `.spec.{js,ts}` files
- Explicitly ignore `.test.{js,jsx,ts,tsx}` files

**Verify Fix**:
```bash
cd frontend
npm run test:e2e  # Should only run 4 .spec.js files from e2e/tests/
```

**Expected Output**:
- Should find and run 4 test files:
  - `admin-login-management.spec.js`
  - `bgg-import-workflow.spec.js`
  - `game-detail-view.spec.js`
  - `public-browsing.spec.js`
- Should NOT show any errors about Vitest or `describe is not defined`

### Pytest Discovery Fails with Import Errors

**Problem**: VSCode shows "Test Discovery Error" with import failures

**Solutions**:
1. Ensure you're in the project root directory
2. Check Python interpreter is correctly selected
3. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
4. Check for missing `__init__.py` files in test directories

### Tests Are "Muddled Up" or Duplicated

**Problem**: Tests appear multiple times or in wrong hierarchy

**Cause**: Multiple pytest.ini files or conflicting configurations

**Solution**:
- Ensure only one `pytest.ini` exists in `backend/` directory
- Clear pytest cache: `rm -rf backend/.pytest_cache`
- Reload window: `Cmd/Ctrl+Shift+P` → "Developer: Reload Window"

### Playwright Tests Timeout

**Problem**: Web server doesn't start, timeout error

**Cause**: Tailwind CSS configuration issue (should be fixed now)

**Verify Fix**:
```bash
cd frontend
npm run dev  # Should start without errors
```

### Coverage Shows in Terminal But Not VSCode

This is intentional! Coverage is:
- **Disabled** in VSCode Test Explorer (`--no-cov` flag) to speed up discovery
- **Enabled** when running `pytest` from terminal (see `pytest.ini`)

To view coverage from terminal:
```bash
cd backend
pytest --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

## Configuration Details

### pytest.ini Settings
- **testpaths**: `tests` (searches in backend/tests/)
- **python_files**: `test_*.py`
- **Coverage**: Enabled with 35% minimum threshold
- **Markers**: `slow`, `integration`, `unit`, `api`

### VSCode Pytest Args
- `backend/tests`: Test directory
- `-v`: Verbose output
- `-l`: Show local variables in tracebacks
- `--disable-warnings`: Reduce noise
- `--tb=short`: Short traceback format
- `--no-cov`: Disable coverage (discovery only)
- `-o addopts=`: Override pytest.ini addopts (prevents double coverage)

## Best Practices

1. **Keep .vscode local**: Don't commit to git (it's in .gitignore)
2. **Share this guide**: Help teammates set up their environment
3. **Run coverage in CI/CD**: Use `pytest` without `--no-cov` in pipelines
4. **Use debug configs**: Set breakpoints and use F5 to debug tests
5. **Keep tests organized**: Maintain `__init__.py` in all test directories

## Additional Resources

- [VSCode Python Testing](https://code.visualstudio.com/docs/python/testing)
- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright VSCode Extension](https://playwright.dev/docs/getting-started-vscode)
- [Tailwind CSS v4 Migration](https://tailwindcss.com/docs/upgrade-guide)

## Need Help?

If tests still don't appear:
1. Check the Output panel (`View` → `Output`)
2. Select "Python Test Log" from dropdown
3. Look for error messages
4. Verify Python interpreter path
5. Try reloading VSCode window

## Summary of Changes

### Files Modified (Committed)
- ✅ `frontend/src/index.css` - Updated to Tailwind v4 syntax (`@import "tailwindcss"`)
- ✅ `frontend/postcss.config.cjs` - Removed old Tailwind plugin
- ✅ `backend/tests/test_scripts/__init__.py` - Added missing init file for pytest discovery
- ✅ `playwright.config.ts` - Added `testMatch` and `testIgnore` to prevent Vitest conflicts
- ✅ `e2e/playwright.config.js` - Added `testMatch` and `testIgnore` for consistency
- ✅ `VSCODE_SETUP.md` - Comprehensive troubleshooting guide

### Files Created (Local Only - Not in Git)
- 📝 `.vscode/settings.json` - Test discovery, Python config, comments for troubleshooting
- 📝 `.vscode/launch.json` - Debug configurations for tests and FastAPI
- 📝 `.vscode/extensions.json` - Recommended extensions list

### Key Configuration Settings
- **Pytest Args**: `--no-cov` and `-o addopts=` to disable coverage during discovery
- **Playwright Test Match**: `**/*.spec.{js,ts}` only (excludes `.test.{js,jsx}`)
- **Test Directories**:
  - Backend: `backend/tests/`
  - E2E: `e2e/tests/` (Playwright `.spec.js` files)
  - Frontend: `frontend/src/**/__tests__/` (Vitest `.test.jsx` files)

---

**Last Updated**: 2026-01-06
**Tailwind Version**: 4.1.18
**Pytest Version**: 9.0.2
**Playwright Version**: 1.57.0
**VSCode Extensions**: Python (ms-python.python), Pylance, Playwright
