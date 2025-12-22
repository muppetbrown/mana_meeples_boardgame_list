import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Admin Login and Game Management
 * Sprint 11: Advanced Testing
 *
 * Critical User Journey: Admins can log in and manage games
 */

// Use test admin token from environment or a test-specific token
const TEST_ADMIN_TOKEN = process.env.TEST_ADMIN_TOKEN || 'test_admin_token_replace_me';

test.describe('Admin Login and Management', () => {
  test('should navigate to admin login page', async ({ page }) => {
    // Navigate to admin login
    await page.goto('/staff/login');

    // Verify we're on the login page
    expect(page.url()).toContain('/staff/login');

    // Verify login form is present
    const loginForm = page.locator('form, input[type="password"], input[name="token"]').first();
    await expect(loginForm).toBeVisible();

    // Verify there's a submit button
    const submitButton = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")').first();
    await expect(submitButton).toBeVisible();
  });

  test('should reject invalid login credentials', async ({ page }) => {
    // Navigate to admin login
    await page.goto('/staff/login');

    // Enter invalid token
    const tokenInput = page.locator('input[type="password"], input[name="token"], input[name="password"]').first();
    await tokenInput.fill('invalid_token_12345');

    // Submit form
    const submitButton = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")').first();
    await submitButton.click();

    // Wait for error message
    await page.waitForTimeout(1000);

    // Verify error message is displayed
    const errorMessage = await page.locator('text=/invalid|incorrect|failed/i, [role="alert"]').count();
    expect(errorMessage).toBeGreaterThan(0);

    // Verify we're still on login page
    expect(page.url()).toContain('/staff/login');
  });

  test('should successfully log in with valid credentials', async ({ page }) => {
    // Skip this test if no test admin token is provided
    if (TEST_ADMIN_TOKEN === 'test_admin_token_replace_me') {
      test.skip();
      return;
    }

    // Navigate to admin login
    await page.goto('/staff/login');

    // Enter valid token
    const tokenInput = page.locator('input[type="password"], input[name="token"], input[name="password"]').first();
    await tokenInput.fill(TEST_ADMIN_TOKEN);

    // Submit form
    const submitButton = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")').first();
    await submitButton.click();

    // Wait for navigation
    await page.waitForTimeout(2000);

    // Verify we're redirected to staff/admin area
    expect(page.url()).toMatch(/\/staff(?!\/login)/);

    // Verify admin UI elements are present
    const hasAdminContent = await page.locator('text=/manage|library|games|admin/i').count() > 0;
    expect(hasAdminContent).toBeTruthy();
  });

  test('should access game management interface after login', async ({ page }) => {
    // Skip this test if no test admin token is provided
    if (TEST_ADMIN_TOKEN === 'test_admin_token_replace_me') {
      test.skip();
      return;
    }

    // Log in
    await page.goto('/staff/login');
    const tokenInput = page.locator('input[type="password"], input[name="token"], input[name="password"]').first();
    await tokenInput.fill(TEST_ADMIN_TOKEN);
    const submitButton = page.locator('button[type="submit"]').first();
    await submitButton.click();

    // Wait for navigation
    await page.waitForTimeout(2000);

    // Look for "Manage Library" or similar link
    const manageLink = page.locator('a:has-text("Manage Library"), a:has-text("Games"), button:has-text("Manage")').first();

    if (await manageLink.count() > 0) {
      await manageLink.click();
      await page.waitForTimeout(1000);

      // Verify we can see game management interface
      const hasGameList = await page.locator('[data-testid="game-list"], table, .game-card').count() > 0;
      expect(hasGameList).toBeTruthy();
    }
  });
});
