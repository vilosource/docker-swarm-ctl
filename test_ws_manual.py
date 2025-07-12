#!/usr/bin/env python3
"""
Manually test WebSocket connection to service logs
"""
import asyncio
import websockets
import json
import requests

async def test_service_logs_ws():
    # First get the token
    login_data = {
        "username": "admin@localhost.local",
        "password": "changeme123"
    }
    
    print("Getting auth token...")
    response = requests.post("http://localhost/api/v1/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return
    
    token = response.json()["access_token"]
    service_id = "l8uqcemgt0eh7f3xcar3d2ps2"
    host_id = "e4e1086d-4533-40cd-8788-069337d04337"
    
    # Build WebSocket URL
    ws_url = f"ws://localhost/ws/services/{service_id}/logs?host_id={host_id}&tail=50&follow=true&timestamps=false&token={token}"
    
    print(f"\nConnecting to: {ws_url}\n")
    
    try:
        async with websockets.connect(ws_url, subprotocols=["websocket"]) as websocket:
            print("Connected! Waiting for messages...\n")
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # Pretty print the message
                    print(f"[{data.get('type', 'unknown')}] ", end="")
                    
                    if data.get('type') == 'error':
                        print(f"ERROR: {data.get('message')} (Type: {data.get('error_type', 'Unknown')})")
                    elif data.get('type') == 'log':
                        print(f"{data.get('data', data.get('message', 'No content'))}")
                    else:
                        print(f"{data.get('message', json.dumps(data))}")
                        
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"\nConnection closed: {e}")
                    break
                except Exception as e:
                    print(f"\nError: {e}")
                    break
                    
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(test_service_logs_ws())