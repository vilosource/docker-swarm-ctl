#!/usr/bin/env python3
"""Test script for refactored Docker service API"""

import requests
import json
import time

# Base URL - use nginx proxy
BASE_URL = "http://localhost/api/v1"

# Login to get token
def login():
    response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "admin@localhost.local",
        "password": "changeme123"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None

# Test container operations
def test_containers(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # List containers
    print("\n1. Testing container list...")
    response = requests.get(f"{BASE_URL}/containers", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        containers = response.json()
        print(f"Found {len(containers)} containers")
        if containers:
            print(f"First container: {containers[0]['name']} ({containers[0]['status']})")
    else:
        print(f"Error: {response.text}")
    
    # Test container stats if we have containers
    if response.status_code == 200 and containers:
        container_id = containers[0]["id"]
        print(f"\n2. Testing container stats for {container_id}...")
        stats_response = requests.get(f"{BASE_URL}/containers/{container_id}/stats", headers=headers)
        print(f"Status: {stats_response.status_code}")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"CPU: {stats['cpu_percent']:.2f}%")
            print(f"Memory: {stats['memory_usage'] / 1024 / 1024:.2f} MB")
        else:
            print(f"Error: {stats_response.text}")

# Test system endpoints
def test_system(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test circuit breakers
    print("\n3. Testing circuit breaker status...")
    response = requests.get(f"{BASE_URL}/system/circuit-breakers", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        breakers = response.json()
        print(f"Circuit breakers: {json.dumps(breakers, indent=2)}")
    else:
        print(f"Error: {response.text}")

# Test container operations
def test_container_operations(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test container start/stop if we have a stopped container
    print("\n4. Testing container operations...")
    response = requests.get(f"{BASE_URL}/containers?all=true", headers=headers)
    if response.status_code == 200:
        containers = response.json()
        stopped_container = next((c for c in containers if c["status"] != "running"), None)
        
        if stopped_container:
            container_id = stopped_container["id"]
            print(f"Found stopped container: {container_id}")
            
            # Test start
            print("Testing container start...")
            start_response = requests.post(
                f"{BASE_URL}/containers/{container_id}/start", 
                headers=headers
            )
            print(f"Start status: {start_response.status_code}")
            if start_response.status_code == 200:
                print("Container started successfully")
                time.sleep(2)  # Wait for container to start
                
                # Test stop
                print("Testing container stop...")
                stop_response = requests.post(
                    f"{BASE_URL}/containers/{container_id}/stop", 
                    headers=headers
                )
                print(f"Stop status: {stop_response.status_code}")
                if stop_response.status_code == 200:
                    print("Container stopped successfully")
        else:
            print("No stopped containers found to test start/stop operations")

def main():
    print("Testing refactored Docker service API...")
    
    # Login
    token = login()
    if not token:
        return
    
    print("Login successful!")
    
    # Run tests
    test_containers(token)
    test_system(token)
    test_container_operations(token)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()