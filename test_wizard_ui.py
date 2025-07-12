#!/usr/bin/env python3
"""
Test the SSH Host Wizard UI functionality
This creates a host using the wizard API to test the complete flow
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
EMAIL = "admin@localhost.local"
PASSWORD = "changeme123"

def login():
    """Login and get access token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None

def create_test_host_with_wizard(token):
    """Create a test host using the wizard flow"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Start wizard
    print("Starting SSH host wizard...")
    response = requests.post(
        f"{BASE_URL}/wizards/start",
        headers=headers,
        json={
            "wizard_type": "ssh_host_setup",
            "initial_state": {}
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to start wizard: {response.text}")
        return None
    
    wizard = response.json()
    wizard_id = wizard["id"]
    print(f"Wizard created: {wizard_id}")
    
    # 2. Step 0 - Connection details
    print("\nStep 1/5: Setting connection details...")
    response = requests.put(
        f"{BASE_URL}/wizards/{wizard_id}/step",
        headers=headers,
        json={
            "step_data": {
                "connection_name": "Test SSH Docker Host",
                "host_url": "ssh://demo@test-docker.example.com",
                "ssh_port": 22,
                "host_type": "standalone",
                "display_name": "Test Docker Host",
                "description": "Test host created via wizard UI test"
            }
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to update step 0: {response.text}")
        return None
    
    # Navigate to next step
    response = requests.post(f"{BASE_URL}/wizards/{wizard_id}/next", headers=headers)
    if response.status_code != 200:
        print(f"Failed to navigate to step 1: {response.text}")
        return None
    
    # 3. Step 1 - Authentication
    print("Step 2/5: Setting authentication...")
    
    # Generate SSH key
    response = requests.post(
        f"{BASE_URL}/wizards/generate-ssh-key",
        headers=headers,
        params={"comment": "test-wizard-ui@docker-control"}
    )
    
    if response.status_code != 200:
        print(f"Failed to generate key: {response.text}")
        return None
    
    key_data = response.json()
    print(f"Generated SSH key with comment: {key_data['comment']}")
    
    # Update authentication data
    response = requests.put(
        f"{BASE_URL}/wizards/{wizard_id}/step",
        headers=headers,
        json={
            "step_data": {
                "auth_method": "new_key",
                "private_key": key_data["private_key"],
                "public_key": key_data["public_key"],
                "key_generated": True
            }
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to update authentication: {response.text}")
        return None
    
    # Navigate to next step
    response = requests.post(f"{BASE_URL}/wizards/{wizard_id}/next", headers=headers)
    if response.status_code != 200:
        print(f"Failed to navigate to step 2: {response.text}")
        return None
    
    # 4. Step 2 - SSH Test (skip actual test for demo)
    print("Step 3/5: SSH test (simulated)...")
    response = requests.put(
        f"{BASE_URL}/wizards/{wizard_id}/step",
        headers=headers,
        json={
            "step_data": {
                "ssh_test_passed": True  # Simulate successful test
            }
        }
    )
    
    # Navigate to next step
    response = requests.post(f"{BASE_URL}/wizards/{wizard_id}/next", headers=headers)
    
    # 5. Step 3 - Docker Test (skip actual test for demo)
    print("Step 4/5: Docker test (simulated)...")
    response = requests.put(
        f"{BASE_URL}/wizards/{wizard_id}/step",
        headers=headers,
        json={
            "step_data": {
                "docker_test_passed": True,  # Simulate successful test
                "docker_info": {
                    "version": "24.0.7",
                    "api_version": "1.43",
                    "os": "Ubuntu 22.04.3 LTS",
                    "architecture": "x86_64",
                    "containers": 5,
                    "images": 12,
                    "is_swarm": False
                }
            }
        }
    )
    
    # Navigate to next step
    response = requests.post(f"{BASE_URL}/wizards/{wizard_id}/next", headers=headers)
    
    # 6. Step 4 - Confirmation
    print("Step 5/5: Confirmation...")
    response = requests.put(
        f"{BASE_URL}/wizards/{wizard_id}/step",
        headers=headers,
        json={
            "step_data": {
                "is_default": False,
                "tags_string": "test, demo, wizard",
                "tags": ["test", "demo", "wizard"]
            }
        }
    )
    
    # 7. Complete wizard
    print("\nCompleting wizard...")
    response = requests.post(
        f"{BASE_URL}/wizards/{wizard_id}/complete",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"Failed to complete wizard: {response.text}")
        return None
    
    result = response.json()
    print(f"✓ Wizard completed successfully!")
    print(f"  Resource ID: {result.get('resource_id')}")
    print(f"  Resource Type: {result.get('resource_type')}")
    
    return result.get('resource_id')

def check_host_status(token, host_id):
    """Check the status of the created host"""
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/hosts/{host_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        host = response.json()
        print(f"\nHost Status:")
        print(f"  Name: {host['name']}")
        print(f"  Status: {host['status']}")
        print(f"  Type: {host['host_type']}")
        print(f"  Connection: {host['connection_type']}")
        print(f"  URL: {host['host_url']}")
        if host.get('tags'):
            print(f"  Tags: {[tag['tag_name'] for tag in host['tags']]}")
    else:
        print(f"Failed to get host: {response.text}")

def cleanup_test_host(token, host_id):
    """Delete the test host"""
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.delete(
        f"{BASE_URL}/hosts/{host_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"\n✓ Test host deleted successfully")
    else:
        print(f"Failed to delete host: {response.text}")

def main():
    print("=== SSH Host Wizard UI Test ===")
    print("This test simulates the complete wizard flow\n")
    
    # Login
    token = login()
    if not token:
        print("Failed to login")
        return
    
    print("✓ Login successful")
    
    # Create host with wizard
    host_id = create_test_host_with_wizard(token)
    
    if host_id:
        # Check host status
        check_host_status(token, host_id)
        
        # Cleanup
        print("\nCleaning up...")
        cleanup_test_host(token, host_id)
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()