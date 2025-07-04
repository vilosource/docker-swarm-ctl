import { test, expect } from '@playwright/test'

test.describe('Profile Page', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@localhost.local')
    await page.fill('input[type="password"]', 'changeme123')
    await page.click('button[type="submit"]')
    await expect(page.locator('main h1')).toContainText('Dashboard')
  })

  test('should navigate to profile page', async ({ page }) => {
    // Click on user avatar/name in sidebar
    await page.click('.text-gray-300.hover\\:text-white')
    
    await expect(page).toHaveURL('/profile')
    await expect(page.locator('main h1')).toContainText('Profile')
  })

  test('should display user information', async ({ page }) => {
    await page.goto('/profile')
    
    // Check user details
    await expect(page.locator('text=System Administrator')).toBeVisible()
    await expect(page.locator('text=admin@localhost.local')).toBeVisible()
    await expect(page.locator('text=admin').nth(1)).toBeVisible() // username
    
    // Check role badge
    await expect(page.locator('.bg-purple-100:has-text("admin")')).toBeVisible()
    
    // Check status
    await expect(page.locator('.bg-green-100:has-text("Active")')).toBeVisible()
  })

  test('should display role permissions', async ({ page }) => {
    await page.goto('/profile')
    
    // Check permissions section
    await expect(page.locator('h3:has-text("Role Permissions")')).toBeVisible()
    await expect(page.locator('text=As a admin, you have the following permissions:')).toBeVisible()
    
    // Admin permissions
    await expect(page.locator('text=Full system access')).toBeVisible()
    await expect(page.locator('text=User management')).toBeVisible()
    await expect(page.locator('text=System configuration')).toBeVisible()
    await expect(page.locator('text=All container and image operations')).toBeVisible()
  })

  test('should display timestamps', async ({ page }) => {
    await page.goto('/profile')
    
    // Check for created and updated timestamps
    await expect(page.locator('dt:has-text("Account created")')).toBeVisible()
    await expect(page.locator('dt:has-text("Last updated")')).toBeVisible()
    
    // Should have valid date formats
    const createdDate = page.locator('dd').filter({ hasText: /\d{1,2}\/\d{1,2}\/\d{4}/ }).first()
    await expect(createdDate).toBeVisible()
  })
})