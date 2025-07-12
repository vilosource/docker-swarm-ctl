#!/usr/bin/env python3
"""Test and fix swarm host metadata"""

import asyncio
import httpx

async def test_swarm_hosts():
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
        
        # Get all hosts
        hosts_resp = await client.get("http://localhost:8000/api/v1/hosts/", headers=headers)
        hosts = hosts_resp.json()["items"]
        
        print("Checking hosts with swarm types but no swarm_id...\n")
        
        for host in hosts:
            if host["host_type"] in ["swarm_manager", "swarm_worker"]:
                print(f"Host: {host['name']}")
                print(f"  Type: {host['host_type']}")
                print(f"  Swarm ID: {host.get('swarm_id', 'None')}")
                print(f"  Status: {host['status']}")
                
                if not host.get('swarm_id'):
                    print("  -> Missing swarm_id! Testing connection to update...")
                    
                    # Test connection to update metadata
                    test_resp = await client.post(
                        f"http://localhost:8000/api/v1/hosts/{host['id']}/test",
                        headers=headers
                    )
                    
                    if test_resp.status_code == 200:
                        # Get updated info
                        host_resp = await client.get(
                            f"http://localhost:8000/api/v1/hosts/{host['id']}",
                            headers=headers
                        )
                        updated = host_resp.json()
                        print(f"  -> Updated type: {updated['host_type']}")
                        print(f"  -> Updated swarm_id: {updated.get('swarm_id', 'None')}")
                    else:
                        print(f"  -> Test failed: {test_resp.status_code}")
                
                print()

if __name__ == "__main__":
    asyncio.run(test_swarm_hosts())