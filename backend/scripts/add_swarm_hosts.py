import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.docker_host import DockerHost
from app.core.config import settings
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_swarm_hosts():
    """Add Docker Swarm hosts to the database"""
    async with AsyncSessionLocal() as session:
        # Define the hosts
        hosts = [
            {
                "name": "docker-2 (Manager)",
                "description": "Swarm Manager Node",
                "connection_type": "tcp",
                "host_url": "tcp://docker-2.lab.viloforge.com:2375",
                "host_type": "swarm_manager",
                "is_active": True,
                "is_default": True
            },
            {
                "name": "docker-3 (Worker)",
                "description": "Swarm Worker Node 1",
                "connection_type": "tcp",
                "host_url": "tcp://docker-3.lab.viloforge.com:2375",
                "host_type": "swarm_worker",
                "is_active": True,
                "is_default": False
            },
            {
                "name": "docker-4 (Worker)",
                "description": "Swarm Worker Node 2",
                "connection_type": "tcp",
                "host_url": "tcp://docker-4.lab.viloforge.com:2375",
                "host_type": "swarm_worker",
                "is_active": True,
                "is_default": False
            }
        ]
        
        for host_data in hosts:
            # Check if host already exists
            result = await session.execute(
                select(DockerHost).where(DockerHost.name == host_data["name"])
            )
            existing_host = result.scalar_one_or_none()
            
            if not existing_host:
                host = DockerHost(**host_data)
                session.add(host)
                logger.info(f"Added host: {host_data['name']}")
            else:
                logger.info(f"Host already exists: {host_data['name']}")
        
        await session.commit()
        
        print("=" * 60)
        print("DOCKER SWARM HOSTS ADDED")
        print("=" * 60)
        print("Hosts configured:")
        print("  - docker-2 (Manager) - tcp://docker-2.lab.viloforge.com:2375")
        print("  - docker-3 (Worker) - tcp://docker-3.lab.optiscangroup.com:2375")
        print("  - docker-4 (Worker) - tcp://docker-4.lab.optiscangroup.com:2375")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(add_swarm_hosts())