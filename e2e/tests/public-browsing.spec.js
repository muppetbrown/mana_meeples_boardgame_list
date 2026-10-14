const { test, expect } = require('@playwright/test');

/**
 * E2E Tests for Public Browsing and Filtering
 * Sprint 11: Advanced Testing
 *
 * Critical User Journey: Public users can browse and filter the game catalogue
 */

const API_BASE = process.env.API_BASE || 'http://localhost:8000';

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

  test('should list games alphabetically by default', async ({ page }) => {
    // The redesigned catalogue has no sort control; it always lists A-Z by title.
    await page.waitForSelector('article h3', { timeout: 10000 });

    const titles = await page.locator('article h3').allInnerTexts();
    expect(titles.length).toBeGreaterThan(1);

    const sorted = [...titles].sort((a, b) => a.localeCompare(b));
    expect(titles).toEqual(sorted);
  });

  test('should filter by New Zealand designers', async ({ request }) => {
    // There is no NZ designer control on the public page, so verify the public
    // API filter that backs it (the seed includes one NZ-designer fixture game).
    const all = await (await request.get(`${API_BASE}/api/public/games?page_size=50`)).json();
    const res = await request.get(`${API_BASE}/api/public/games?nz_designer=true&page_size=50`);
    expect(res.ok()).toBeTruthy();
    const nz = await res.json();

    expect(nz.total).toBeGreaterThan(0);
    expect(nz.total).toBeLessThan(all.total);
    expect(nz.items.every((game) => game.nz_designer === true)).toBeTruthy();
    expect(nz.items.map((game) => game.title)).toContain('Kiwi Test Game');
  });

  test('should sort games by different criteria', async ({ request }) => {
    // Sorting is not exposed in the public UI; verify the API sort options.
    const years = async (sort) => {
      const res = await request.get(`${API_BASE}/api/public/games?sort=${sort}&page_size=50`);
      expect(res.ok()).toBeTruthy();
      return (await res.json()).items.map((game) => game.year);
    };

    const newestFirst = await years('year_desc');
    const oldestFirst = await years('year_asc');

    expect(newestFirst.length).toBeGreaterThan(1);
    expect(newestFirst).toEqual([...newestFirst].sort((a, b) => b - a));
    expect(oldestFirst).toEqual([...oldestFirst].sort((a, b) => a - b));
    expect(newestFirst[0]).not.toEqual(oldestFirst[0]);
  });
});
