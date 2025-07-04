import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login')
    
    await expect(page.locator('h2')).toContainText('Docker Control Platform')
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toContainText('Sign in')
  })

  test('should login with valid credentials', async ({ page }) => {
    await page.goto('/login')
    
    await page.fill('input[type="email"]', 'admin@localhost.local')
    await page.fill('input[type="password"]', 'changeme123')
    await page.click('button[type="submit"]')
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/')
    await expect(page.locator('main h1')).toContainText('Dashboard')
  })

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login')
    
    await page.fill('input[type="email"]', 'invalid@example.com')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')
    
    // Should show error message
    await expect(page.locator('.bg-red-50')).toBeVisible()
    await expect(page.locator('.text-red-800')).toContainText('Invalid email or password')
  })

  test('should logout successfully', async ({ page }) => {
    // First login
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@localhost.local')
    await page.fill('input[type="password"]', 'changeme123')
    await page.click('button[type="submit"]')
    
    // Wait for dashboard
    await expect(page.locator('main h1')).toContainText('Dashboard')
    
    // Click logout button
    await page.click('button[title="Logout"]')
    
    // Should redirect to login
    await expect(page).toHaveURL('/login')
  })

  test('should protect routes when not authenticated', async ({ page }) => {
    // Try to access protected route
    await page.goto('/')
    
    // Should redirect to login
    await expect(page).toHaveURL('/login')
  })
})