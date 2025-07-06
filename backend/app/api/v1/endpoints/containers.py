from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.config import settings
from app.schemas.container import ContainerCreate, ContainerResponse, ContainerStats, ContainerInspect
from app.services.docker_service import (
    IDockerService, DockerServiceFactory, ContainerData
)
from app.services.audit import AuditService
from app.models.user import User
from app.core.exceptions import DockerOperationError, AuthorizationError
from app.core.feature_flags import FeatureFlag, is_feature_enabled
from app.services.container_stats_calculator import calculate_container_stats
from app.api.decorators import audit_operation, handle_docker_errors


router = APIRouter()


def format_container(container_data: ContainerData) -> ContainerResponse:
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


async def get_docker_service_dep(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> IDockerService:
    """Dependency to get Docker service instance"""
    # Check if multi-host is enabled via settings or feature flag
    multi_host_enabled = getattr(settings, 'multi_host_enabled', True)
    return DockerServiceFactory.create(current_user, db, multi_host_enabled)


@router.get("/", response_model=List[ContainerResponse])
async def list_containers(
    all: bool = Query(False, description="Show all containers (default shows just running)"),
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """List containers from specified or default Docker host"""
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid filters format")
    
    try:
        containers = await docker_service.list_containers(
            all=all,
            filters=filter_dict,
            host_id=host_id
        )
        return [format_container(c) for c in containers]
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DockerOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=ContainerResponse)
async def create_container(
    request: Request,
    config: ContainerCreate,
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """Create a new container on specified or default Docker host"""
    # Build container configuration
    container_config = {
        "image": config.image,
        "detach": True
    }
    
    if config.name:
        container_config["name"] = config.name
    if config.command:
        container_config["command"] = config.command
    if config.environment:
        container_config["environment"] = config.environment
    if config.ports:
        container_config["ports"] = config.ports
    if config.volumes:
        container_config["volumes"] = config.volumes
    if config.labels:
        container_config["labels"] = config.labels
    if config.restart_policy:
        container_config["restart_policy"] = {"Name": config.restart_policy}
    
    try:
        container_data = await docker_service.create_container(
            config=container_config,
            host_id=host_id
        )
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.create",
            resource_type="container",
            resource_id=container_data.id,
            host_id=container_data.host_id,
            details={
                "image": config.image,
                "name": config.name,
                "command": config.command
            },
            request=request
        )
        
        return format_container(container_data)
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DockerOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{container_id}", response_model=ContainerResponse)
async def get_container(
    container_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """Get container details"""
    try:
        container_data = await docker_service.get_container(
            container_id=container_id,
            host_id=host_id
        )
        return format_container(container_data)
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DockerOperationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{container_id}/inspect", response_model=ContainerInspect)
async def inspect_container(
    container_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """Get detailed container inspection data"""
    try:
        attrs = await docker_service.inspect_container(
            container_id=container_id,
            host_id=host_id
        )
        
        # Extract environment variables from Config
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
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DockerOperationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{container_id}/start")
async def start_container(
    request: Request,
    container_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """Start a stopped container"""
    try:
        await docker_service.start_container(
            container_id=container_id,
            host_id=host_id
        )
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.start",
            resource_type="container",
            resource_id=container_id,
            host_id=host_id,
            request=request
        )
        
        return {"message": f"Container {container_id} started"}
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DockerOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{container_id}/stop")
async def stop_container(
    request: Request,
    container_id: str,
    timeout: int = Query(10, description="Timeout in seconds"),
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """Stop a running container"""
    try:
        await docker_service.stop_container(
            container_id=container_id,
            timeout=timeout,
            host_id=host_id
        )
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.stop",
            resource_type="container",
            resource_id=container_id,
            host_id=host_id,
            request=request
        )
        
        return {"message": f"Container {container_id} stopped"}
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DockerOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{container_id}/restart")
async def restart_container(
    request: Request,
    container_id: str,
    timeout: int = Query(10, description="Timeout in seconds"),
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """Restart a container"""
    try:
        await docker_service.restart_container(
            container_id=container_id,
            timeout=timeout,
            host_id=host_id
        )
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.restart",
            resource_type="container",
            resource_id=container_id,
            host_id=host_id,
            request=request
        )
        
        return {"message": f"Container {container_id} restarted"}
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DockerOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{container_id}")
async def remove_container(
    request: Request,
    container_id: str,
    force: bool = Query(False, description="Force removal"),
    volumes: bool = Query(False, description="Remove associated volumes"),
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """Remove a container"""
    try:
        await docker_service.remove_container(
            container_id=container_id,
            force=force,
            volumes=volumes,
            host_id=host_id
        )
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.delete",
            resource_type="container",
            resource_id=container_id,
            host_id=host_id,
            details={"force": force, "volumes": volumes},
            request=request
        )
        
        return {"message": f"Container {container_id} removed"}
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DockerOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{container_id}/logs")
async def get_container_logs(
    container_id: str,
    lines: int = Query(100, description="Number of lines to return"),
    timestamps: bool = Query(False, description="Add timestamps to logs"),
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """Get container logs"""
    try:
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
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DockerOperationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{container_id}/stats", response_model=ContainerStats)
@handle_docker_errors()
async def get_container_stats(
    container_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)"),
    docker_service: IDockerService = Depends(get_docker_service_dep)
):
    """Get real-time container resource usage statistics"""
    # Get raw stats from Docker
    raw_stats = await docker_service.get_container_stats(
        container_id=container_id,
        host_id=host_id
    )
    
    # Use new calculator if feature flag is enabled
    if is_feature_enabled(FeatureFlag.USE_CONTAINER_STATS_CALCULATOR):
        return calculate_container_stats(raw_stats)
    
    # Legacy calculation code (will be removed after testing)
    # Calculate CPU percentage
    cpu_delta = raw_stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                raw_stats["precpu_stats"]["cpu_usage"]["total_usage"]
    system_delta = raw_stats["cpu_stats"]["system_cpu_usage"] - \
                  raw_stats["precpu_stats"]["system_cpu_usage"]
    cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
    
    # Memory stats
    memory_usage = raw_stats["memory_stats"]["usage"]
    memory_limit = raw_stats["memory_stats"]["limit"]
    memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0
    
    # Network stats
    network_rx = sum(v["rx_bytes"] for v in raw_stats["networks"].values()) if "networks" in raw_stats else 0
    network_tx = sum(v["tx_bytes"] for v in raw_stats["networks"].values()) if "networks" in raw_stats else 0
    
    # Block I/O stats
    block_read = sum(item["value"] for item in raw_stats["blkio_stats"]["io_service_bytes_recursive"] 
                    if item["op"] == "Read") if "blkio_stats" in raw_stats else 0
    block_write = sum(item["value"] for item in raw_stats["blkio_stats"]["io_service_bytes_recursive"] 
                     if item["op"] == "Write") if "blkio_stats" in raw_stats else 0
    
    return ContainerStats(
        cpu_percent=cpu_percent,
        memory_usage=memory_usage,
        memory_limit=memory_limit,
        memory_percent=memory_percent,
        network_rx=network_rx,
        network_tx=network_tx,
        block_read=block_read,
        block_write=block_write,
        pids=raw_stats["pids_stats"]["current"] if "pids_stats" in raw_stats else 0
    )