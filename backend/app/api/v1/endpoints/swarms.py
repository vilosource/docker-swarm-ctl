"""
Swarm clusters overview endpoints
"""

from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.docker_host import DockerHost, HostType
from app.schemas.swarm import SwarmClusterInfo, SwarmClusterListResponse
from app.services.docker_service import IDockerService, DockerServiceFactory
from app.api.decorators_enhanced import handle_api_errors
from app.core.logging import logger


router = APIRouter()


async def get_docker_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> IDockerService:
    """Dependency to get Docker service instance"""
    return DockerServiceFactory.create(current_user, db, multi_host=True)


@router.get("/", response_model=SwarmClusterListResponse)
@handle_api_errors("list_swarm_clusters")
async def list_swarm_clusters(
    current_user: User = Depends(get_current_active_user),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """List all swarm clusters across all hosts"""
    
    # Get all hosts accessible by the user
    query = select(DockerHost).where(
        DockerHost.is_active == True,
        DockerHost.swarm_id != None
    )
    
    # If not admin, filter by permissions
    if current_user.role != "admin":
        # TODO: Add permission filtering
        pass
    
    result = await db.execute(query)
    swarm_hosts = result.scalars().all()
    
    # Group hosts by swarm_id
    swarm_groups: Dict[str, List[DockerHost]] = {}
    for host in swarm_hosts:
        if host.swarm_id:
            if host.swarm_id not in swarm_groups:
                swarm_groups[host.swarm_id] = []
            swarm_groups[host.swarm_id].append(host)
    
    # Build swarm cluster info for each swarm
    swarm_clusters = []
    
    for swarm_id, hosts in swarm_groups.items():
        # Find the leader/primary manager
        leader_host = next((h for h in hosts if h.is_leader), None)
        if not leader_host:
            # If no leader marked, use first manager
            leader_host = next((h for h in hosts if h.host_type == HostType.swarm_manager), hosts[0])
        
        # Count managers and workers
        manager_count = sum(1 for h in hosts if h.host_type == HostType.swarm_manager)
        worker_count = sum(1 for h in hosts if h.host_type == HostType.swarm_worker)
        
        # Get service count from leader
        service_count = 0
        swarm_created_at = None
        swarm_updated_at = None
        
        try:
            # Get swarm info from leader
            swarm_info = await docker_service.get_swarm_info(str(leader_host.id))
            swarm_created_at = swarm_info.get("CreatedAt")
            swarm_updated_at = swarm_info.get("UpdatedAt")
            
            # Get services count
            services = await docker_service.list_services(str(leader_host.id))
            service_count = len(services)
        except Exception as e:
            logger.warning(f"Failed to get swarm details for {swarm_id}: {e}")
        
        # Build cluster info
        cluster_info = {
            "swarm_id": swarm_id,
            "cluster_name": hosts[0].cluster_name or f"Swarm {swarm_id[:8]}",
            "created_at": swarm_created_at,
            "updated_at": swarm_updated_at,
            "manager_count": manager_count,
            "worker_count": worker_count,
            "total_nodes": len(hosts),
            "service_count": service_count,
            "leader_host": {
                "id": str(leader_host.id),
                "display_name": leader_host.display_name or leader_host.name,
                "url": leader_host.host_url
            },
            "hosts": [
                {
                    "id": str(h.id),
                    "display_name": h.display_name or h.name,
                    "host_type": h.host_type,
                    "is_leader": h.is_leader
                }
                for h in hosts
            ]
        }
        
        swarm_clusters.append(cluster_info)
    
    # Sort by cluster name
    swarm_clusters.sort(key=lambda x: x["cluster_name"])
    
    return SwarmClusterListResponse(
        swarms=swarm_clusters,
        total=len(swarm_clusters)
    )


@router.get("/{swarm_id}", response_model=SwarmClusterInfo)
@handle_api_errors("get_swarm_cluster")
async def get_swarm_cluster(
    swarm_id: str,
    current_user: User = Depends(get_current_active_user),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific swarm cluster"""
    
    # Get all hosts in this swarm
    query = select(DockerHost).where(
        DockerHost.is_active == True,
        DockerHost.swarm_id == swarm_id
    )
    
    result = await db.execute(query)
    hosts = result.scalars().all()
    
    if not hosts:
        raise HTTPException(status_code=404, detail=f"Swarm cluster {swarm_id} not found")
    
    # Find the leader
    leader_host = next((h for h in hosts if h.is_leader), None)
    if not leader_host:
        leader_host = next((h for h in hosts if h.host_type == HostType.swarm_manager), hosts[0])
    
    # Get detailed swarm info from leader
    try:
        # Basic info we can get from database
        manager_count = sum(1 for h in hosts if h.host_type == HostType.swarm_manager)
        worker_count = sum(1 for h in hosts if h.host_type == HostType.swarm_worker)
        
        # Try to get additional info from Docker API
        swarm_created_at = None
        swarm_updated_at = None
        service_count = 0
        ready_nodes = len(hosts)  # Default to all nodes ready
        swarm_spec = {}
        join_tokens = {}
        
        try:
            swarm_info = await docker_service.get_swarm_info(str(leader_host.id))
            swarm_created_at = swarm_info.get("CreatedAt")
            swarm_updated_at = swarm_info.get("UpdatedAt")
            swarm_spec = swarm_info.get("Spec", {})
            join_tokens = swarm_info.get("JoinTokens", {})
        except Exception as e:
            logger.warning(f"Could not get swarm info: {e}")
        
        try:
            services = await docker_service.list_services(str(leader_host.id))
            service_count = len(services)
        except Exception as e:
            logger.warning(f"Could not get services: {e}")
        
        try:
            nodes = await docker_service.list_nodes(str(leader_host.id))
            ready_nodes = sum(1 for n in nodes if n.get("state") == "ready")
        except Exception as e:
            logger.warning(f"Could not get nodes: {e}")
        
        return SwarmClusterInfo(
            swarm_id=swarm_id,
            cluster_name=hosts[0].cluster_name or f"Swarm {swarm_id[:8]}",
            created_at=swarm_created_at,
            updated_at=swarm_updated_at,
            manager_count=manager_count,
            worker_count=worker_count,
            total_nodes=len(hosts),
            ready_nodes=ready_nodes,
            service_count=service_count,
            leader_host={
                "id": str(leader_host.id),
                "display_name": leader_host.display_name or leader_host.name,
                "url": leader_host.host_url
            },
            hosts=[
                {
                    "id": str(h.id),
                    "display_name": h.display_name or h.name,
                    "host_type": h.host_type.value if hasattr(h.host_type, 'value') else str(h.host_type) if h.host_type else None,
                    "is_leader": h.is_leader,
                    "url": h.host_url
                }
                for h in hosts
            ],
            swarm_spec=swarm_spec,
            join_tokens=join_tokens
        )
        
    except Exception as e:
        logger.error(f"Failed to get swarm cluster details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve swarm cluster information")