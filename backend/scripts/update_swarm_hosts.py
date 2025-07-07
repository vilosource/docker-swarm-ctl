import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.docker_host import DockerHost
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_swarm_hosts():
    """Update Docker Swarm host URLs to correct domain"""
    async with AsyncSessionLocal() as session:
        # Update docker-3
        result = await session.execute(
            select(DockerHost).where(DockerHost.name == "docker-3 (Worker)")
        )
        host = result.scalar_one_or_none()
        if host:
            host.host_url = "tcp://docker-3.lab.viloforge.com:2375"
            logger.info(f"Updated host URL for: {host.name}")
        
        # Update docker-4
        result = await session.execute(
            select(DockerHost).where(DockerHost.name == "docker-4 (Worker)")
        )
        host = result.scalar_one_or_none()
        if host:
            host.host_url = "tcp://docker-4.lab.viloforge.com:2375"
            logger.info(f"Updated host URL for: {host.name}")
        
        await session.commit()
        
        print("=" * 60)
        print("DOCKER SWARM HOSTS UPDATED")
        print("=" * 60)
        print("Updated host URLs to use correct domain (viloforge.com)")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(update_swarm_hosts())