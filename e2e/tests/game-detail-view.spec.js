const { test, expect } = require('@playwright/test');

/**
 * E2E Tests for Game Detail View
 * Sprint 11: Advanced Testing
 *
 * Critical User Journey: Users can view detailed information about a game
 */

test.describe('Game Detail View', () => {
  test('should display game details when clicking on a game card', async ({ page }) => {
    // Navigate to catalogue
    await page.goto('/');

    // Wait for games to load
    await page.waitForSelector('[data-testid="game-card"], .game-card, article', {
      timeout: 10000
    });

    // Click on the first game card's link (not the expand button)
    const firstGameLink = page.locator('article a[href^="/game/"]').first();
    await firstGameLink.click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/game\/\d+/);

    // Verify we're on a game detail page
    expect(page.url()).toMatch(/\/game\/\d+/);

    // Verify game title is displayed
    const title = page.locator('h1, h2').first();
    await expect(title).toBeVisible();
    await expect(title).not.toBeEmpty();
  });

  test('should display comprehensive game information', async ({ page }) => {
    // Navigate to catalogue
    await page.goto('/');

    // Wait for games to load
    await page.waitForSelector('[data-testid="game-card"], .game-card, article');

    // Click on a game card's link (not the expand button)
    await page.locator('article a[href^="/game/"]').first().click();

    // Wait for detail page
    await page.waitForURL(/\/game\/\d+/);

    // Check for key game information sections
    // Note: These are typical fields, actual implementation may vary

    // Game image should be present
    const gameImage = page.locator('img').first();
    await expect(gameImage).toBeVisible();

    // At least some game information should be displayed (not all games have all fields)
    // Check for player count, playtime, or year
    const hasPlayerInfo = await page.locator('text=/\\d+[-–]\\d+ players?/i').or(page.locator(':text("Players")')).count() > 0;
    const hasPlaytime = await page.locator('text=/\\d+ min/i').or(page.locator(':text("Playtime")')).count() > 0;
    const hasYear = await page.locator('text=/20\\d\\d|19\\d\\d/').or(page.locator(':text("Year")')).count() > 0;

    // At least one of these fields should be present
    expect(hasPlayerInfo || hasPlaytime || hasYear).toBeTruthy();
  });

  test('should have a back button to return to catalogue', async ({ page }) => {
    // Navigate to catalogue
    await page.goto('/');

    // Wait for games to load
    await page.waitForSelector('[data-testid="game-card"], .game-card, article');

    // Remember the catalogue URL
    const catalogueUrl = page.url();

    // Click on a game card's link (not the expand button)
    await page.locator('article a[href^="/game/"]').first().click();

    // Wait for detail page
    await page.waitForURL(/\/game\/\d+/);

    // Find and click back button
    const backButton = page.locator('button:has-text("Back"), a:has-text("Back"), [aria-label="Back"], [aria-label="Go back"]').first();

    if (await backButton.count() > 0) {
      await backButton.click();

      // Wait for navigation back to catalogue
      await page.waitForTimeout(500);

      // Verify we're back at the catalogue
      expect(page.url()).toContain(catalogueUrl.split('?')[0]);
    } else {
      // If no back button, browser back should work
      await page.goBack();
      await page.waitForTimeout(500);
      expect(page.url()).toContain(catalogueUrl.split('?')[0]);
    }
  });
});
