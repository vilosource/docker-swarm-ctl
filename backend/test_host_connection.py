#!/usr/bin/env python3
"""Test host connection and show the update"""

import asyncio
import httpx

async def test_host_connection():
    async with httpx.AsyncClient() as client:
        # Login
        login_resp = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            data={"username": "admin@localhost.local", "password": "changeme123"}
        )
        
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.status_code}")
            return
        
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get the local-docker host
        hosts_resp = await client.get("http://localhost:8000/api/v1/hosts/", headers=headers)
        hosts = hosts_resp.json()["items"]
        
        local_host = None
        for host in hosts:
            if "local" in host["name"].lower() or "127.0.0.1" in host["name"]:
                local_host = host
                break
        
        if not local_host:
            print("No local host found")
            return
        
        print(f"Found host: {local_host['name']}")
        print(f"Current type: {local_host['host_type']}")
        print(f"Current status: {local_host['status']}")
        
        # Test connection - this will update the host type based on actual swarm status
        print("\nTesting connection...")
        test_resp = await client.post(
            f"http://localhost:8000/api/v1/hosts/{local_host['id']}/test",
            headers=headers
        )
        
        if test_resp.status_code == 200:
            result = test_resp.json()
            print(f"Connection test: {result['message']}")
            
            # Get updated host info
            host_resp = await client.get(
                f"http://localhost:8000/api/v1/hosts/{local_host['id']}",
                headers=headers
            )
            updated_host = host_resp.json()
            
            print(f"\nAfter test:")
            print(f"Host type: {updated_host['host_type']}")
            print(f"Status: {updated_host['status']}")
            print(f"Is leader: {updated_host.get('is_leader', False)}")
            print(f"Swarm ID: {updated_host.get('swarm_id', 'None')}")
        else:
            print(f"Test failed: {test_resp.status_code} - {test_resp.text}")

if __name__ == "__main__":
    asyncio.run(test_host_connection())