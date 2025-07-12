#!/usr/bin/env python3
"""Test what Docker info returns for swarm nodes"""

import docker
import json

def test_docker_info():
    """Check what Docker returns for swarm info"""
    try:
        # Connect to local Docker
        client = docker.DockerClient(base_url="tcp://host.docker.internal:2375")
        info = client.info()
        
        # Extract swarm info
        swarm_info = info.get("Swarm", {})
        
        print("=== Docker Swarm Information ===")
        print(f"LocalNodeState: {swarm_info.get('LocalNodeState', 'inactive')}")
        print(f"ControlAvailable: {swarm_info.get('ControlAvailable', False)}")
        print(f"NodeID: {swarm_info.get('NodeID', 'N/A')}")
        
        if swarm_info.get('LocalNodeState') == 'active':
            print(f"\nNode is in a swarm!")
            print(f"Cluster ID: {swarm_info.get('Cluster', {}).get('ID', 'N/A')}")
            print(f"Node Address: {swarm_info.get('NodeAddr', 'N/A')}")
            
            # Determine role
            if swarm_info.get('ControlAvailable'):
                print("Role: Manager (has control plane access)")
                print(f"Manager Status: {swarm_info.get('Managers', 'N/A')}")
            else:
                print("Role: Worker (no control plane access)")
                
            # Remote managers (for workers)
            remote_managers = swarm_info.get('RemoteManagers')
            if remote_managers:
                print(f"\nRemote Managers: {len(remote_managers)}")
                for mgr in remote_managers[:3]:  # Show first 3
                    print(f"  - {mgr.get('Addr', 'N/A')}")
        else:
            print("\nNode is NOT in a swarm (standalone)")
            
        # Show what the system would set
        print("\n=== System Would Set ===")
        if swarm_info.get('LocalNodeState') == 'active':
            if swarm_info.get('ControlAvailable'):
                print("host_type: swarm_manager")
            else:
                print("host_type: swarm_worker")
            print(f"swarm_id: {swarm_info.get('Cluster', {}).get('ID', 'None')}")
            print("is_leader: false (determined separately)")
        else:
            print("host_type: standalone")
            print("swarm_id: None")
            print("is_leader: false")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_docker_info()