#!/usr/bin/env python3
"""
Test the service logs UI using headless Playwright
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def test_service_logs_ui():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("🌐 Navigating to application...")
            await page.goto("http://localhost")
            
            # Wait for login page to load
            await page.wait_for_selector('input[type="email"]', timeout=10000)
            print("✅ Login page loaded")
            
            # Login
            print("🔑 Logging in...")
            await page.fill('input[type="email"]', 'admin@localhost.local')
            await page.fill('input[type="password"]', 'changeme123')
            await page.click('button[type="submit"]')
            
            # Wait for dashboard to load
            await page.wait_for_selector('.page-title', timeout=10000)
            print("✅ Successfully logged in")
            
            # Navigate to Services
            print("📋 Navigating to Services...")
            
            # Try to find the service via different navigation paths
            try:
                # Method 1: Try direct navigation to services
                await page.goto("http://localhost/hosts/e4e1086d-4533-40cd-8788-069337d04337/services")
                await page.wait_for_selector('.page-title', timeout=5000)
                print("✅ Navigated to Services page")
            except:
                # Method 2: Try navigation through sidebar
                print("🔍 Trying sidebar navigation...")
                
                # Look for Docker Hosts section
                docker_hosts = await page.query_selector_all('li.menu-title')
                for title in docker_hosts:
                    text = await title.inner_text()
                    if 'Docker Hosts' in text:
                        print("📁 Found Docker Hosts section")
                        break
                
                # Look for a host with services
                services_links = await page.query_selector_all('a[href*="/services"]')
                if services_links:
                    await services_links[0].click()
                    await page.wait_for_selector('.page-title', timeout=5000)
                    print("✅ Navigated to Services page via sidebar")
                else:
                    print("❌ No services links found in sidebar")
                    return
            
            # Check if we have the test-logger service
            print("🔍 Looking for test-logger service...")
            
            # Wait for services table to load
            await page.wait_for_selector('table', timeout=10000)
            
            # Wait for loading to complete
            print("⏳ Waiting for services to load...")
            await page.wait_for_timeout(5000)
            
            # Wait for loading spinners to disappear
            try:
                await page.wait_for_selector('.spinner-border', state='detached', timeout=10000)
            except:
                print("⚠️  Loading spinner still present, continuing anyway")
            
            # Look for test-logger service in different ways
            test_logger_link = None
            
            # Method 1: Look for clickable service name
            service_links = await page.query_selector_all('a[href*="/services/"]')
            print(f"🔗 Found {len(service_links)} service links")
            
            for link in service_links:
                text = await link.inner_text()
                if 'test-logger' in text:
                    test_logger_link = link
                    break
            
            # Method 2: Look for clickable elements containing 'test-logger'
            if not test_logger_link:
                all_links = await page.query_selector_all('a')
                for link in all_links:
                    text = await link.inner_text()
                    if 'test-logger' in text:
                        test_logger_link = link
                        break
            
            # Method 3: Look for view details button in the same row as test-logger
            if not test_logger_link:
                rows = await page.query_selector_all('tr')
                for row in rows:
                    text = await row.inner_text()
                    if 'test-logger' in text:
                        # Look for view details button in this row
                        view_button = await row.query_selector('button:has-text("View"), .btn-primary')
                        if view_button:
                            test_logger_link = view_button
                            break
            
            if not test_logger_link:
                print("❌ test-logger service not found")
                
                # Try to find any service
                if service_links:
                    print(f"📋 Found {len(service_links)} service(s), using the first one")
                    test_logger_link = service_links[0]
                else:
                    print("❌ No services found at all")
                    
                    # Take screenshot for debugging
                    await page.screenshot(path="no_services_found.png")
                    print("📸 Screenshot saved as no_services_found.png")
                    return
            
            # Click on the service
            print("🖱️  Clicking on service...")
            await test_logger_link.click()
            
            # Wait for service detail page to load
            await page.wait_for_selector('.page-title', timeout=10000)
            print("✅ Service detail page loaded")
            
            # Look for the Logs tab
            print("🔍 Looking for Logs tab...")
            
            # Wait for tabs to load
            await page.wait_for_selector('.nav-tabs', timeout=5000)
            
            # Find and click the Logs tab
            logs_tab = await page.query_selector('a[href="#"]:has-text("Logs")')
            if not logs_tab:
                # Try alternative selectors
                logs_tab = await page.query_selector('.nav-link:has-text("Logs")')
            
            if logs_tab:
                print("📋 Found Logs tab, clicking...")
                await logs_tab.click()
                
                # Wait for logs viewer to load
                await page.wait_for_timeout(2000)
                
                # Check if the terminal-style log viewer is present
                log_viewer = await page.query_selector('.bg-black, .terminal, [style*="background"]')
                if log_viewer:
                    print("🎉 SUCCESS! Terminal-style log viewer is loaded")
                    
                    # Check for connection status
                    connection_status = await page.query_selector('.w-2.h-2.rounded-full')
                    if connection_status:
                        print("✅ Connection status indicator found")
                    
                    # Check for log controls
                    controls = await page.query_selector_all('select, input[type="text"], button')
                    print(f"🎛️  Found {len(controls)} log viewer controls")
                    
                    # Check for log container
                    log_container = await page.query_selector('.overflow-auto')
                    if log_container:
                        print("📜 Log container found")
                        
                        # Check for any log messages
                        log_content = await log_container.inner_text()
                        if log_content.strip():
                            print(f"📝 Log content: {log_content[:100]}...")
                        else:
                            print("⚠️  Log container is empty (this is expected if service isn't generating logs)")
                    
                    # Take a screenshot for verification
                    await page.screenshot(path="service_logs_viewer.png")
                    print("📸 Screenshot saved as service_logs_viewer.png")
                    
                else:
                    print("❌ Terminal-style log viewer not found")
            else:
                print("❌ Logs tab not found")
                
                # List available tabs
                tabs = await page.query_selector_all('.nav-link')
                tab_names = []
                for tab in tabs:
                    text = await tab.inner_text()
                    tab_names.append(text)
                print(f"📋 Available tabs: {tab_names}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path="error_screenshot.png")
            print("📸 Error screenshot saved as error_screenshot.png")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_service_logs_ui())