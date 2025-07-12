#!/usr/bin/env python3
"""
Test script to verify host deletion works correctly
"""

import asyncio
import httpx
import sys

# API endpoint
BASE_URL = "http://localhost:8000/api/v1"

async def test_delete_host():
    """Test deleting a host"""
    async with httpx.AsyncClient() as client:
        # First, login to get auth token
        login_resp = await client.post(
            f"{BASE_URL}/auth/login",
            data={"username": "admin@localhost.local", "password": "changeme123"}  # Form data, not JSON
        )
        
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.status_code} - {login_resp.text}")
            return
        
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get list of hosts
        hosts_resp = await client.get(f"{BASE_URL}/hosts/", headers=headers)
        if hosts_resp.status_code != 200:
            print(f"Failed to get hosts: {hosts_resp.status_code}")
            return
        
        hosts = hosts_resp.json()["items"]
        print(f"Found {len(hosts)} hosts")
        
        # List all hosts
        for host in hosts:
            print(f"  - {host['name']} (ID: {host['id']}, Type: {host['connection_type']}, Status: {host['status']})")
        
        # Find any host to test deletion (preferably not the local one)
        test_host = None
        for host in hosts:
            if host["name"] != "local":  # Don't delete the local host
                test_host = host
                break
        
        if not test_host:
            print("No suitable host found to test deletion")
            return
        
        print(f"\nAttempting to delete host: {test_host['name']} (ID: {test_host['id']})")
        
        # Try to delete the host
        delete_resp = await client.delete(
            f"{BASE_URL}/hosts/{test_host['id']}",
            headers=headers
        )
        
        print(f"Delete response status: {delete_resp.status_code}")
        print(f"Delete response: {delete_resp.text}")
        
        if delete_resp.status_code == 200:
            print("\n✅ Host deleted successfully!")
        else:
            print(f"\n❌ Failed to delete host: {delete_resp.status_code}")


if __name__ == "__main__":
    asyncio.run(test_delete_host())