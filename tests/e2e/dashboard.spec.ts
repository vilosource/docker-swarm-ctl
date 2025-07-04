import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@localhost.local')
    await page.fill('input[type="password"]', 'changeme123')
    await page.click('button[type="submit"]')
    await expect(page.locator('main h1')).toContainText('Dashboard')
  })

  test('should display system statistics', async ({ page }) => {
    // Check for stats cards
    await expect(page.locator('text=Total Containers')).toBeVisible()
    await expect(page.locator('text=Running')).toBeVisible()
    await expect(page.locator('text=Stopped')).toBeVisible()
    await expect(page.locator('dt:text("Images")')).toBeVisible()
    
    // Each stat should have a number
    const statValues = page.locator('.text-lg.font-semibold')
    await expect(statValues).toHaveCount(4)
  })

  test('should display system information', async ({ page }) => {
    // Check for system info section
    await expect(page.locator('h3:has-text("System Information")')).toBeVisible()
    
    // Check for specific system details
    await expect(page.locator('text=Docker Version')).toBeVisible()
    await expect(page.locator('text=Operating System')).toBeVisible()
    await expect(page.locator('text=CPU Count')).toBeVisible()
    await expect(page.locator('text=Total Memory')).toBeVisible()
  })

  test('should navigate using sidebar', async ({ page }) => {
    // Click Containers
    await page.click('nav a:has-text("Containers")')
    await expect(page.locator('main h1')).toContainText('Containers')
    
    // Click Images
    await page.click('nav a:has-text("Images")')
    await expect(page.locator('main h1')).toContainText('Images')
    
    // Click Dashboard
    await page.click('nav a:has-text("Dashboard")')
    await expect(page.locator('main h1')).toContainText('Dashboard')
  })

  test('should display user info in sidebar', async ({ page }) => {
    // Check user info in sidebar
    await expect(page.locator('text=admin')).toBeVisible()
    await expect(page.locator('.text-xs.text-gray-400:has-text("admin")')).toBeVisible()
  })
})