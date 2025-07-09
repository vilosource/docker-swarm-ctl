#!/usr/bin/env python3
"""
Test script for swarms API endpoint
"""
import json
import requests
import sys

def test_swarms_api():
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
    
    # Test swarms endpoint
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print("\n🔍 Testing /swarms/ endpoint...")
    response = requests.get(f"{base_url}/swarms/", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Response:")
        print(json.dumps(data, indent=2))
        
        # Analyze the response
        swarms = data.get("swarms", [])
        total = data.get("total", 0)
        print(f"\n📊 Summary:")
        print(f"Total swarms: {total}")
        print(f"Swarms in response: {len(swarms)}")
        
        for i, swarm in enumerate(swarms):
            print(f"\nSwarm {i+1}:")
            print(f"  ID: {swarm.get('swarm_id', 'N/A')}")
            print(f"  Name: {swarm.get('cluster_name', 'N/A')}")
            print(f"  Nodes: {swarm.get('total_nodes', 0)} ({swarm.get('manager_count', 0)}M, {swarm.get('worker_count', 0)}W)")
            print(f"  Services: {swarm.get('service_count', 0)}")
            print(f"  Leader: {swarm.get('leader_host', {}).get('display_name', 'N/A')}")
        
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False

if __name__ == "__main__":
    success = test_swarms_api()
    sys.exit(0 if success else 1)