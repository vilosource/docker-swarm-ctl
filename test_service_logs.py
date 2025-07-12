#!/usr/bin/env python3
"""
Test the service logs functionality by creating a test service
"""
import requests
import json
import time

def test_service_logs():
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
        print(response.text)
        return False
    
    token_data = response.json()
    access_token = token_data["access_token"]
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Get swarm manager host
    print("\n📋 Getting swarm info...")
    response = requests.get(f"{base_url}/swarms/", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to get swarms: {response.status_code}")
        print(response.text)
        return False
    
    swarms = response.json()["swarms"]
    if not swarms:
        print("❌ No swarms found")
        return False
    
    swarm = swarms[0]
    manager_host_id = swarm["leader_host"]["id"]
    print(f"Manager host: {manager_host_id}")
    
    # Check existing services
    print("\n🔍 Checking existing services...")
    response = requests.get(f"{base_url}/services/?host_id={manager_host_id}", headers=headers)
    if response.status_code == 200:
        services = response.json()["services"]
        print(f"Found {len(services)} existing services")
        
        for service in services:
            print(f"  - {service['name']} ({service['ID'][:12]})")
            
        if services:
            service_id = services[0]["ID"]
            print(f"\n✅ Using existing service: {services[0]['name']}")
            print(f"📋 Service ID: {service_id}")
            print(f"🌐 View service details at: http://localhost/hosts/{manager_host_id}/services/{service_id}")
            print("\n📺 To see the real-time logs viewer:")
            print(f"   1. Go to: http://localhost")
            print(f"   2. Navigate to: Hosts → Services")
            print(f"   3. Click on service '{services[0]['name']}'")
            print(f"   4. Click the 'Logs' tab")
            return True
    
    # Create a test service
    print("\n🚀 Creating a test service...")
    
    service_data = {
        "name": "test-logger",
        "image": "busybox:latest",
        "command": ["sh", "-c", "while true; do echo 'Test log message at' $(date); sleep 5; done"],
        "replicas": 1,
        "labels": {
            "test": "true"
        }
    }
    
    response = requests.post(
        f"{base_url}/services/?host_id={manager_host_id}", 
        headers=headers,
        json=service_data
    )
    
    if response.status_code == 200:
        service = response.json()
        service_id = service["ID"]
        print(f"✅ Created test service: {service['name']}")
        print(f"📋 Service ID: {service_id}")
        print(f"🌐 View service details at: http://localhost/hosts/{manager_host_id}/services/{service_id}")
        print("\n📺 To see the real-time logs viewer:")
        print(f"   1. Go to: http://localhost")
        print(f"   2. Navigate to: Hosts → Services")
        print(f"   3. Click on service 'test-logger'")
        print(f"   4. Click the 'Logs' tab")
        print("\n⏱️ Wait a few seconds for the service to start generating logs, then check the UI!")
        return True
    else:
        print(f"❌ Failed to create service: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    test_service_logs()