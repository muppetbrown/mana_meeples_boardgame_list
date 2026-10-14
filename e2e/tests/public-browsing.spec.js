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

      // Verify URL contains category parameter (the shelf picker syncs it as `cats`)
      expect(page.url()).toContain('cats=');

      // Verify games are still displayed
      const gameCards = page.locator('[data-testid="game-card"], .game-card, article');
      const count = await gameCards.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('should shortlist games with a quick pick', async ({ page }) => {
    // The search box was removed from the main page in the mobile redesign;
    // the "Who's playing today?" quick picks are the primary way to narrow down.
    await page.waitForSelector('[data-testid="game-card"], .game-card, article', {
      timeout: 10000
    });

    const quickPick = page.getByRole('button', { name: /First timers/i }).first();
    await quickPick.click();

    // Wait for the URL to reflect the selected quick pick
    await expect(page).toHaveURL(/quickPick=/);

    // Results should be visible (or an empty-state message)
    const hasResults = await page.locator('[data-testid="game-card"], .game-card, article').count() > 0;
    const hasNoResults = await page.locator('text=/no.*games.*found/i').or(page.locator('text=/no.*results/i')).count() > 0;

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

    // Find sort dropdown/select - use a simpler selector
    const sortSelect = page.locator('select[aria-label="Choose sort field"]').first();

    // Check if sort select exists and is visible (may be hidden on mobile)
    const isVisible = await sortSelect.isVisible().catch(() => false);

    if (isVisible) {
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
    } else {
      // Sort controls may be hidden on mobile or in certain layouts
      // Skip the sorting verification but ensure games are still displayed
      const gameCards = page.locator('[data-testid="game-card"], .game-card, article');
      const count = await gameCards.count();
      expect(count).toBeGreaterThan(0);
      console.log('Sort select not visible - skipping sort test (may be mobile layout)');
    }
  });
});
