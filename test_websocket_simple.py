#!/usr/bin/env python3
"""
Simple WebSocket test without Playwright
"""
import asyncio
import websockets
import json
import requests

async def test_websocket():
    # First login to get token
    print("🔑 Logging in...")
    login_response = requests.post("http://localhost/api/v1/auth/login", data={
        "username": "admin@localhost.local",
        "password": "changeme123"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    token = login_response.json()["access_token"]
    print("✅ Login successful")
    
    # Test WebSocket connection
    ws_url = "ws://localhost/api/v1/services/l8uqcemgt0eh7f3xcar3d2ps2/logs"
    params = {
        "host_id": "e4e1086d-4533-40cd-8788-069337d04337",
        "tail": "100",
        "follow": "true",
        "timestamps": "false",
        "token": token
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{ws_url}?{query_string}"
    
    print(f"🔗 Connecting to: {full_url}")
    
    try:
        async with websockets.connect(full_url) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Listen for messages
            message_count = 0
            async for message in websocket:
                data = json.loads(message)
                print(f"📨 Message {message_count + 1}: {data}")
                message_count += 1
                
                if message_count >= 5:  # Limit to 5 messages
                    break
                    
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ WebSocket connection closed: {e}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())