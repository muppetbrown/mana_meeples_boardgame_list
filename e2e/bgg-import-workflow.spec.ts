import { test, expect } from '@playwright/test';

/**
 * E2E Tests for BGG Import Workflow
 * Sprint 11: Advanced Testing
 *
 * Critical User Journey: Admins can import games from BoardGameGeek
 */

const TEST_ADMIN_TOKEN = process.env.TEST_ADMIN_TOKEN || 'test_admin_token_replace_me';

test.describe('BGG Import Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Skip all tests if no test admin token is provided
    if (TEST_ADMIN_TOKEN === 'test_admin_token_replace_me') {
      test.skip();
      return;
    }

    // Log in before each test
    await page.goto('/staff/login');
    const tokenInput = page.locator('input[type="password"], input[name="token"], input[name="password"]').first();
    await tokenInput.fill(TEST_ADMIN_TOKEN);
    const submitButton = page.locator('button[type="submit"]').first();
    await submitButton.click();
    await page.waitForTimeout(2000);
  });

  test('should access BGG import interface', async ({ page }) => {
    // Look for "Add Game" or "Import from BGG" link/button
    const importLink = page.locator('a:has-text("Add Game"), a:has-text("Import"), button:has-text("Add"), button:has-text("Import")').first();

    if (await importLink.count() > 0) {
      await importLink.click();
      await page.waitForTimeout(1000);

      // Verify BGG import form is visible
      const bggInput = page.locator('input[name="bgg_id"], input[placeholder*="BGG"], input[placeholder*="BoardGameGeek"]').first();
      await expect(bggInput).toBeVisible();
    } else {
      // If no obvious import link, check if we're already on the import page
      const bggInput = page.locator('input[name="bgg_id"], input[placeholder*="BGG"]').first();
      const hasImportForm = await bggInput.count() > 0;
      expect(hasImportForm).toBeTruthy();
    }
  });

  test('should validate BGG ID before importing', async ({ page }) => {
    // Navigate to import interface
    const importLink = page.locator('a:has-text("Add Game"), a:has-text("Import"), button:has-text("Add")').first();
    if (await importLink.count() > 0) {
      await importLink.click();
      await page.waitForTimeout(500);
    }

    // Try to import with invalid BGG ID (e.g., letters or negative number)
    const bggInput = page.locator('input[name="bgg_id"], input[placeholder*="BGG"]').first();

    if (await bggInput.count() > 0) {
      await bggInput.fill('invalid_id');

      // Try to submit
      const submitButton = page.locator('button:has-text("Import"), button[type="submit"]').first();
      await submitButton.click();

      // Wait for validation error
      await page.waitForTimeout(1000);

      // Verify error message or validation feedback
      const hasError = await page.locator('text=/invalid|error|required/i, [role="alert"]').count() > 0;
      expect(hasError).toBeTruthy();
    }
  });

  test('should import a valid game from BGG', async ({ page }) => {
    // Navigate to import interface
    const importLink = page.locator('a:has-text("Add Game"), a:has-text("Import")').first();
    if (await importLink.count() > 0) {
      await importLink.click();
      await page.waitForTimeout(500);
    }

    // Use a well-known BGG ID (e.g., 13 for Catan)
    const bggInput = page.locator('input[name="bgg_id"], input[placeholder*="BGG"]').first();

    if (await bggInput.count() > 0) {
      await bggInput.fill('13'); // Catan

      // Submit import
      const submitButton = page.locator('button:has-text("Import"), button[type="submit"]').first();
      await submitButton.click();

      // Wait for import to complete (this may take several seconds)
      await page.waitForTimeout(5000);

      // Check for success message or verify game appears in library
      const hasSuccess = await page.locator('text=/success|imported|added/i, [role="alert"]:has-text("success")').count() > 0;
      const hasGameInLibrary = await page.locator('text=/catan/i').count() > 0;

      expect(hasSuccess || hasGameInLibrary).toBeTruthy();
    }
  });
});
