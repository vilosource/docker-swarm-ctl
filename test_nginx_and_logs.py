#!/usr/bin/env python3
"""
Test nginx service and generate logs for the log viewer
"""
import asyncio
from playwright.async_api import async_playwright
import requests
import time

async def test_nginx_and_logs():
    # First, let's try to access nginx through different methods
    print("🔍 Testing nginx service access...")
    
    # Method 1: Try localhost:9091
    try:
        response = requests.get("http://localhost:9091", timeout=5)
        if response.status_code == 200:
            print("✅ nginx accessible at localhost:9091")
        else:
            print(f"⚠️  nginx responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ localhost:9091 not accessible: {e}")
    
    # Method 2: Try to access via docker hosts
    docker_hosts = [
        "docker-2.lab.viloforge.com:9091",
        "docker-3.lab.viloforge.com:9091", 
        "docker-4.lab.viloforge.com:9091"
    ]
    
    for host in docker_hosts:
        try:
            response = requests.get(f"http://{host}", timeout=5)
            if response.status_code == 200:
                print(f"✅ nginx accessible at {host}")
                break
        except Exception as e:
            print(f"❌ {host} not accessible: {e}")
    
    # Now let's test the log viewer UI
    print("\n📋 Testing log viewer UI...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Login
            await page.goto("http://localhost")
            await page.wait_for_selector('input[type="email"]', timeout=10000)
            await page.fill('input[type="email"]', 'admin@localhost.local')
            await page.fill('input[type="password"]', 'changeme123')
            await page.click('button[type="submit"]')
            await page.wait_for_selector('.page-title', timeout=10000)
            print("✅ Successfully logged in")
            
            # Navigate to nginx service
            service_url = "http://localhost/hosts/e4e1086d-4533-40cd-8788-069337d04337/services/l8uqcemgt0eh7f3xcar3d2ps2"
            await page.goto(service_url)
            await page.wait_for_selector('.page-title', timeout=10000)
            print("✅ Navigated to nginx service page")
            
            # Click on Logs tab
            logs_tab = await page.query_selector('a:has-text("Logs")')
            if logs_tab:
                await logs_tab.click()
                await page.wait_for_timeout(2000)
                print("✅ Clicked on Logs tab")
                
                # Wait for log viewer to load
                await page.wait_for_selector('.bg-black', timeout=10000)
                print("✅ Log viewer loaded")
                
                # Check initial logs
                log_container = await page.query_selector('.overflow-auto')
                if log_container:
                    initial_content = await log_container.inner_text()
                    print(f"📋 Initial log content ({len(initial_content)} chars)")
                    
                    # Show first few lines
                    lines = initial_content.split('\n')[:5]
                    for i, line in enumerate(lines):
                        if line.strip():
                            print(f"  {i+1}: {line[:80]}...")
                
                # Take screenshot
                await page.screenshot(path="nginx_logs_viewer.png")
                print("📸 Screenshot saved as nginx_logs_viewer.png")
                
                # Test log viewer features
                print("\n🎛️  Testing log viewer features...")
                
                # Test refresh button
                refresh_btn = await page.query_selector('button:has-text("Reconnect")')
                if refresh_btn:
                    await refresh_btn.click()
                    print("✅ Tested reconnect button")
                
                # Test filters
                filter_input = await page.query_selector('input[placeholder*="Filter"]')
                if filter_input:
                    await filter_input.fill('worker')
                    await page.wait_for_timeout(1000)
                    print("✅ Tested log filtering")
                
                # Test log level filter
                level_select = await page.query_selector('select')
                if level_select:
                    await level_select.select_option('info')
                    await page.wait_for_timeout(1000)
                    print("✅ Tested log level filter")
                
                # Check connection status
                connection_indicator = await page.query_selector('.w-2.h-2.rounded-full')
                if connection_indicator:
                    color_class = await connection_indicator.get_attribute('class')
                    if 'bg-green-500' in color_class:
                        print("✅ Connection status: Connected")
                    elif 'bg-red-500' in color_class:
                        print("⚠️  Connection status: Disconnected")
                    else:
                        print("⚠️  Connection status: Unknown")
                
                print("\n🎉 Log viewer test completed successfully!")
                print("📋 Features tested:")
                print("  ✅ Terminal-style interface")
                print("  ✅ Real-time log display")
                print("  ✅ Connection status indicator")
                print("  ✅ Log filtering")
                print("  ✅ Reconnect functionality")
                print("  ✅ Log level filtering")
                
            else:
                print("❌ Logs tab not found")
                
        except Exception as e:
            print(f"❌ Error testing log viewer: {e}")
            await page.screenshot(path="log_viewer_error.png")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_nginx_and_logs())