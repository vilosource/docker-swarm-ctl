#!/usr/bin/env python3
"""
Test connectivity to lab Docker hosts
"""
import docker
import requests
from typing import Optional

def test_docker_host(hostname: str, port: int = 2375) -> bool:
    """Test connection to a Docker host"""
    base_url = f"tcp://{hostname}:{port}"
    
    print(f"\nTesting connection to {hostname}...")
    
    try:
        # First try with HTTP API directly
        response = requests.get(f"http://{hostname}:{port}/version", timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            print(f"✓ HTTP API accessible - Docker version: {version_info.get('Version')}")
        else:
            print(f"✗ HTTP API returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ HTTP API connection failed: {e}")
        return False
    
    try:
        # Now try with Docker SDK
        client = docker.DockerClient(base_url=base_url)
        version = client.version()
        print(f"✓ Docker SDK connected successfully")
        
        # Get some basic info
        info = client.info()
        print(f"  - Containers: {info.get('Containers', 0)}")
        print(f"  - Images: {info.get('Images', 0)}")
        print(f"  - Server Version: {info.get('ServerVersion', 'Unknown')}")
        
        # List containers
        containers = client.containers.list(all=True)
        print(f"  - Running containers: {len([c for c in containers if c.status == 'running'])}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"✗ Docker SDK connection failed: {e}")
        return False

def main():
    """Test all lab hosts"""
    lab_hosts = [
        "docker-1.lab.viloforge.com",
        "docker-2.lab.viloforge.com",
        "docker-3.lab.viloforge.com",
        "docker-4.lab.viloforge.com",
    ]
    
    print("Testing Docker lab host connectivity...")
    print("=" * 50)
    
    results = {}
    for host in lab_hosts:
        results[host] = test_docker_host(host)
    
    print("\n" + "=" * 50)
    print("Summary:")
    for host, success in results.items():
        status = "✓ Connected" if success else "✗ Failed"
        print(f"  {host}: {status}")

if __name__ == "__main__":
    main()