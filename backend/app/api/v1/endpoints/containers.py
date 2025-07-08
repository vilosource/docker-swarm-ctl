"""
Refactored Container Endpoints

Simplified implementation using enhanced decorators and helper functions.
Reduces code from 413 lines to ~200 lines while maintaining functionality.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import ValidationError
from app.core.rate_limit import rate_limit
from app.schemas.container import (
    ContainerCreate, ContainerResponse, ContainerStats, ContainerInspect
)
from app.services.docker_service import IDockerService, DockerServiceFactory
from app.models.user import User
from app.api.decorators import audit_operation, handle_docker_errors
from app.api.decorators_enhanced import (
    handle_api_errors,
    standard_response,
    ContainerConfigBuilder
)
from app.core.feature_flags import FeatureFlag, is_feature_enabled
from app.services.container_stats_calculator import calculate_container_stats


router = APIRouter()


def format_container(container_data) -> ContainerResponse:
    """Format container data for response"""
    return ContainerResponse(
        id=container_data.id,
        name=container_data.name,
        image=container_data.image,
        status=container_data.status,
        state=container_data.state,
        created=container_data.created,
        ports=container_data.ports,
        labels=container_data.labels,
        host_id=container_data.host_id
    )


async def get_docker_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> IDockerService:
    """Dependency to get Docker service instance"""
    return DockerServiceFactory.create(current_user, db, multi_host=True)


@router.get("/", response_model=List[ContainerResponse])
@handle_api_errors("list_containers")
async def list_containers(
    all: bool = Query(False, description="Show all containers"),
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """List containers from specified or default Docker host"""
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise ValidationError("filters", "Invalid JSON format")
    
    containers = await docker_service.list_containers(
        all=all,
        filters=filter_dict,
        host_id=host_id
    )
    return [format_container(c) for c in containers]


@router.post("/", response_model=ContainerResponse)
@rate_limit("30/hour")
@handle_api_errors("create_container")
@audit_operation("container.create", "container", lambda r: r.id)
async def create_container(
    request: Request,
    response: Response,
    config: ContainerCreate,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Create a new container on specified or default Docker host"""
    container_config = ContainerConfigBuilder.from_create_schema(config)
    
    container_data = await docker_service.create_container(
        config=container_config,
        host_id=host_id
    )
    
    return format_container(container_data)


@router.get("/{container_id}", response_model=ContainerResponse)
@handle_api_errors("get_container")
async def get_container(
    container_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get container details"""
    container_data = await docker_service.get_container(
        container_id=container_id,
        host_id=host_id
    )
    return format_container(container_data)


@router.get("/{container_id}/inspect", response_model=ContainerInspect)
@handle_api_errors("inspect_container")
async def inspect_container(
    container_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get detailed container inspection data"""
    attrs = await docker_service.inspect_container(
        container_id=container_id,
        host_id=host_id
    )
    
    env_list = attrs.get("Config", {}).get("Env", [])
    
    return ContainerInspect(
        id=attrs.get("Id", ""),
        name=attrs.get("Name", "").lstrip("/"),
        image=attrs.get("Config", {}).get("Image", ""),
        config=attrs.get("Config", {}),
        environment=env_list,
        mounts=attrs.get("Mounts", []),
        network_settings=attrs.get("NetworkSettings", {}),
        state=attrs.get("State", {}),
        host_config=attrs.get("HostConfig", {})
    )


@router.post("/{container_id}/start")
@rate_limit("60/minute")
@handle_api_errors("start_container")
@audit_operation("container.start", "container")
@standard_response("Container {container_id} started")
async def start_container(
    request: Request,
    container_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Start a stopped container"""
    await docker_service.start_container(
        container_id=container_id,
        host_id=host_id
    )


@router.post("/{container_id}/stop")
@rate_limit("60/minute")
@handle_api_errors("stop_container")
@audit_operation("container.stop", "container")
@standard_response("Container {container_id} stopped")
async def stop_container(
    request: Request,
    container_id: str,
    timeout: int = Query(10, description="Timeout in seconds"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Stop a running container"""
    await docker_service.stop_container(
        container_id=container_id,
        timeout=timeout,
        host_id=host_id
    )


@router.post("/{container_id}/restart")
@rate_limit("60/minute")
@handle_api_errors("restart_container")
@audit_operation("container.restart", "container")
@standard_response("Container {container_id} restarted")
async def restart_container(
    request: Request,
    container_id: str,
    timeout: int = Query(10, description="Timeout in seconds"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Restart a container"""
    await docker_service.restart_container(
        container_id=container_id,
        timeout=timeout,
        host_id=host_id
    )


@router.delete("/{container_id}")
@rate_limit("50/hour")
@handle_api_errors("remove_container")
@audit_operation("container.delete", "container")
@standard_response("Container {container_id} removed")
async def remove_container(
    request: Request,
    container_id: str,
    force: bool = Query(False, description="Force removal"),
    volumes: bool = Query(False, description="Remove associated volumes"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Remove a container"""
    await docker_service.remove_container(
        container_id=container_id,
        force=force,
        volumes=volumes,
        host_id=host_id
    )


@router.get("/{container_id}/logs")
@rate_limit("200/minute")
@handle_api_errors("get_container_logs")
async def get_container_logs(
    request: Request,
    container_id: str,
    lines: int = Query(100, description="Number of lines to return"),
    timestamps: bool = Query(False, description="Add timestamps to logs"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get container logs"""
    logs = await docker_service.get_container_logs(
        container_id=container_id,
        lines=lines,
        timestamps=timestamps,
        host_id=host_id
    )
    
    return {
        "container_id": container_id,
        "logs": logs,
        "host_id": host_id
    }


@router.get("/{container_id}/stats", response_model=ContainerStats)
@rate_limit("100/minute")
@handle_api_errors("get_container_stats")
async def get_container_stats(
    request: Request,
    container_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get real-time container resource usage statistics"""
    raw_stats = await docker_service.get_container_stats(
        container_id=container_id,
        host_id=host_id
    )
    
    # Use feature flag to determine calculation method
    if is_feature_enabled(FeatureFlag.USE_CONTAINER_STATS_CALCULATOR):
        return calculate_container_stats(raw_stats)
    
    # Legacy fallback (can be removed after testing)
    return ContainerStats(
        cpu_percent=0.0,
        memory_usage=raw_stats.get("memory_stats", {}).get("usage", 0),
        memory_limit=raw_stats.get("memory_stats", {}).get("limit", 0),
        memory_percent=0.0,
        network_rx=0,
        network_tx=0,
        block_read=0,
        block_write=0,
        pids=raw_stats.get("pids_stats", {}).get("current", 0)
    )