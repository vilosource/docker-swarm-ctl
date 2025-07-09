#!/usr/bin/env python3
"""Test the new swarms overview API"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin@localhost.local"
PASSWORD = "changeme123"

def test_swarms_api():
    """Test the swarms overview endpoint"""
    
    # Login
    print("1. Logging in...")
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": USERNAME, "password": PASSWORD}
    )
    
    if login_resp.status_code != 200:
        print(f"❌ Login failed: {login_resp.status_code}")
        return
    
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Get all swarm clusters
    print("\n2. Getting swarm clusters overview...")
    resp = requests.get(f"{BASE_URL}/swarms/", headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Success! Found {data['total']} swarm clusters")
        
        for swarm in data["swarms"]:
            print(f"\n   Cluster: {swarm['cluster_name']}")
            print(f"   - Swarm ID: {swarm['swarm_id'][:12]}")
            print(f"   - Total Nodes: {swarm['total_nodes']} ({swarm['manager_count']}M, {swarm['worker_count']}W)")
            print(f"   - Services: {swarm['service_count']}")
            print(f"   - Leader: {swarm['leader_host']['display_name']}")
    else:
        print(f"❌ Failed: {resp.status_code}")
        print(f"Response: {resp.text}")
    
    # Also test getting hosts to see swarm info
    print("\n3. Getting hosts to check swarm_id population...")
    resp = requests.get(f"{BASE_URL}/hosts/", headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        for host in data["items"][:3]:
            print(f"\n   Host: {host.get('display_name', 'N/A')}")
            print(f"   - Swarm ID: {host.get('swarm_id', 'None')}")
            print(f"   - Cluster Name: {host.get('cluster_name', 'None')}")
            print(f"   - Host Type: {host.get('host_type', 'None')}")

if __name__ == "__main__":
    test_swarms_api()