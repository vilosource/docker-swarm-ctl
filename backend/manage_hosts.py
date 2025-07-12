#!/usr/bin/env python3
"""
Host management utility script

This script helps manage Docker hosts and their circuit breakers.
"""

import asyncio
import sys
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.db.session import AsyncSessionLocal
from app.models import DockerHost, HostCredential
from app.services.circuit_breaker import get_circuit_breaker_manager
from app.services.encryption import get_encryption_service


async def list_all_hosts():
    """List all Docker hosts with their status"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DockerHost).order_by(DockerHost.created_at.desc())
        )
        hosts = result.scalars().all()
        
        if not hosts:
            print("No hosts found.")
            return
        
        print("\nDocker Hosts:")
        print("=" * 100)
        print(f"{'ID':^36} | {'Name':^30} | {'Type':^10} | {'Status':^12} | {'URL':^30}")
        print("-" * 100)
        
        for host in hosts:
            print(f"{str(host.id):^36} | {host.name[:30]:^30} | {host.connection_type:^10} | {host.status:^12} | {host.host_url[:30]:^30}")
        
        print("\n")
        return hosts


async def show_host_details(host_id: str):
    """Show detailed information about a specific host"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DockerHost).where(DockerHost.id == UUID(host_id))
        )
        host = result.scalar_one_or_none()
        
        if not host:
            print(f"Host {host_id} not found.")
            return
        
        print(f"\nHost Details for: {host.name}")
        print("=" * 60)
        print(f"ID:              {host.id}")
        print(f"Display Name:    {host.display_name}")
        print(f"Description:     {host.description}")
        print(f"Type:            {host.host_type}")
        print(f"Connection:      {host.connection_type}")
        print(f"URL:             {host.host_url}")
        print(f"Status:          {host.status}")
        print(f"Active:          {host.is_active}")
        print(f"Default:         {host.is_default}")
        print(f"Last Check:      {host.last_health_check}")
        print(f"Docker Version:  {host.docker_version}")
        print(f"API Version:     {host.api_version}")
        
        if host.host_type.startswith('swarm'):
            print(f"\nSwarm Info:")
            print(f"Swarm ID:        {host.swarm_id}")
            print(f"Cluster Name:    {host.cluster_name}")
            print(f"Is Leader:       {host.is_leader}")
        
        # Check credentials
        result = await db.execute(
            select(HostCredential).where(HostCredential.host_id == host.id)
        )
        credentials = result.scalars().all()
        
        print(f"\nCredentials:     {len(credentials)} configured")
        for cred in credentials:
            print(f"  - {cred.credential_type}")
        
        # Check circuit breaker
        manager = get_circuit_breaker_manager()
        breaker_name = f"docker-host-{host.id}"
        breaker_status = manager.get_all_status().get(breaker_name, {})
        
        print(f"\nCircuit Breaker:")
        print(f"  State:         {breaker_status.get('state', 'unknown')}")
        print(f"  Failures:      {breaker_status.get('failure_count', 0)}")
        print(f"  Last Failure:  {breaker_status.get('last_failure_time', 'N/A')}")
        
        return host


async def reset_circuit_breaker(host_id: str):
    """Reset circuit breaker for a specific host"""
    manager = get_circuit_breaker_manager()
    breaker_name = f"docker-host-{host_id}"
    
    try:
        await manager.reset(breaker_name)
        print(f"✓ Circuit breaker '{breaker_name}' has been reset")
    except Exception as e:
        print(f"✗ Failed to reset circuit breaker: {e}")


async def reset_all_circuit_breakers():
    """Reset all circuit breakers"""
    manager = get_circuit_breaker_manager()
    all_breakers = manager.get_all_status()
    
    for breaker_name in all_breakers:
        if breaker_name.startswith("docker-host-"):
            try:
                await manager.reset(breaker_name)
                print(f"✓ Reset {breaker_name}")
            except Exception as e:
                print(f"✗ Failed to reset {breaker_name}: {e}")


