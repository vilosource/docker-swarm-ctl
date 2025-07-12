#!/usr/bin/env python3
"""
Test WebSocket connection for service logs
"""
import asyncio
import websockets
import json
import requests

async def test_websocket_logs():
    # First get auth token
    login_data = {
        "username": "admin@localhost.local",
        "password": "changeme123"
    }
    
    print("🔑 Getting auth token...")
    response = requests.post("http://localhost/api/v1/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json()["access_token"]
    print(f"✅ Token obtained: {token[:20]}...")
    
    # Test WebSocket connection
    service_id = "sduv8m6v0yxvv6ulrdpjg4q2j"
    host_id = "e4e1086d-4533-40cd-8788-069337d04337"
    
    ws_url = f"ws://localhost/api/v1/services/{service_id}/logs?host_id={host_id}&tail=10&follow=true&timestamps=false&token={token}"
    
    print(f"🔌 Connecting to WebSocket: {ws_url[:100]}...")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Listen for messages for 10 seconds
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"📨 Received: {data.get('type')} - {data.get('data', data.get('message'))}")
                except json.JSONDecodeError:
                    print(f"📨 Raw message: {message}")
                    
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ WebSocket connection closed: {e}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_logs())