#!/usr/bin/env python3
"""Test WebSocket endpoints"""

import asyncio
import websockets
import json
import requests
from datetime import datetime

# Base URLs
import os
if os.environ.get('DOCKER_CONTAINER'):
    # Running inside container
    BASE_URL = "http://nginx/api/v1"
    WS_BASE_URL = "ws://nginx/ws"
else:
    # Running on host
    BASE_URL = "http://localhost/api/v1"
    WS_BASE_URL = "ws://localhost/ws"

# Login to get token
def login():
    response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "admin@localhost.local",
        "password": "changeme123"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None

async def test_container_logs(token, container_id):
    """Test container logs WebSocket"""
    print(f"\n1. Testing container logs WebSocket for {container_id}...")
    
    uri = f"{WS_BASE_URL}/containers/{container_id}/logs?token={token}&tail=5&follow=false"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to logs WebSocket")
            
            # Receive messages
            message_count = 0
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    if data["type"] == "log":
                        message_count += 1
                        print(f"Log #{message_count}: {data['data'][:50]}...")
                    elif data["type"] == "info":
                        print(f"Info: {data['message']}")
                    elif data["type"] == "error":
                        print(f"Error: {data['message']}")
                        break
                        
                except asyncio.TimeoutError:
                    print("No more logs received (timeout)")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
            
            print(f"Received {message_count} log messages")
            
    except Exception as e:
        print(f"WebSocket error: {e}")

async def test_container_stats(token, container_id):
    """Test container stats WebSocket"""
    print(f"\n2. Testing container stats WebSocket for {container_id}...")
    
    uri = f"{WS_BASE_URL}/containers/{container_id}/stats?token={token}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to stats WebSocket")
            
            # Receive a few stats updates
            update_count = 0
            while update_count < 3:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    if data["type"] == "stats":
                        update_count += 1
                        stats = data["data"]
                        print(f"Stats update #{update_count}:")
                        print(f"  CPU: {stats['cpu_percent']:.2f}%")
                        print(f"  Memory: {stats['memory_usage'] / 1024 / 1024:.2f} MB ({stats['memory_percent']:.2f}%)")
                        print(f"  Network RX/TX: {stats['network_rx']} / {stats['network_tx']} bytes")
                    elif data["type"] == "error":
                        print(f"Error: {data['message']}")
                        break
                        
                except asyncio.TimeoutError:
                    print("No stats received (timeout)")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
            
            print(f"Received {update_count} stats updates")
            
    except Exception as e:
        print(f"WebSocket error: {e}")

async def main():
    print("Testing WebSocket endpoints...")
    
    # Login
    token = login()
    if not token:
        return
    
    print("Login successful!")
    
    # Get a running container
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/containers", headers=headers)
    
    if response.status_code == 200:
        containers = response.json()
        if containers:
            # Use the first running container
            container = containers[0]
            container_id = container["id"]
            print(f"Using container: {container['name']} ({container_id})")
            
            # Test logs WebSocket
            await test_container_logs(token, container_id)
            
            # Test stats WebSocket
            await test_container_stats(token, container_id)
        else:
            print("No containers found")
    else:
        print(f"Failed to get containers: {response.status_code}")
    
    print("\n✅ WebSocket tests completed!")

if __name__ == "__main__":
    asyncio.run(main())