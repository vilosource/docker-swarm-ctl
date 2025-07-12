#!/usr/bin/env python3
"""
Test the SSH Host Wizard functionality
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

def test_wizard_flow(token):
    """Test the complete wizard flow"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Start a new SSH host wizard
    print("\n1. Starting SSH host wizard...")
    response = requests.post(
        f"{BASE_URL}/wizards/start",
        headers=headers,
        json={
            "wizard_type": "ssh_host_setup",
            "initial_state": {}
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to start wizard: {response.status_code} - {response.text}")
        return
    
    wizard = response.json()
    wizard_id = wizard["id"]
    print(f"Wizard created: {wizard_id}")
    print(f"Current step: {wizard['current_step']}/{wizard['total_steps']}")
    
    # 2. Update step 0 - Connection details
    print("\n2. Setting connection details...")
    response = requests.put(
        f"{BASE_URL}/wizards/{wizard_id}/step",
        headers=headers,
        json={
            "step_data": {
                "connection_name": "Test SSH Host",
                "host_url": "ssh://root@test-host.example.com",
                "ssh_port": 22,
                "host_type": "standalone",
                "display_name": "Test Host",
                "description": "Test SSH host via wizard"
            }
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to update step: {response.status_code} - {response.text}")
        return
    
    # 3. Navigate to next step
    print("\n3. Moving to authentication step...")
    response = requests.post(
        f"{BASE_URL}/wizards/{wizard_id}/next",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"Failed to navigate: {response.status_code} - {response.text}")
        return
    
    wizard = response.json()
    print(f"Current step: {wizard['current_step']}/{wizard['total_steps']}")
    
    # 4. Generate SSH key
    print("\n4. Generating SSH key...")
    response = requests.post(
        f"{BASE_URL}/wizards/generate-ssh-key",
        headers=headers,
        params={"comment": "test-wizard@docker-control"}
    )
    
    if response.status_code != 200:
        print(f"Failed to generate key: {response.status_code} - {response.text}")
        return
    
    key_data = response.json()
    print("SSH key generated successfully")
    print(f"Public key: {key_data['public_key'][:50]}...")
    
    # 5. Update authentication data
    print("\n5. Setting authentication data...")
    response = requests.put(
        f"{BASE_URL}/wizards/{wizard_id}/step",
        headers=headers,
        json={
            "step_data": {
                "auth_method": "new_key",
                "private_key": key_data["private_key"],
                "public_key": key_data["public_key"]
            }
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to update auth: {response.status_code} - {response.text}")
        return
    
    # 6. List pending wizards
    print("\n6. Listing pending wizards...")
    response = requests.get(
        f"{BASE_URL}/wizards/my-pending",
        headers=headers,
        params={"wizard_type": "ssh_host_setup"}
    )
    
    if response.status_code == 200:
        pending = response.json()
        print(f"Found {pending['total']} pending wizard(s)")
        for w in pending["wizards"]:
            print(f"  - {w['id']}: Step {w['current_step']}/{w['total_steps']}")
    
    # 7. Cancel the wizard (cleanup)
    print("\n7. Cancelling wizard (cleanup)...")
    response = requests.delete(
        f"{BASE_URL}/wizards/{wizard_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print("Wizard cancelled successfully")
    else:
        print(f"Failed to cancel: {response.status_code} - {response.text}")

def main():
    print("=== SSH Host Wizard Test ===")
    
    # Login
    token = login()
    if not token:
        print("Failed to login")
        return
    
    print("Login successful")
    
    # Test wizard flow
    test_wizard_flow(token)
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()