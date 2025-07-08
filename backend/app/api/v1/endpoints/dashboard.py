"""
Dashboard endpoints for multi-host aggregated views
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import docker
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.core.logging import logger
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.models.docker_host import DockerHost
from app.models import HostStatus
from app.schemas.dashboard import (
    DashboardResponse, HostOverview, ResourceStats, 
    HostSummary, HostStats
)
from app.services.docker_service import IDockerService, DockerServiceFactory
from app.api.decorators_enhanced import handle_api_errors


router = APIRouter()


async def get_host_stats(docker_service: IDockerService, host: DockerHost) -> Optional[HostStats]:
    """Get statistics for a single host"""
    try:
        # Get Docker info for the host
        info = await docker_service.get_system_info(host_id=str(host.id))
        
        return HostStats(
            containers=info.get("Containers", 0),
            containers_running=info.get("ContainersRunning", 0),
            containers_stopped=info.get("ContainersStopped", 0),
            containers_paused=info.get("ContainersPaused", 0),
            images=info.get("Images", 0),
            docker_version=info.get("ServerVersion"),
            os_type=info.get("OSType"),
            architecture=info.get("Architecture"),
            memory_total=info.get("MemTotal"),
            cpu_count=info.get("NCPU")
        )
    except Exception as e:
        logger.error(f"Error getting stats for host {host.name}: {e}")
        # The circuit breaker is handled at the DockerOperationExecutor level
        return None


@router.get("/", response_model=DashboardResponse)
@handle_api_errors("dashboard")
async def get_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(True, description="Only include active hosts")
):
    """Get dashboard data with aggregated multi-host statistics"""
    
    # Get Docker service
    docker_service = DockerServiceFactory.create(current_user, db, multi_host=True)
    
    # Query all hosts
    query = select(DockerHost)
    if active_only:
        query = query.where(DockerHost.is_active == True)
    
    result = await db.execute(query)
    hosts = result.scalars().all()
    
    # Initialize response structure
    host_overview = HostOverview(total=len(hosts))
    resource_stats = ResourceStats()
    host_details = []
    
    # Count hosts by status
    for host in hosts:
        if host.status == HostStatus.healthy:
            host_overview.healthy += 1
        elif host.status == HostStatus.unhealthy:
            host_overview.unhealthy += 1
        elif host.status == HostStatus.unreachable:
            host_overview.unreachable += 1
        elif host.status == HostStatus.pending:
            host_overview.pending += 1
    
    # Get stats for each host in parallel
    async def process_host(host: DockerHost):
        stats = await get_host_stats(docker_service, host)
        
        # Create host summary
        host_summary = HostSummary(
            id=host.id,
            name=host.name,
            display_name=host.display_name,
            status=host.status,
            last_health_check=host.last_health_check,
            is_default=host.is_default,
            stats=stats or HostStats()  # Use empty stats if fetch failed
        )
        
        # Aggregate stats if available
        if stats and host.status == HostStatus.healthy:
            resource_stats.containers["total"] += stats.containers
            resource_stats.containers["running"] += stats.containers_running
            resource_stats.containers["stopped"] += stats.containers_stopped
            resource_stats.containers["paused"] += stats.containers_paused
            resource_stats.images["total"] += stats.images
        
        return host_summary
    
    # Process all hosts concurrently
    host_details = await asyncio.gather(*[process_host(host) for host in hosts])
    
    # Sort host details by name
    host_details.sort(key=lambda h: h.name)
    
    # Get volume and network stats for healthy hosts (if needed)
    # This is a simplified version - could be expanded
    try:
        # For now, we'll get this from the default host if available
        default_host = next((h for h in hosts if h.is_default and h.status == HostStatus.healthy), None)
        if default_host:
            df_data = await docker_service.get_disk_usage(host_id=str(default_host.id))
            if df_data:
                resource_stats.volumes["total"] = len(df_data.get("Volumes", []))
                resource_stats.volumes["size"] = sum(v.get("Size", 0) for v in df_data.get("Volumes", []))
                resource_stats.networks["total"] = len(df_data.get("Networks", []))
    except Exception as e:
        logger.warning(f"Could not get volume/network stats: {e}")
    
    return DashboardResponse(
        hosts=host_overview,
        resources=resource_stats,
        host_details=host_details
    )


@router.get("/refresh/{host_id}")
@rate_limit("60/minute")
@handle_api_errors("refresh_host_stats")
async def refresh_host_stats(
    request: Request,
    host_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Refresh statistics for a specific host"""
    # Get the host
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == host_id)
    )
    host = result.scalar_one_or_none()
    
    if not host:
        raise ValueError(f"Host {host_id} not found")
    
    # Get Docker service and refresh stats
    docker_service = DockerServiceFactory.create(current_user, db, multi_host=True)
    stats = await get_host_stats(docker_service, host)
    
    # Update host health check time
    host.last_health_check = datetime.utcnow()
    if stats:
        host.status = HostStatus.healthy
    else:
        host.status = HostStatus.unreachable
    
    await db.commit()
    
    return {
        "host_id": host_id,
        "status": host.status,
        "stats": stats
    }