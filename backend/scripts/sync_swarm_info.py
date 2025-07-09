#!/usr/bin/env python3
"""
Sync swarm information for existing hosts
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.docker_host import DockerHost, HostType
from app.services.docker_connection_manager import get_docker_connection_manager
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_swarm_info():
    """Sync swarm information for all hosts"""
    async with AsyncSessionLocal() as db:
        # Get admin user for connection manager
        from app.models.user import User
        admin_stmt = select(User).where(User.role == "admin").limit(1)
        admin_result = await db.execute(admin_stmt)
        admin_user = admin_result.scalar_one_or_none()
        
        if not admin_user:
            print("❌ No admin user found - cannot connect to Docker hosts")
            return
        
        connection_manager = get_docker_connection_manager()
        
        # Get all active hosts
        stmt = select(DockerHost).where(DockerHost.is_active == True)
        result = await db.execute(stmt)
        hosts = result.scalars().all()
        
        print(f"Found {len(hosts)} active hosts")
        
        for host in hosts:
            try:
                print(f"\n🔍 Checking host: {host.name} ({host.id})")
                
                # Try to get swarm info
                try:
                    client = await connection_manager.get_client(str(host.id), admin_user, db)
                    swarm_info = await asyncio.to_thread(lambda: client.swarm.attrs)
                    print(f"  ✅ Swarm info retrieved: {swarm_info.get('ID', 'N/A')[:12]}")
                    
                    # Update host with swarm info
                    host.swarm_id = swarm_info.get("ID")
                    
                    # Get node info to determine role
                    try:
                        # Get current node info
                        node_list = await asyncio.to_thread(client.nodes.list)
                        for node in node_list:
                            node_attrs = await asyncio.to_thread(lambda: node.attrs)
                            if node_attrs.get("Self"):
                                spec = node_attrs.get("Spec", {})
                                manager_status = node_attrs.get("ManagerStatus", {})
                                
                                if spec.get("Role") == "manager":
                                    host.host_type = HostType.swarm_manager
                                    host.is_leader = manager_status.get("Leader", False)
                                else:
                                    host.host_type = HostType.swarm_worker
                                    host.is_leader = False
                                
                                print(f"  📋 Role: {spec.get('Role')}, Leader: {host.is_leader}")
                                break
                    except Exception as e:
                        print(f"  ⚠️  Could not get node info: {e}")
                    
                    # Set cluster name if not already set
                    if not host.cluster_name:
                        if host.host_type == HostType.swarm_manager:
                            # Generate cluster name from swarm ID
                            cluster_name = f"cluster-{swarm_info.get('ID', 'unknown')[:8]}"
                            host.cluster_name = cluster_name
                            print(f"  🏷️  Set cluster name: {cluster_name}")
                        else:
                            # For workers, try to get cluster name from managers
                            manager_stmt = select(DockerHost).where(
                                DockerHost.swarm_id == host.swarm_id,
                                DockerHost.host_type == HostType.swarm_manager,
                                DockerHost.cluster_name != None
                            ).limit(1)
                            manager_result = await db.execute(manager_stmt)
                            manager_host = manager_result.scalar_one_or_none()
                            if manager_host:
                                host.cluster_name = manager_host.cluster_name
                                print(f"  🏷️  Got cluster name from manager: {host.cluster_name}")
                    
                    print(f"  💾 Updated swarm info for {host.name}")
                    
                except Exception as e:
                    print(f"  ❌ Host {host.name} is not part of a swarm or error: {e}")
                    # Clear swarm info if host is not in a swarm
                    if host.swarm_id:
                        host.swarm_id = None
                        host.cluster_name = None
                        host.host_type = HostType.standalone
                        host.is_leader = False
                        print(f"  🧹 Cleared swarm info for {host.name}")
                    
            except Exception as e:
                print(f"  ❌ Error processing host {host.name}: {e}")
                continue
        
        await db.commit()
        print(f"\n✅ Sync completed for {len(hosts)} hosts")


if __name__ == "__main__":
    asyncio.run(sync_swarm_info())