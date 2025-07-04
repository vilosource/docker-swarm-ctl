import { test, expect } from '@playwright/test'

test.describe('Image Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@localhost.local')
    await page.fill('input[type="password"]', 'changeme123')
    await page.click('button[type="submit"]')
    await expect(page.locator('main h1')).toContainText('Dashboard')
  })

  test('should display images page', async ({ page }) => {
    await page.click('text=Images')
    
    await expect(page.locator('main h1')).toContainText('Images')
    await expect(page.locator('button:has-text("Pull Image")')).toBeVisible()
  })

  test('should open pull image modal', async ({ page }) => {
    await page.click('text=Images')
    await page.click('button:has-text("Pull Image")')
    
    // Modal should be visible
    await expect(page.locator('.fixed.inset-0')).toBeVisible()
    await expect(page.locator('h2')).toContainText('Pull Image')
    await expect(page.locator('input[placeholder="nginx"]')).toBeVisible()
    await expect(page.locator('input[placeholder="latest"]')).toBeVisible()
  })

  test('should pull an image', async ({ page }) => {
    await page.click('text=Images')
    await page.click('button:has-text("Pull Image")')
    
    // Fill form
    await page.fill('input[placeholder="nginx"]', 'alpine')
    await page.fill('input[placeholder="latest"]', 'latest')
    
    await page.click('button:has-text("Pull")')
    
    // Should show success message
    await expect(page.locator('.bg-green-50')).toBeVisible()
    await expect(page.locator('.text-green-800')).toContainText('Image pull started')
  })

  test('should display image details', async ({ page }) => {
    await page.click('text=Images')
    
    // Check if images are displayed with proper information
    const imageRow = page.locator('li').first()
    await expect(imageRow).toBeVisible()
    
    // Should show size and creation date
    await expect(imageRow.locator('text=/Size:/')).toBeVisible()
    await expect(imageRow.locator('text=/Created:/')).toBeVisible()
  })
})