async def add_ssh_credential(host_id: str, cred_type: str, cred_value: str):
    """Add a credential to a host"""
    async with AsyncSessionLocal() as db:
        encryption = get_encryption_service()
        
        # Check if host exists
        result = await db.execute(
            select(DockerHost).where(DockerHost.id == UUID(host_id))
        )
        host = result.scalar_one_or_none()
        
        if not host:
            print(f"Host {host_id} not found.")
            return
        
        # Check if credential already exists
        result = await db.execute(
            select(HostCredential).where(
                HostCredential.host_id == UUID(host_id),
                HostCredential.credential_type == cred_type
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.encrypted_value = encryption.encrypt(cred_value)
            print(f"✓ Updated {cred_type} for {host.name}")
        else:
            # Create new
            new_cred = HostCredential(
                host_id=UUID(host_id),
                credential_type=cred_type,
                encrypted_value=encryption.encrypt(cred_value)
            )
            db.add(new_cred)
            print(f"✓ Added {cred_type} for {host.name}")
        
        await db.commit()


async def main():
    print("\nDocker Host Management Utility")
    print("=" * 60)
    
    while True:
        print("\nOptions:")
        print("1. List all hosts")
        print("2. Show host details")
        print("3. Reset circuit breaker for a host")
        print("4. Reset ALL circuit breakers")
        print("5. Add SSH credential to a host")
        print("0. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "1":
            await list_all_hosts()
            
        elif choice == "2":
            hosts = await list_all_hosts()
            if hosts:
                host_id = input("Enter host ID (or partial ID): ").strip()
                # Find matching host
                matching = [h for h in hosts if str(h.id).startswith(host_id)]
                if len(matching) == 1:
                    await show_host_details(str(matching[0].id))
                elif len(matching) > 1:
                    print("Multiple hosts match. Please be more specific.")
                else:
                    print("No matching host found.")
                    
        elif choice == "3":
            hosts = await list_all_hosts()
            if hosts:
                host_id = input("Enter host ID (or partial ID): ").strip()
                # Find matching host
                matching = [h for h in hosts if str(h.id).startswith(host_id)]
                if len(matching) == 1:
                    await reset_circuit_breaker(str(matching[0].id))
                elif len(matching) > 1:
                    print("Multiple hosts match. Please be more specific.")
                else:
                    print("No matching host found.")
                    
        elif choice == "4":
            confirm = input("Reset ALL circuit breakers? (y/N): ").strip().lower()
            if confirm == 'y':
                await reset_all_circuit_breakers()
                
        elif choice == "5":
            hosts = await list_all_hosts()
            if hosts:
                host_id = input("Enter host ID (or partial ID): ").strip()
                # Find matching host
                matching = [h for h in hosts if str(h.id).startswith(host_id)]
                if len(matching) == 1:
                    host = matching[0]
                    await show_host_details(str(host.id))
                    print("\nCredential types:")
                    print("1. ssh_private_key")
                    print("2. ssh_password")
                    print("3. ssh_user")
                    print("4. use_ssh_config")
                    cred_choice = input("\nChoice (1-4): ").strip()
                    
                    cred_type_map = {
                        "1": "ssh_private_key",
                        "2": "ssh_password",
                        "3": "ssh_user",
                        "4": "use_ssh_config"
                    }
                    
                    if cred_choice in cred_type_map:
                        cred_type = cred_type_map[cred_choice]
                        
                        if cred_type == "ssh_private_key":
                            print("Paste SSH private key (press Enter twice when done):")
                            lines = []
                            while True:
                                line = input()
                                if not line and lines and lines[-1] == "":
                                    break
                                lines.append(line)
                            cred_value = "\n".join(lines[:-1])
                        else:
                            cred_value = input(f"Enter {cred_type} value: ").strip()
                        
                        await add_ssh_credential(str(host.id), cred_type, cred_value)
                    else:
                        print("Invalid choice.")
                elif len(matching) > 1:
                    print("Multiple hosts match. Please be more specific.")
                else:
                    print("No matching host found.")
                    
        elif choice == "0":
            break
        else:
            print("Invalid choice.")
    
    print("\nGoodbye!")


if __name__ == "__main__":
    asyncio.run(main())