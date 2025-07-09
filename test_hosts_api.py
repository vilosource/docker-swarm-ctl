#!/usr/bin/env python3
"""
Test script for hosts API endpoint to check swarm status
"""
import json
import requests
import sys

def test_hosts_api():
    # Base URL
    base_url = "http://localhost/api/v1"
    
    # Login to get token (using form data)
    login_data = {
        "username": "admin@localhost.local",
        "password": "changeme123"
    }
    
    print("🔑 Logging in...")
    response = requests.post(f"{base_url}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    token_data = response.json()
    access_token = token_data["access_token"]
    print(f"✅ Login successful, got access token")
    
    # Test hosts endpoint
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print("\n🔍 Testing /hosts/ endpoint...")
    response = requests.get(f"{base_url}/hosts/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Response:")
        print(json.dumps(data, indent=2))
        
        # Analyze the response
        hosts = data.get("items", [])
        total = data.get("total", 0)
        print(f"\n📊 Summary:")
        print(f"Total hosts: {total}")
        print(f"Hosts in response: {len(hosts)}")
        
        swarm_hosts = []
        for i, host in enumerate(hosts):
            print(f"\nHost {i+1}:")
            print(f"  ID: {host.get('id', 'N/A')}")
            print(f"  Name: {host.get('name', 'N/A')}")
            print(f"  Display Name: {host.get('display_name', 'N/A')}")
            print(f"  Type: {host.get('host_type', 'N/A')}")
            print(f"  Status: {host.get('status', 'N/A')}")
            print(f"  Active: {host.get('is_active', 'N/A')}")
            print(f"  Swarm ID: {host.get('swarm_id', 'N/A')}")
            print(f"  Cluster Name: {host.get('cluster_name', 'N/A')}")
            print(f"  Is Leader: {host.get('is_leader', 'N/A')}")
            
            if host.get('swarm_id'):
                swarm_hosts.append(host)
        
        print(f"\n🐝 Swarm Status:")
        print(f"Swarm hosts found: {len(swarm_hosts)}")
        
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False

if __name__ == "__main__":
    success = test_hosts_api()
    sys.exit(0 if success else 1)