#!/usr/bin/env python3
"""
Debug the services page
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_services_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("🌐 Navigating to application...")
            await page.goto("http://localhost")
            
            # Login
            await page.wait_for_selector('input[type="email"]', timeout=10000)
            await page.fill('input[type="email"]', 'admin@localhost.local')
            await page.fill('input[type="password"]', 'changeme123')
            await page.click('button[type="submit"]')
            
            # Wait for dashboard
            await page.wait_for_selector('.page-title', timeout=10000)
            print("✅ Successfully logged in")
            
            # Navigate to services
            await page.goto("http://localhost/hosts/e4e1086d-4533-40cd-8788-069337d04337/services")
            await page.wait_for_timeout(3000)
            
            # Take screenshot
            await page.screenshot(path="services_page.png")
            print("📸 Services page screenshot saved")
            
            # Get page title
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Check if there are any error messages
            error_messages = await page.query_selector_all('.alert-danger')
            if error_messages:
                for i, error in enumerate(error_messages):
                    text = await error.inner_text()
                    print(f"❌ Error #{i+1}: {text}")
            
            # Check if there's a loading indicator
            loading = await page.query_selector('.spinner-border')
            if loading:
                print("⏳ Page is still loading...")
            
            # Look for services table
            table = await page.query_selector('table')
            if table:
                print("📋 Found services table")
                
                # Get table content
                rows = await table.query_selector_all('tr')
                print(f"📊 Table has {len(rows)} rows")
                
                for i, row in enumerate(rows[:5]):  # Show first 5 rows
                    text = await row.inner_text()
                    print(f"  Row #{i+1}: {text}")
            else:
                print("❌ No services table found")
                
            # Look for any service-related elements
            service_elements = await page.query_selector_all('[href*="service"]')
            print(f"🔗 Found {len(service_elements)} service-related links")
            
            # Look for create service button
            create_button = await page.query_selector('button:has-text("Create Service")')
            if create_button:
                print("➕ Create Service button found")
            
            # Check page content for 'test-logger'
            content = await page.content()
            if 'test-logger' in content:
                print("✅ test-logger found in page content")
            else:
                print("❌ test-logger not found in page content")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path="services_error.png")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_services_page())