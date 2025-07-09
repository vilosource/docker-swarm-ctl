#!/usr/bin/env python3
"""
Test the swarm detail API endpoint
"""
import requests
import json

def test_swarm_detail():
    base_url = "http://localhost/api/v1"
    
    # Login
    login_data = {
        "username": "admin@localhost.local",
        "password": "changeme123"
    }
    
    print("🔑 Logging in...")
    response = requests.post(f"{base_url}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token_data = response.json()
    access_token = token_data["access_token"]
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # First, get the swarm list to see what we have
    print("\n📋 Getting swarm list...")
    response = requests.get(f"{base_url}/swarms/", headers=headers)
    if response.status_code == 200:
        swarms = response.json()
        print(f"Found {swarms['total']} swarms")
        
        for swarm in swarms['swarms']:
            print(f"\n🐝 Swarm: {swarm['cluster_name']} ({swarm['swarm_id'][:12]})")
            print(f"   Nodes: {swarm['total_nodes']} ({swarm['manager_count']}M, {swarm['worker_count']}W)")
            print(f"   Leader: {swarm['leader_host']['display_name']} (ID: {swarm['leader_host']['id']})")
            
            # Test the detail endpoint
            print(f"\n🔍 Testing detail endpoint for swarm {swarm['swarm_id']}...")
            detail_response = requests.get(f"{base_url}/swarms/{swarm['swarm_id']}", headers=headers)
            print(f"   Status: {detail_response.status_code}")
            if detail_response.status_code != 200:
                print(f"   Error: {detail_response.text}")
            else:
                detail = detail_response.json()
                print(f"   ✅ Success! Got {len(detail.get('hosts', []))} hosts")
    else:
        print(f"❌ Failed to get swarm list: {response.status_code}")

if __name__ == "__main__":
    test_swarm_detail()