#!/usr/bin/env python3
"""
Fix swarm database information based on actual Docker swarm status
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


async def fix_swarm_data():
    """Fix swarm information based on actual Docker reality"""
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
        
        # First, clear all swarm information to start fresh
        print("\n🧹 Clearing all swarm information...")
        for host in hosts:
            host.swarm_id = None
            host.cluster_name = None
            host.is_leader = False
            # Keep host_type as is for now - we'll update it based on actual status
        
        await db.commit()
        print("✅ Cleared all swarm data")
        
        # Now check each host and find the real swarm
        real_swarm_id = None
        manager_host = None
        
        print("\n🔍 Finding the real swarm...")
        # Check docker-2 first since we know it's the main manager
        priority_hosts = ["docker-2", "docker-3", "docker-4"]
        
        # Sort hosts to check priority hosts first
        sorted_hosts = []
        for priority_name in priority_hosts:
            for host in hosts:
                if priority_name in host.name:
                    sorted_hosts.append(host)
                    break
        # Add remaining hosts
        for host in hosts:
            if host not in sorted_hosts:
                sorted_hosts.append(host)
        
        for host in sorted_hosts:
            try:
                print(f"  Checking {host.name}...")
                client = await connection_manager.get_client(str(host.id), admin_user, db)
                
                # Try to get swarm info
                try:
                    swarm_info = await asyncio.to_thread(lambda: client.swarm.attrs)
                    if swarm_info and swarm_info.get('ID'):
                        print(f"    ✅ Found swarm ID: {swarm_info.get('ID')[:12]}")
                        
                        # Try to get nodes (only works on managers)
                        try:
                            node_list = await asyncio.to_thread(client.nodes.list)
                            if node_list:
                                print(f"    🎯 This is a MANAGER with {len(node_list)} nodes!")
                                real_swarm_id = swarm_info.get('ID')
                                manager_host = host
                                break
                        except:
                            print(f"    ℹ️  This is a worker node")
                            # Store the swarm ID but continue looking for manager
                            if not real_swarm_id:
                                real_swarm_id = swarm_info.get('ID')
                            
                except Exception as e:
                    print(f"    ❌ Not in a swarm: {e}")
                    
            except Exception as e:
                print(f"    ❌ Connection failed: {e}")
                continue
        
        if not real_swarm_id:
            print("\n❌ No active swarm found!")
            return
            
        print(f"\n🎯 Real swarm ID: {real_swarm_id}")
        print(f"🏅 Manager host: {manager_host.name if manager_host else 'Unknown'}")
        
        # Now properly assign swarm membership
        if manager_host:
            client = await connection_manager.get_client(str(manager_host.id), admin_user, db)
            
            try:
                # Get all nodes from the manager
                node_list = await asyncio.to_thread(client.nodes.list)
                swarm_info = await asyncio.to_thread(lambda: client.swarm.attrs)
                
                print(f"\n🐝 Processing {len(node_list)} swarm nodes:")
                
                # Create a mapping of node hostnames to our database hosts
                hostname_to_host = {}
                for host in hosts:
                    # Try different hostname matching strategies
                    possible_names = [
                        host.name,
                        host.display_name,
                        host.name.split('.')[0],  # Short hostname
                        host.host_url.split('://')[1].split(':')[0] if '://' in host.host_url else None
                    ]
                    for name in possible_names:
                        if name:
                            hostname_to_host[name.lower()] = host
                
                for node in node_list:
                    node_attrs = await asyncio.to_thread(lambda: node.attrs)
                    hostname = node_attrs.get('Description', {}).get('Hostname', '')
                    role = node_attrs.get('Spec', {}).get('Role', 'worker')
                    state = node_attrs.get('Status', {}).get('State', 'unknown')
                    is_leader = node_attrs.get('ManagerStatus', {}).get('Leader', False) if role == 'manager' else False
                    
                    print(f"  🔍 Node: {hostname} - {role.upper()} - {state.upper()}")
                    
                    # Find matching host in our database
                    matching_host = None
                    for hostname_variant in [hostname.lower(), hostname.lower().split('.')[0]]:
                        if hostname_variant in hostname_to_host:
                            matching_host = hostname_to_host[hostname_variant]
                            break
                    
                    if matching_host:
                        print(f"    ✅ Matched to database host: {matching_host.name}")
                        matching_host.swarm_id = real_swarm_id
                        matching_host.cluster_name = "Production Swarm"  # Give it a proper name
                        matching_host.host_type = HostType.swarm_manager if role == 'manager' else HostType.swarm_worker
                        matching_host.is_leader = is_leader
                    else:
                        print(f"    ⚠️  No matching database host found for {hostname}")
                
                await db.commit()
                print(f"\n✅ Successfully updated swarm membership!")
                
            except Exception as e:
                print(f"❌ Failed to process swarm nodes: {e}")
        
        # Final verification
        print(f"\n📊 Final verification:")
        stmt = select(DockerHost).where(DockerHost.swarm_id == real_swarm_id)
        result = await db.execute(stmt)
        swarm_hosts = result.scalars().all()
        
        managers = [h for h in swarm_hosts if h.host_type == HostType.swarm_manager]
        workers = [h for h in swarm_hosts if h.host_type == HostType.swarm_worker]
        leader = next((h for h in managers if h.is_leader), None)
        
        print(f"  🏅 Swarm: {real_swarm_id[:12]}")
        print(f"  👥 Total nodes: {len(swarm_hosts)}")
        print(f"  🛡️  Managers: {len(managers)}")
        print(f"  ⚡ Workers: {len(workers)}")
        print(f"  👑 Leader: {leader.name if leader else 'None'}")
        
        for host in swarm_hosts:
            role = "MANAGER" if host.host_type == HostType.swarm_manager else "WORKER"
            leader_mark = " (LEADER)" if host.is_leader else ""
            print(f"    - {host.name}: {role}{leader_mark}")


if __name__ == "__main__":
    asyncio.run(fix_swarm_data())