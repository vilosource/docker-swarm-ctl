#!/usr/bin/env python3
"""
Script to reset circuit breakers and manage Docker hosts

This script can be used to:
1. Reset circuit breakers for failed hosts
2. Update host connection types
3. Delete hosts that can't be connected
"""

import asyncio
import sys
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.db.session import AsyncSessionLocal
from app.models import DockerHost
from app.services.circuit_breaker import get_circuit_breaker_manager


async def list_hosts():
    """List all Docker hosts"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DockerHost))
        hosts = result.scalars().all()
        
        print("\nDocker Hosts:")
        print("-" * 80)
        for host in hosts:
            print(f"ID: {host.id}")
            print(f"Name: {host.name}")
            print(f"URL: {host.host_url}")
            print(f"Type: {host.connection_type}")
            print(f"Status: {host.status}")
            print("-" * 80)
        
        return hosts


async def reset_circuit_breaker(host_id: str):
    """Reset circuit breaker for a specific host"""
    manager = get_circuit_breaker_manager()
    breaker_name = f"docker-host-{host_id}"
    
    try:
        await manager.reset(breaker_name)
        print(f"✓ Circuit breaker '{breaker_name}' has been reset")
    except Exception as e:
        print(f"✗ Failed to reset circuit breaker: {e}")


async def update_host_type(host_id: str, new_type: str):
    """Update host connection type"""
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(DockerHost)
            .where(DockerHost.id == UUID(host_id))
            .values(connection_type=new_type)
        )
        await db.commit()
        print(f"✓ Updated host {host_id} to connection type: {new_type}")


async def delete_host(host_id: str):
    """Delete a Docker host"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DockerHost).where(DockerHost.id == UUID(host_id))
        )
        host = result.scalar_one_or_none()
        
        if host:
            await db.delete(host)
            await db.commit()
            print(f"✓ Deleted host {host.name} ({host_id})")
        else:
            print(f"✗ Host {host_id} not found")


async def main():
    print("\nDocker Host Management Script")
    print("=" * 80)
    
    # List all hosts
    hosts = await list_hosts()
    
    # Find SSH hosts
    ssh_hosts = [h for h in hosts if h.connection_type == "ssh"]
    
    if ssh_hosts:
        print("\n⚠️  WARNING: SSH hosts detected!")
        print("SSH connections are not yet supported in this version.")
        print("\nOptions for SSH hosts:")
        print("1. Delete the host and recreate with TCP/TLS")
        print("2. Update the host to use TCP connection (if Docker API is exposed)")
        print("3. Wait for SSH support in a future release")
        
        for host in ssh_hosts:
            print(f"\nSSH Host: {host.name} ({host.id})")
            
            # Reset circuit breaker
            await reset_circuit_breaker(str(host.id))
            
            # Offer to delete or update
            action = input("\nAction? (d=delete, t=change to tcp, s=skip): ").lower()
            
            if action == 'd':
                await delete_host(str(host.id))
            elif action == 't':
                new_url = input("Enter TCP URL (e.g., tcp://host:2376): ")
                if new_url:
                    # Update the host
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(DockerHost)
                            .where(DockerHost.id == host.id)
                            .values(
                                connection_type="tcp",
                                host_url=new_url
                            )
                        )
                        await db.commit()
                    print(f"✓ Updated host to TCP connection")
                    await reset_circuit_breaker(str(host.id))
    else:
        print("\n✓ No SSH hosts found")
    
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())