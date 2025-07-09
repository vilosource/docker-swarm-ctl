#!/usr/bin/env python3
"""
UI tests for Docker Swarm interfaces
Tests the frontend components by making API calls that the UI would make
"""
import requests
import json
import time
from typing import Dict, Any, Optional, List

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin@localhost.local"
PASSWORD = "changeme123"

class SwarmUITester:
    def __init__(self):
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.host_id: Optional[str] = None
        self.swarm_host_id: Optional[str] = None
        
    def login(self):
        """Login and get access token"""
        print("🔐 Logging in as admin...")
        resp = self.session.post(
            f"{BASE_URL}/auth/login",
            data={"username": USERNAME, "password": PASSWORD}
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
    
    def get_hosts(self):
        """Get list of Docker hosts - simulating Hosts page load"""
        print("\n📋 Testing Hosts List (GET /hosts/)...")
        resp = self.session.get(f"{BASE_URL}/hosts/")
        
        if resp.status_code == 200:
            data = resp.json()
            hosts = data.get("items", [])
            print(f"✅ Found {len(hosts)} hosts")
            
            # Find a host that might be part of a swarm
            for host in hosts:
                print(f"   - {host['display_name']} (ID: {host['id']}, Active: {host['is_active']})")
                if host.get("is_active"):
                    self.host_id = host["id"]
                    # Check if this host is in a swarm
                    if self.check_host_swarm_status(host["id"]):
                        self.swarm_host_id = host["id"]
            
            return True
        else:
            print(f"❌ Failed to get hosts: {resp.status_code}")
            return False
    
    def check_host_swarm_status(self, host_id: str) -> bool:
        """Check if a host is part of a swarm"""
        resp = self.session.get(
            f"{BASE_URL}/swarm/",
            params={"host_id": host_id}
        )
        return resp.status_code == 200
    
    def test_swarm_overview(self):
        """Test Swarm Overview page"""
        print(f"\n🌐 Testing Swarm Overview (host: {self.swarm_host_id})...")
        
        if not self.swarm_host_id:
            print("⚠️  No swarm host available, attempting to initialize swarm...")
            if self.host_id:
                self.init_swarm_on_host(self.host_id)
                self.swarm_host_id = self.host_id
            else:
                print("❌ No host available for swarm initialization")
                return False
        
        # Test swarm info endpoint
        resp = self.session.get(
            f"{BASE_URL}/swarm/",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print("✅ Swarm Overview loaded successfully")
            print(f"   - Swarm ID: {data.get('id', 'N/A')[:12]}")
            print(f"   - Created: {data.get('created_at', 'N/A')}")
            
            # Test node count
            self.test_node_count()
            
            # Test service count
            self.test_service_count()
            
            return True
        else:
            print(f"❌ Failed to load swarm overview: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    
    def init_swarm_on_host(self, host_id: str):
        """Initialize swarm on a host"""
        print(f"🚀 Initializing swarm on host {host_id}...")
        
        init_data = {
            "advertise_addr": "127.0.0.1",
            "listen_addr": "0.0.0.0:2377"
        }
        
        resp = self.session.post(
            f"{BASE_URL}/swarm/init",
            params={"host_id": host_id},
            json=init_data
        )
        
        if resp.status_code in [200, 409]:
            print("✅ Swarm initialized or already exists")
            return True
        else:
            print(f"❌ Failed to initialize swarm: {resp.status_code}")
            return False
    
    def test_node_count(self):
        """Get node count for overview"""
        resp = self.session.get(
            f"{BASE_URL}/nodes",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            nodes = data.get("nodes", [])
            print(f"   - Total Nodes: {len(nodes)}")
            manager_count = sum(1 for n in nodes if n.get("role") == "manager")
            worker_count = sum(1 for n in nodes if n.get("role") == "worker")
            print(f"   - Managers: {manager_count}, Workers: {worker_count}")
    
    def test_service_count(self):
        """Get service count for overview"""
        resp = self.session.get(
            f"{BASE_URL}/services",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            services = data.get("services", [])
            print(f"   - Total Services: {len(services)}")
    
    def test_nodes_page(self):
        """Test Nodes management page"""
        print(f"\n🖥️  Testing Nodes Page...")
        
        if not self.swarm_host_id:
            print("⚠️  No swarm host available")
            return False
        
        # List nodes
        resp = self.session.get(
            f"{BASE_URL}/nodes",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            nodes = data.get("nodes", [])
            print(f"✅ Nodes page loaded - Found {len(nodes)} nodes")
            
            for node in nodes[:3]:
                print(f"   - {node.get('hostname', 'N/A')} - Role: {node.get('role', 'N/A')}, State: {node.get('state', 'N/A')}")
                
                # Test getting individual node details
                if node.get('id'):
                    self.test_node_details(node['id'])
            
            return True
        else:
            print(f"❌ Failed to load nodes: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    
    def test_node_details(self, node_id: str):
        """Test getting node details"""
        resp = self.session.get(
            f"{BASE_URL}/nodes/{node_id}",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            print(f"     ✓ Node details loaded for {node_id[:12]}")
        else:
            print(f"     ✗ Failed to get node details: {resp.status_code}")
    
    def test_services_page(self):
        """Test Services management page"""
        print(f"\n⚙️  Testing Services Page...")
        
        if not self.swarm_host_id:
            print("⚠️  No swarm host available")
            return False
        
        # List services
        resp = self.session.get(
            f"{BASE_URL}/services",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            services = data.get("services", [])
            print(f"✅ Services page loaded - Found {len(services)} services")
            
            # Test creating a service
            service_id = self.test_create_service()
            
            if service_id:
                # Test service details
                self.test_service_details(service_id)
                
                # Test scaling service
                self.test_scale_service(service_id)
                
                # Test service tasks
                self.test_service_tasks(service_id)
                
                # Clean up - delete the service
                self.test_delete_service(service_id)
            
            return True
        else:
            print(f"❌ Failed to load services: {resp.status_code}")
            return False
    
    def test_create_service(self) -> Optional[str]:
        """Test creating a service"""
        print("\n   📝 Testing service creation...")
        
        service_data = {
            "name": f"test-nginx-{int(time.time())}",
            "image": "nginx:alpine",
            "replicas": 2,
            "ports": [
                {
                    "target_port": 80,
                    "published_port": 8000 + int(time.time()) % 1000,  # Use dynamic port
                    "protocol": "tcp"
                }
            ],
            "labels": {
                "test": "true",
                "created_by": "ui_test"
            }
        }
        
        resp = self.session.post(
            f"{BASE_URL}/services",
            params={"host_id": self.swarm_host_id},
            json=service_data
        )
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            service_id = data.get("id")
            print(f"   ✅ Service created: {service_data['name']} (ID: {service_id})")
            return service_id
        else:
            print(f"   ❌ Failed to create service: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return None
    
    def test_service_details(self, service_id: str):
        """Test getting service details"""
        resp = self.session.get(
            f"{BASE_URL}/services/{service_id}",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✓ Service details loaded - Replicas: {data.get('replicas', 0)}")
        else:
            print(f"   ✗ Failed to get service details: {resp.status_code}")
    
    def test_scale_service(self, service_id: str):
        """Test scaling a service"""
        print("\n   🔄 Testing service scaling...")
        
        # Get current service to get version
        resp = self.session.get(
            f"{BASE_URL}/services/{service_id}",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            service = resp.json()
            version = service.get("version", {}).get("Index", 0)
            
            # Scale to 3 replicas
            scale_data = {
                "version": version,
                "replicas": 3
            }
            
            resp = self.session.put(
                f"{BASE_URL}/services/{service_id}/scale",
                params={"host_id": self.swarm_host_id},
                json=scale_data
            )
            
            if resp.status_code == 200:
                print("   ✅ Service scaled to 3 replicas")
            else:
                print(f"   ❌ Failed to scale service: {resp.status_code}")
    
    def test_service_tasks(self, service_id: str):
        """Test getting service tasks"""
        resp = self.session.get(
            f"{BASE_URL}/services/{service_id}/tasks",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            tasks = data.get("tasks", [])
            print(f"   ✓ Service tasks loaded - Found {len(tasks)} tasks")
        else:
            print(f"   ✗ Failed to get service tasks: {resp.status_code}")
    
    def test_delete_service(self, service_id: str):
        """Test deleting a service"""
        resp = self.session.delete(
            f"{BASE_URL}/services/{service_id}",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            print("   ✅ Service deleted successfully")
        else:
            print(f"   ❌ Failed to delete service: {resp.status_code}")
    
    def test_secrets_configs_page(self):
        """Test Secrets & Configs page"""
        print(f"\n🔐 Testing Secrets & Configs Page...")
        
        if not self.swarm_host_id:
            print("⚠️  No swarm host available")
            return False
        
        # Test secrets tab
        self.test_secrets_tab()
        
        # Test configs tab
        self.test_configs_tab()
        
        return True
    
    def test_secrets_tab(self):
        """Test secrets functionality"""
        print("\n   🔑 Testing Secrets tab...")
        
        # List secrets
        resp = self.session.get(
            f"{BASE_URL}/secrets",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            secrets = data.get("secrets", [])
            print(f"   ✅ Secrets loaded - Found {len(secrets)} secrets")
            
            # Test creating a secret
            secret_id = self.test_create_secret()
            
            if secret_id:
                # Clean up
                self.test_delete_secret(secret_id)
        else:
            print(f"   ❌ Failed to load secrets: {resp.status_code}")
    
    def test_create_secret(self) -> Optional[str]:
        """Test creating a secret"""
        import base64
        
        secret_data = {
            "name": f"test-secret-{int(time.time())}",
            "data": base64.b64encode(b"test-secret-value").decode(),
            "labels": {
                "test": "true"
            }
        }
        
        resp = self.session.post(
            f"{BASE_URL}/secrets",
            params={"host_id": self.swarm_host_id},
            json=secret_data
        )
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            secret_id = data.get("id")
            print(f"   ✅ Secret created: {secret_data['name']}")
            return secret_id
        else:
            print(f"   ❌ Failed to create secret: {resp.status_code}")
            return None
    
    def test_delete_secret(self, secret_id: str):
        """Test deleting a secret"""
        resp = self.session.delete(
            f"{BASE_URL}/secrets/{secret_id}",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            print("   ✅ Secret deleted successfully")
        else:
            print(f"   ❌ Failed to delete secret: {resp.status_code}")
    
    def test_configs_tab(self):
        """Test configs functionality"""
        print("\n   ⚙️  Testing Configs tab...")
        
        # List configs
        resp = self.session.get(
            f"{BASE_URL}/configs",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            configs = data.get("configs", [])
            print(f"   ✅ Configs loaded - Found {len(configs)} configs")
            
            # Test creating a config
            config_id = self.test_create_config()
            
            if config_id:
                # Clean up
                self.test_delete_config(config_id)
        else:
            print(f"   ❌ Failed to load configs: {resp.status_code}")
    
    def test_create_config(self) -> Optional[str]:
        """Test creating a config"""
        import base64
        
        config_data = {
            "name": f"test-config-{int(time.time())}",
            "data": base64.b64encode(b"test-config-value").decode(),
            "labels": {
                "test": "true"
            }
        }
        
        resp = self.session.post(
            f"{BASE_URL}/configs",
            params={"host_id": self.swarm_host_id},
            json=config_data
        )
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            config_id = data.get("id")
            print(f"   ✅ Config created: {config_data['name']}")
            return config_id
        else:
            print(f"   ❌ Failed to create config: {resp.status_code}")
            return None
    
    def test_delete_config(self, config_id: str):
        """Test deleting a config"""
        resp = self.session.delete(
            f"{BASE_URL}/configs/{config_id}",
            params={"host_id": self.swarm_host_id}
        )
        
        if resp.status_code == 200:
            print("   ✅ Config deleted successfully")
        else:
            print(f"   ❌ Failed to delete config: {resp.status_code}")
    
    def run_tests(self):
        """Run all UI tests"""
        print("🧪 Starting Docker Swarm UI Tests")
        print("=" * 60)
        
        # Login
        if not self.login():
            print("❌ Cannot proceed without authentication")
            return
        
        # Get hosts
        if not self.get_hosts():
            print("❌ Cannot proceed without hosts")
            return
        
        # Test all UI pages
        test_results = []
        
        # Test Swarm Overview
        print("\n" + "="*60)
        print("TESTING SWARM OVERVIEW PAGE")
        print("="*60)
        test_results.append(("Swarm Overview", self.test_swarm_overview()))
        
        # Test Nodes page
        print("\n" + "="*60)
        print("TESTING NODES PAGE")
        print("="*60)
        test_results.append(("Nodes Page", self.test_nodes_page()))
        
        # Test Services page
        print("\n" + "="*60)
        print("TESTING SERVICES PAGE")
        print("="*60)
        test_results.append(("Services Page", self.test_services_page()))
        
        # Test Secrets & Configs page
        print("\n" + "="*60)
        print("TESTING SECRETS & CONFIGS PAGE")
        print("="*60)
        test_results.append(("Secrets & Configs", self.test_secrets_configs_page()))
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:.<40} {status}")
        
        passed = sum(1 for _, r in test_results if r)
        total = len(test_results)
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed < total:
            print("\n⚠️  Some tests failed. Check backend logs for details.")
        else:
            print("\n✅ All tests passed!")

def main():
    tester = SwarmUITester()
    tester.run_tests()

if __name__ == "__main__":
    main()