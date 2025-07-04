import { test, expect } from '@playwright/test'

test.describe('Debug', () => {
  test('debug login flow', async ({ page }) => {
    // Enable console logging
    page.on('console', msg => console.log('Browser console:', msg.text()))
    page.on('pageerror', err => console.log('Page error:', err))
    
    await page.goto('/login')
    
    // Take screenshot before login
    await page.screenshot({ path: 'login-page.png' })
    
    await page.fill('input[type="email"]', 'admin@localhost.local')
    await page.fill('input[type="password"]', 'changeme123')
    await page.click('button[type="submit"]')
    
    // Wait a bit and take screenshot
    await page.waitForTimeout(2000)
    await page.screenshot({ path: 'after-login.png' })
    
    // Check URL
    console.log('Current URL:', page.url())
    
    // Check if there's any h1
    const h1Count = await page.locator('h1').count()
    console.log('H1 count:', h1Count)
    
    // Get all h1 text
    if (h1Count > 0) {
      for (let i = 0; i < h1Count; i++) {
        const text = await page.locator('h1').nth(i).textContent()
        console.log(`H1[${i}]:`, text)
      }
    }
    
    // Check for main element
    const mainExists = await page.locator('main').count()
    console.log('Main element exists:', mainExists > 0)
    
    // Get page content
    const bodyText = await page.locator('body').textContent()
    console.log('Body text (first 500 chars):', bodyText?.substring(0, 500))
  })
})