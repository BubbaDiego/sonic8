import { test, expect } from '@playwright/test';

test.describe('basic routes', () => {
  test('root redirects to dashboard and loads', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBe(200);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/dashboard\/sonic/);
  });

  test('dashboard page shows elements', async ({ page }) => {
    const response = await page.goto('/dashboard/sonic');
    expect(response?.status()).toBe(200);
    await expect(page.getByRole('heading', { name: /total value/i })).toBeVisible();
  });

  test('reload preserves page', async ({ page }) => {
    await page.goto('/dashboard/sonic');
    await page.reload();
    await expect(page).toHaveURL(/dashboard\/sonic/);
  });
});
