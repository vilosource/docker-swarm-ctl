import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.docker_host import DockerHost
from app.models.user import User
from app.services.docker_service import DockerServiceFactory
from sqlalchemy import select
import docker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_hosts():
    """Test connectivity to all configured hosts"""
    async with AsyncSessionLocal() as session:
        # Get admin user
        result = await session.execute(
            select(User).where(User.role == "admin").limit(1)
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            logger.error("No admin user found")
            return
        
        # Get all hosts
        result = await session.execute(
            select(DockerHost).where(DockerHost.is_active == True)
        )
        hosts = result.scalars().all()
        
        print("=" * 60)
        print("TESTING DOCKER HOST CONNECTIVITY")
        print("=" * 60)
        
        for host in hosts:
            print(f"\nHost: {host.name}")
            print(f"  URL: {host.host_url}")
            print(f"  Type: {host.host_type}")
            
            try:
                # Test direct connection
                client = docker.DockerClient(base_url=host.host_url)
                info = client.info()
                
                print(f"  ✅ Connected successfully!")
                print(f"  Docker Version: {info.get('ServerVersion', 'N/A')}")
                print(f"  Containers: {info.get('Containers', 0)}")
                print(f"  Images: {info.get('Images', 0)}")
                
                if host.host_type in ["swarm_manager", "swarm_worker"]:
                    swarm_info = info.get('Swarm', {})
                    print(f"  Swarm Node ID: {swarm_info.get('NodeID', 'N/A')}")
                    print(f"  Swarm Role: {swarm_info.get('LocalNodeState', 'N/A')}")
                
                # List containers on this host
                containers = client.containers.list(all=True)
                if containers:
                    print(f"  Containers on this host:")
                    for container in containers[:5]:  # Show first 5
                        print(f"    - {container.name} ({container.status})")
                    if len(containers) > 5:
                        print(f"    ... and {len(containers) - 5} more")
                
                client.close()
                
            except Exception as e:
                print(f"  ❌ Connection failed: {str(e)}")
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_hosts())