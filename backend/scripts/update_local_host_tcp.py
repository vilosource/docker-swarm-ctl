#!/usr/bin/env python3
"""
Script to update the local Docker host to use TCP connection
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import DockerHost
from app.models.docker_host import ConnectionType


async def update_local_host_to_tcp():
    """Update local Docker host to use TCP connection"""
    async with AsyncSessionLocal() as db:
        # Get local host
        result = await db.execute(
            select(DockerHost).where(DockerHost.name == "local")
        )
        local_host = result.scalar_one_or_none()
        
        if not local_host:
            print("Local host not found")
            return
        
        # Update to TCP connection
        local_host.connection_type = ConnectionType.tcp
        local_host.host_url = "tcp://host.docker.internal:2375"
        
        await db.commit()
        print(f"Successfully updated local Docker host to use TCP connection")
        print(f"Connection URL: {local_host.host_url}")


if __name__ == "__main__":
    asyncio.run(update_local_host_to_tcp())