#!/usr/bin/env python3
"""
Check the actual Docker swarm status directly
"""
import requests
import json

def check_actual_swarm():
    # Base URL
    base_url = "http://localhost/api/v1"
    
    # Login to get token
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
    
    # Check each host's swarm info and nodes
    hosts = [
        {"id": "e4e1086d-4533-40cd-8788-069337d04337", "name": "docker-2", "type": "manager"},
        {"id": "92e60363-4284-47c4-a004-72da21dcf648", "name": "docker-3", "type": "worker"},
        {"id": "58aa0857-b89c-44b0-bfc9-67662a64a142", "name": "docker-4", "type": "worker"},
        {"id": "eefc47ba-d416-4b8d-bea8-3db96ee150ea", "name": "local", "type": "unknown"},
        {"id": "ec6fa957-0aac-47cf-8517-d898bbcbd018", "name": "docker-1", "type": "unknown"}
    ]
    
    for host in hosts:
        print(f"\n🔍 Checking {host['name']} ({host['type']}):")
        
        # Check swarm info
        try:
            response = requests.get(f"{base_url}/swarm/info?host_id={host['id']}", headers=headers)
            if response.status_code == 200:
                swarm_info = response.json()
                print(f"  ✅ Swarm ID: {swarm_info.get('id', 'N/A')}")
                print(f"  📅 Created: {swarm_info.get('created_at', 'N/A')}")
                print(f"  🏷️  Version: {swarm_info.get('version', {}).get('Index', 'N/A')}")
            else:
                print(f"  ❌ Swarm info failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"  ❌ Swarm info error: {e}")
        
        # Check nodes (only for managers)
        if host['type'] == 'manager':
            try:
                response = requests.get(f"{base_url}/nodes/?host_id={host['id']}", headers=headers)
                if response.status_code == 200:
                    nodes_info = response.json()
                    nodes = nodes_info.get('nodes', [])
                    print(f"  🐝 Nodes in this swarm: {len(nodes)}")
                    for i, node in enumerate(nodes):
                        role = node.get('role', 'unknown')
                        status = node.get('state', 'unknown')  
                        hostname = node.get('hostname', 'unknown')
                        is_leader = node.get('is_leader', False)
                        leader_text = " (LEADER)" if is_leader else ""
                        print(f"    {i+1}. {hostname} - {role.upper()} - {status.upper()}{leader_text}")
                else:
                    print(f"  ❌ Nodes info failed: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"  ❌ Nodes info error: {e}")

if __name__ == "__main__":
    check_actual_swarm()