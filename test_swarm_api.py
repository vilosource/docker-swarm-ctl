#!/usr/bin/env python3
"""
Test script for Docker Swarm API endpoints
"""
import requests
import json
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
EMAIL = "admin@localhost.local"
PASSWORD = "changeme123"

class SwarmAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.host_id: Optional[str] = None
    
    def login(self):
        """Login and get access token"""
        print("🔐 Logging in...")
        resp = self.session.post(
            f"{BASE_URL}/auth/login",
            data={"username": EMAIL, "password": PASSWORD}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    
    def get_swarm_host(self):
        """Get a Docker host that supports Swarm"""
        print("\n🔍 Getting Docker hosts...")
        resp = self.session.get(f"{BASE_URL}/hosts/")
        
        if resp.status_code == 200:
            data = resp.json()
            hosts = data.get("items", [])
            # Find a host that might be a swarm manager
            for host in hosts:
                if host.get("is_active"):
                    self.host_id = host["id"]
                    print(f"✅ Using host: {host['display_name']} (ID: {self.host_id})")
                    return True
            print("❌ No active hosts found")
            return False
        else:
            print(f"❌ Failed to get hosts: {resp.status_code}")
            return False
    
    def test_swarm_info(self):
        """Test GET /swarm/info endpoint"""
        print("\n📊 Testing Swarm Info...")
        resp = self.session.get(
            f"{BASE_URL}/swarm/",
            params={"host_id": self.host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print("✅ Swarm info retrieved successfully")
            print(f"   - Swarm ID: {data.get('id', 'N/A')}")
            print(f"   - Node ID: {data.get('node_id', 'N/A')}")
            print(f"   - Is Manager: {data.get('is_manager', False)}")
            return True
        elif resp.status_code == 404:
            print("❌ Swarm not initialized on this host")
            return False
        else:
            print(f"❌ Failed to get swarm info: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    
    def test_init_swarm(self):
        """Test POST /swarm/init endpoint"""
        print("\n🚀 Testing Swarm Initialization...")
        init_data = {
            "advertise_addr": "127.0.0.1",
            "listen_addr": "0.0.0.0:2377"
        }
        
        resp = self.session.post(
            f"{BASE_URL}/swarm/init",
            params={"host_id": self.host_id},
            json=init_data
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print("✅ Swarm initialized successfully")
            print(f"   - Node ID: {data.get('node_id', 'N/A')}")
            return True
        elif resp.status_code == 409:
            print("ℹ️  Swarm already initialized")
            return True
        else:
            print(f"❌ Failed to initialize swarm: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    
    def test_nodes(self):
        """Test nodes endpoints"""
        print("\n🖥️  Testing Nodes API...")
        
        # List nodes
        resp = self.session.get(
            f"{BASE_URL}/nodes",
            params={"host_id": self.host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            nodes = data.get("nodes", [])
            print(f"✅ Listed {len(nodes)} nodes")
            for node in nodes[:3]:  # Show first 3
                print(f"   - {node.get('hostname', 'N/A')} ({node.get('role', 'N/A')})")
            return True
        else:
            print(f"❌ Failed to list nodes: {resp.status_code}")
            return False
    
    def test_services(self):
        """Test services endpoints"""
        print("\n🔧 Testing Services API...")
        
        # Create a test service
        service_data = {
            "name": "test-nginx",
            "image": "nginx:alpine",
            "replicas": 1,
            "ports": [
                {
                    "target_port": 80,
                    "published_port": 8080,
                    "protocol": "tcp"
                }
            ]
        }
        
        # Create service
        resp = self.session.post(
            f"{BASE_URL}/services",
            params={"host_id": self.host_id},
            json=service_data
        )
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            service_id = data.get("id")
            print(f"✅ Created service: {service_data['name']} (ID: {service_id})")
            
            # List services
            self.list_services()
            
            # Delete the test service
            if service_id:
                self.delete_service(service_id)
            
            return True
        else:
            print(f"❌ Failed to create service: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    
    def list_services(self):
        """List services"""
        resp = self.session.get(
            f"{BASE_URL}/services",
            params={"host_id": self.host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            services = data.get("services", [])
            print(f"✅ Listed {len(services)} services")
            for service in services[:3]:  # Show first 3
                print(f"   - {service.get('name', 'N/A')} ({service.get('replicas', 0)} replicas)")
        else:
            print(f"❌ Failed to list services: {resp.status_code}")
    
    def delete_service(self, service_id: str):
        """Delete a service"""
        resp = self.session.delete(
            f"{BASE_URL}/services/{service_id}",
            params={"host_id": self.host_id}
        )
        
        if resp.status_code == 200:
            print(f"✅ Deleted service: {service_id}")
        else:
            print(f"❌ Failed to delete service: {resp.status_code}")
    
    def test_tasks(self):
        """Test tasks endpoint - Skipping as tasks are accessed through services"""
        print("\n📋 Testing Tasks API...")
        print("ℹ️  Tasks are accessed through /services/{service_id}/tasks endpoint")
        return True
    
    def test_secrets(self):
        """Test secrets endpoints"""
        print("\n🔐 Testing Secrets API...")
        
        # Create a test secret
        secret_data = {
            "name": "test-secret",
            "data": "c2VjcmV0LWRhdGE="  # base64 encoded "secret-data"
        }
        
        # Create secret
        resp = self.session.post(
            f"{BASE_URL}/secrets",
            params={"host_id": self.host_id},
            json=secret_data
        )
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            secret_id = data.get("id")
            print(f"✅ Created secret: {secret_data['name']} (ID: {secret_id})")
            
            # List secrets
            self.list_secrets()
            
            # Delete the test secret
            if secret_id:
                self.delete_secret(secret_id)
            
            return True
        else:
            print(f"❌ Failed to create secret: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    
    def list_secrets(self):
        """List secrets"""
        resp = self.session.get(
            f"{BASE_URL}/secrets",
            params={"host_id": self.host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            secrets = data.get("secrets", [])
            print(f"✅ Listed {len(secrets)} secrets")
            for secret in secrets[:3]:  # Show first 3
                print(f"   - {secret.get('name', 'N/A')}")
        else:
            print(f"❌ Failed to list secrets: {resp.status_code}")
    
    def delete_secret(self, secret_id: str):
        """Delete a secret"""
        resp = self.session.delete(
            f"{BASE_URL}/secrets/{secret_id}",
            params={"host_id": self.host_id}
        )
        
        if resp.status_code == 200:
            print(f"✅ Deleted secret: {secret_id}")
        else:
            print(f"❌ Failed to delete secret: {resp.status_code}")
    
    def test_configs(self):
        """Test configs endpoints"""
        print("\n⚙️  Testing Configs API...")
        
        # Create a test config
        config_data = {
            "name": "test-config",
            "data": "Y29uZmlnLWRhdGE="  # base64 encoded "config-data"
        }
        
        # Create config
        resp = self.session.post(
            f"{BASE_URL}/configs",
            params={"host_id": self.host_id},
            json=config_data
        )
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            config_id = data.get("id")
            print(f"✅ Created config: {config_data['name']} (ID: {config_id})")
            
            # List configs
            self.list_configs()
            
            # Delete the test config
            if config_id:
                self.delete_config(config_id)
            
            return True
        else:
            print(f"❌ Failed to create config: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    
    def list_configs(self):
        """List configs"""
        resp = self.session.get(
            f"{BASE_URL}/configs",
            params={"host_id": self.host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            configs = data.get("configs", [])
            print(f"✅ Listed {len(configs)} configs")
            for config in configs[:3]:  # Show first 3
                print(f"   - {config.get('name', 'N/A')}")
        else:
            print(f"❌ Failed to list configs: {resp.status_code}")
    
    def delete_config(self, config_id: str):
        """Delete a config"""
        resp = self.session.delete(
            f"{BASE_URL}/configs/{config_id}",
            params={"host_id": self.host_id}
        )
        
        if resp.status_code == 200:
            print(f"✅ Deleted config: {config_id}")
        else:
            print(f"❌ Failed to delete config: {resp.status_code}")
    
    def run_tests(self):
        """Run all tests"""
        print("🧪 Starting Docker Swarm API Tests")
        print("=" * 50)
        
        # Login
        if not self.login():
            print("❌ Cannot proceed without authentication")
            return
        
        # Get a host
        if not self.get_swarm_host():
            print("❌ Cannot proceed without a Docker host")
            return
        
        # Test swarm endpoints
        swarm_active = self.test_swarm_info()
        
        if not swarm_active:
            # Try to initialize swarm
            self.test_init_swarm()
            # Check again
            swarm_active = self.test_swarm_info()
        
        if swarm_active:
            # Test all swarm endpoints
            self.test_nodes()
            self.test_services()
            self.test_tasks()
            self.test_secrets()
            self.test_configs()
        else:
            print("\n⚠️  Swarm is not active. Skipping swarm-specific tests.")
        
        print("\n" + "=" * 50)
        print("✅ Testing completed!")

def main():
    tester = SwarmAPITester()
    tester.run_tests()

if __name__ == "__main__":
    main()