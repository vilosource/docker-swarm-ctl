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


async def update_host_names():
    """Update Docker host names to remove role suffixes"""
    async with AsyncSessionLocal() as session:
        # Update docker-2
        result = await session.execute(
            select(DockerHost).where(DockerHost.name == "docker-2 (Manager)")
        )
        host = result.scalar_one_or_none()
        if host:
            host.name = "docker-2"
            host.display_name = "docker-2"
            logger.info(f"Updated host name: docker-2")
        
        # Update docker-3
        result = await session.execute(
            select(DockerHost).where(DockerHost.name == "docker-3 (Worker)")
        )
        host = result.scalar_one_or_none()
        if host:
            host.name = "docker-3"
            host.display_name = "docker-3"
            logger.info(f"Updated host name: docker-3")
        
        # Update docker-4
        result = await session.execute(
            select(DockerHost).where(DockerHost.name == "docker-4 (Worker)")
        )
        host = result.scalar_one_or_none()
        if host:
            host.name = "docker-4"
            host.display_name = "docker-4"
            logger.info(f"Updated host name: docker-4")
        
        await session.commit()
        
        print("=" * 60)
        print("DOCKER HOST NAMES UPDATED")
        print("=" * 60)
        print("Removed (Manager) and (Worker) suffixes from host names")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(update_host_names())