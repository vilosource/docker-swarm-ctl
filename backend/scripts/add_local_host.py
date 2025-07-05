#!/usr/bin/env python3
"""
Script to add the local Docker host to the database for backward compatibility
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import DockerHost, UserHostPermission, User, UserRole
from app.models.docker_host import HostType, ConnectionType, HostStatus


async def add_local_host():
    """Add local Docker host to the database"""
    async with AsyncSessionLocal() as db:
        # Check if local host already exists
        result = await db.execute(
            select(DockerHost).where(DockerHost.name == "local")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Local host already exists")
            return
        
        # Get admin user
        result = await db.execute(
            select(User).where(User.email == "admin@localhost.local")
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            print("Admin user not found. Please run init_db.py first.")
            return
        
        # Create local host
        local_host = DockerHost(
            name="local",
            description="Local Docker daemon",
            host_type=HostType.standalone,
            connection_type=ConnectionType.unix,
            host_url="unix:///var/run/docker.sock",
            is_active=True,
            is_default=True,
            status=HostStatus.healthy,
            created_by=admin_user.id
        )
        db.add(local_host)
        await db.flush()
        
        # Grant all users access to local host
        result = await db.execute(select(User))
        all_users = result.scalars().all()
        
        for user in all_users:
            permission = UserHostPermission(
                user_id=user.id,
                host_id=local_host.id,
                permission_level="admin" if user.role == UserRole.admin else "operator",
                granted_by=admin_user.id
            )
            db.add(permission)
        
        await db.commit()
        print(f"Successfully added local Docker host with ID: {local_host.id}")
        print("All existing users have been granted access to the local host")


if __name__ == "__main__":
    asyncio.run(add_local_host())