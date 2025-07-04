import { test, expect } from '@playwright/test'

test.describe('Container Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@localhost.local')
    await page.fill('input[type="password"]', 'changeme123')
    await page.click('button[type="submit"]')
    await expect(page.locator('main h1')).toContainText('Dashboard')
  })

  test('should display containers page', async ({ page }) => {
    await page.click('text=Containers')
    
    await expect(page.locator('main h1')).toContainText('Containers')
    await expect(page.locator('button:has-text("Create Container")')).toBeVisible()
    await expect(page.locator('input[type="checkbox"]')).toBeVisible()
  })

  test('should create a new container', async ({ page }) => {
    await page.click('text=Containers')
    await page.click('button:has-text("Create Container")')
    
    // Fill create form
    await page.fill('input[placeholder="e.g., nginx:latest"]', 'nginx:alpine')
    await page.fill('input[placeholder="my-container"]', 'test-nginx-' + Date.now())
    
    await page.click('button:has-text("Create")')
    
    // Should close modal and show container in list
    await expect(page.locator('.fixed.inset-0')).not.toBeVisible()
    await expect(page.locator('text=nginx:alpine')).toBeVisible()
  })

  test('should start and stop container', async ({ page }) => {
    await page.click('text=Containers')
    
    // Find a stopped container and start it
    const stoppedContainer = page.locator('li').filter({ hasText: 'exited' }).first()
    if (await stoppedContainer.count() > 0) {
      await stoppedContainer.locator('button:has-text("Start")').click()
      
      // Wait for status to change
      await page.waitForTimeout(2000)
      
      // Should now show Stop button
      await expect(stoppedContainer.locator('button:has-text("Stop")')).toBeVisible()
    }
  })

  test('should toggle show all containers', async ({ page }) => {
    await page.click('text=Containers')
    
    // Get initial count
    const initialCount = await page.locator('li').count()
    
    // Toggle show all
    await page.click('input[type="checkbox"]')
    
    // Wait for update
    await page.waitForTimeout(1000)
    
    // Count might be different
    const newCount = await page.locator('li').count()
    expect(newCount).toBeGreaterThanOrEqual(initialCount)
  })
})