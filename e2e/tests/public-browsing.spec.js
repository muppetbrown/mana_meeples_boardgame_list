const { test, expect } = require('@playwright/test');

/**
 * E2E Tests for Public Browsing and Filtering
 * Sprint 11: Advanced Testing
 *
 * Critical User Journey: Public users can browse and filter the game catalogue
 */

test.describe('Public Browsing and Filtering', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the home page before each test
    await page.goto('/');
  });

  test('should load the public catalogue with games', async ({ page }) => {
    // Wait for games to load
    await page.waitForSelector('[data-testid="game-card"], .game-card, article', {
      timeout: 10000
    });

    // Verify page title or heading
    await expect(page.locator('h1, h2').first()).toBeVisible();

    // Count visible game cards (should be at least 1)
    const gameCards = page.locator('[data-testid="game-card"], .game-card, article');
    const count = await gameCards.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should filter games by category', async ({ page }) => {
    // Wait for initial load
    await page.waitForSelector('[data-testid="game-card"], .game-card, article');

    // Click on a category filter button
    const categoryButton = page.locator('button:has-text("Gateway Strategy"), button:has-text("Co-op"), button:has-text("GATEWAY_STRATEGY")').first();

    if (await categoryButton.count() > 0) {
      await categoryButton.click();

      // Wait for filtered results
      await page.waitForTimeout(500);

      // Verify URL contains category parameter
      expect(page.url()).toContain('category=');

      // Verify games are still displayed
      const gameCards = page.locator('[data-testid="game-card"], .game-card, article');
      const count = await gameCards.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('should search for games by title', async ({ page }) => {
    // Find search input
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"], input[name="search"]').first();

    await searchInput.fill('catan');

    // Wait for debounced search
    await page.waitForTimeout(300);

    // Verify URL contains search parameter
    expect(page.url()).toContain('q=');

    // Results should be visible (or "no results" message)
    const hasResults = await page.locator('[data-testid="game-card"], .game-card, article').count() > 0;
    const hasNoResults = await page.locator('text=/no.*games.*found/i, text=/no.*results/i').count() > 0;

    expect(hasResults || hasNoResults).toBeTruthy();
  });

  test('should filter by New Zealand designers', async ({ page }) => {
    // Look for NZ designer filter checkbox or button
    const nzFilter = page.locator('input[type="checkbox"]:near(:text("New Zealand")), button:has-text("NZ Designer"), label:has-text("New Zealand")').first();

    if (await nzFilter.count() > 0) {
      await nzFilter.click();

      // Wait for filter to apply
      await page.waitForTimeout(500);

      // Verify URL contains nz_designer parameter
      expect(page.url()).toContain('nz_designer=true');
    }
  });

  test('should sort games by different criteria', async ({ page }) => {
    // Wait for initial load
    await page.waitForSelector('[data-testid="game-card"], .game-card, article');

    // Find sort dropdown/select
    const sortSelect = page.locator('select[name="sort"], select:has(option:text-matches("Title|Year|Rating", "i"))').first();

    if (await sortSelect.count() > 0) {
      // Select "Year" option by value
      await sortSelect.selectOption('year');

      // Wait for re-sort
      await page.waitForTimeout(500);

      // Verify URL contains sort parameter
      expect(page.url()).toContain('sort=');

      // Verify games are still displayed
      const gameCards = page.locator('[data-testid="game-card"], .game-card, article');
      const count = await gameCards.count();
      expect(count).toBeGreaterThan(0);
    }
  });
});
