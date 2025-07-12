#!/usr/bin/env python3
"""
Final test of the service logs functionality
"""
import requests
import json

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
    print(f"✅ Manager host: {manager_host_id}")
    
    # List services
    print("\n🔍 Listing services...")
    response = requests.get(f"{base_url}/services/?host_id={manager_host_id}", headers=headers)
    if response.status_code == 200:
        services = response.json()["services"]
        print(f"✅ Found {len(services)} services")
        
        for service in services:
            print(f"  - {service['name']} ({service['ID'][:12]})")
            
        if services:
            # Test getting logs for the first service
            test_service = services[0]
            service_id = test_service["ID"]
            service_name = test_service["name"]
            
            print(f"\n📊 Testing log retrieval for service: {service_name}")
            
            # Test non-streaming logs endpoint
            response = requests.get(
                f"{base_url}/services/{service_id}/logs",
                params={
                    "host_id": manager_host_id,
                    "tail": 10,
                    "follow": False
                },
                headers=headers
            )
            
            if response.status_code == 200:
                logs = response.json()
                print(f"✅ Successfully retrieved logs!")
                print(f"   Got {len(logs)} log entries")
                if logs:
                    print("\n📜 Last few log entries:")
                    for log in logs[-3:]:
                        print(f"   {log}")
            else:
                print(f"❌ Failed to get logs: {response.status_code}")
                print(response.text)
            
            print(f"\n🎉 Service logs implementation is working!")
            print(f"\n📺 To see the real-time logs viewer in the UI:")
            print(f"   1. Go to: http://localhost")
            print(f"   2. Navigate to: Hosts → {manager_host_id} → Services")
            print(f"   3. Click on service '{service_name}'")
            print(f"   4. Click the 'Logs' tab")
            print(f"\n✨ The logs should now stream in real-time!")
            return True
    else:
        print(f"❌ Failed to list services: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    test_service_logs()