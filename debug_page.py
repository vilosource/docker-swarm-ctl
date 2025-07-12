#!/usr/bin/env python3
"""
Debug what's on the page
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("🌐 Navigating to application...")
            await page.goto("http://localhost")
            
            # Wait a bit for page to load
            await page.wait_for_timeout(3000)
            
            # Get page title
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Get page content
            content = await page.content()
            print(f"📝 Page content length: {len(content)}")
            
            # Look for common elements
            h1_elements = await page.query_selector_all('h1')
            if h1_elements:
                for i, h1 in enumerate(h1_elements):
                    text = await h1.inner_text()
                    print(f"📌 H1 #{i+1}: {text}")
            
            # Look for forms
            forms = await page.query_selector_all('form')
            print(f"📋 Found {len(forms)} forms")
            
            # Look for input fields
            inputs = await page.query_selector_all('input')
            print(f"🔤 Found {len(inputs)} input fields")
            for i, input_elem in enumerate(inputs):
                name = await input_elem.get_attribute('name')
                type_attr = await input_elem.get_attribute('type')
                print(f"  Input #{i+1}: name='{name}', type='{type_attr}'")
            
            # Look for buttons
            buttons = await page.query_selector_all('button')
            print(f"🔘 Found {len(buttons)} buttons")
            
            # Take a screenshot
            await page.screenshot(path="debug_page.png")
            print("📸 Screenshot saved as debug_page.png")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())