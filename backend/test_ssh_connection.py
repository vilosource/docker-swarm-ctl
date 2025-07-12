#!/usr/bin/env python3
"""
Test script for SSH Docker connections

This script tests the SSH implementation by:
1. Creating a test host with SSH connection
2. Testing the connection
3. Listing containers via SSH
"""

import asyncio
import sys
from uuid import uuid4

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.db.session import AsyncSessionLocal
from app.models import DockerHost, User, HostCredential
from app.services.encryption import get_encryption_service
from app.services.docker_connection_manager import get_docker_connection_manager
from sqlalchemy import select


async def test_ssh_connection():
    """Test SSH connection to Docker"""
    
    print("\nSSH Docker Connection Test")
    print("=" * 50)
    
    async with AsyncSessionLocal() as db:
        # Get admin user
        result = await db.execute(
            select(User).where(User.username == "admin")
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            print("❌ Admin user not found. Please create an admin user first.")
            return
        
        # Get encryption service
        encryption = get_encryption_service()
        
        # Test connection parameters
        print("\nEnter SSH connection details:")
        ssh_host = input("SSH Host (e.g., server.example.com): ").strip()
        ssh_port = input("SSH Port (default 22): ").strip() or "22"
        ssh_user = input("SSH User (default root): ").strip() or "root"
        
        # Create SSH URL
        host_url = f"ssh://{ssh_user}@{ssh_host}:{ssh_port}"
        print(f"\nSSH URL: {host_url}")
        
        # Get authentication method
        print("\nAuthentication method:")
        print("1. Use system SSH configuration (SSH agent/keys)")
        print("2. Provide SSH private key")
        print("3. Password authentication")
        auth_method = input("Choose (1, 2, or 3): ").strip()
        
        credentials = []
        
        if auth_method == "1":
            # Use system SSH config - no credentials needed!
            print("\nUsing system SSH configuration.")
            print("Make sure you can connect with: ssh", host_url.replace('ssh://', ''))
            
            # Optionally disable SSH config
            use_config = input("Use ~/.ssh/config? (Y/n): ").strip().lower()
            if use_config == 'n':
                credentials.append({
                    'type': 'use_ssh_config',
                    'value': encryption.encrypt('false')
                })
                
        elif auth_method == "2":
            print("\nPaste your SSH private key (press Enter twice when done):")
            key_lines = []
            while True:
                line = input()
                if not line and key_lines and key_lines[-1] == "":
                    break
                key_lines.append(line)
            
            private_key = "\n".join(key_lines[:-1])  # Remove last empty line
            
            # Create private key credential
            credentials.append({
                'type': 'ssh_private_key',
                'value': encryption.encrypt(private_key)
            })
            
            # Ask for passphrase
            passphrase = input("\nPrivate key passphrase (leave empty if none): ").strip()
            if passphrase:
                credentials.append({
                    'type': 'ssh_private_key_passphrase',
                    'value': encryption.encrypt(passphrase)
                })
                
        elif auth_method == "3":
            password = input("\nSSH Password: ").strip()
            credentials.append({
                'type': 'ssh_password',
                'value': encryption.encrypt(password)
            })
        else:
            print("❌ Invalid authentication method")
            return
        
        # Create test host
        print("\nCreating test SSH host...")
        test_host = DockerHost(
            id=uuid4(),
            name=f"ssh-test-{ssh_host}",
            display_name="SSH Test Host",
            description="Test SSH Docker connection",
            host_type="standalone",
            connection_type="ssh",
            host_url=host_url,
            is_active=True,
            is_default=False,
            status="pending",
            created_by=admin_user.id
        )
        
        db.add(test_host)
        
        # Add credentials
        for cred in credentials:
            host_cred = HostCredential(
                host_id=test_host.id,
                credential_type=cred['type'],
                encrypted_value=cred['value']
            )
            db.add(host_cred)
        
        # Add SSH user if not in URL
        if '@' not in host_url and ssh_user != 'root':
            host_cred = HostCredential(
                host_id=test_host.id,
                credential_type='ssh_user',
                encrypted_value=encryption.encrypt(ssh_user)
            )
            db.add(host_cred)
        
        await db.commit()
        
        print(f"✅ Created test host: {test_host.name}")
        
        # Test connection
        print("\nTesting SSH connection...")
        
        try:
            # Get connection manager
            connection_manager = get_docker_connection_manager()
            
            # Get Docker client
            client = await connection_manager.get_client(
                str(test_host.id),
                admin_user,
                db
            )
            
            print("✅ Successfully connected via SSH!")
            
            # Test Docker operations
            print("\nTesting Docker operations...")
            
            # Get version
            version = client.version()
            print(f"Docker version: {version.get('Version')}")
            print(f"API version: {version.get('ApiVersion')}")
            
            # List containers
            containers = client.containers.list(all=True)
            print(f"\nContainers: {len(containers)}")
            for container in containers[:5]:  # Show first 5
                print(f"  - {container.name}: {container.status}")
            
            # Get system info
            info = client.info()
            print(f"\nSystem info:")
            print(f"  - OS: {info.get('OperatingSystem')}")
            print(f"  - Architecture: {info.get('Architecture')}")
            print(f"  - CPUs: {info.get('NCPU')}")
            print(f"  - Memory: {info.get('MemTotal', 0) / (1024**3):.1f} GB")
            
            print("\n✅ All tests passed!")
            
        except Exception as e:
            print(f"\n❌ Connection failed: {e}")
            
            # Clean up on failure
            await db.delete(test_host)
            await db.commit()
            print("Cleaned up test host")
            
            # Print detailed error for debugging
            import traceback
            print("\nDetailed error:")
            traceback.print_exc()
        
        # Optionally clean up
        keep = input("\nKeep test host? (y/N): ").strip().lower()
        if keep != 'y':
            await db.delete(test_host)
            await db.commit()
            print("✅ Cleaned up test host")
        else:
            print(f"Test host kept: {test_host.name} ({test_host.id})")


if __name__ == "__main__":
    asyncio.run(test_ssh_connection())