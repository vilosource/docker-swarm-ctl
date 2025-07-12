#!/usr/bin/env python3
"""
Create an nginx service in the swarm on port 9091
"""
import requests
import json

def create_nginx_service():
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
    
    # Check if nginx service already exists
    print("\n🔍 Checking existing services...")
    response = requests.get(f"{base_url}/services/?host_id={manager_host_id}", headers=headers)
    if response.status_code == 200:
        services = response.json()["services"]
        for service in services:
            if service["name"] == "nginx-web":
                print(f"⚠️  nginx-web service already exists: {service['ID']}")
                return True
    
    # Create nginx service
    print("\n🚀 Creating nginx service...")
    
    service_data = {
        "name": "nginx-web",
        "image": "nginx:alpine",
        "replicas": 2,
        "ports": [
            {
                "Protocol": "tcp",
                "TargetPort": 80,
                "PublishedPort": 9091,
                "PublishMode": "ingress"
            }
        ],
        "labels": {
            "app": "nginx-web",
            "environment": "demo"
        },
        "container_labels": {
            "service": "nginx-web"
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
        print(f"✅ Created nginx service: {service['name']}")
        print(f"📋 Service ID: {service_id}")
        print(f"🌐 Service URL: http://localhost:9091")
        print(f"🔗 Service Details: http://localhost/hosts/{manager_host_id}/services/{service_id}")
        
        print("\n📺 To see the nginx service logs:")
        print(f"   1. Go to: http://localhost/hosts/{manager_host_id}/services/{service_id}")
        print(f"   2. Click the 'Logs' tab")
        print(f"   3. Generate logs by visiting: http://localhost:9091")
        
        print("\n✨ The nginx service will generate access logs when you visit http://localhost:9091")
        print("   This will provide real-time log data to test the log viewer!")
        
        return True
    else:
        print(f"❌ Failed to create service: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    create_nginx_service()