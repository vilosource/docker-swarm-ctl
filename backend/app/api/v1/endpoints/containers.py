from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.schemas.container import ContainerCreate, ContainerResponse, ContainerStats, ContainerInspect
from app.services.docker_client import get_docker_client, handle_docker_errors
from app.services.audit import AuditService
from app.models.user import User


router = APIRouter()


def format_container(container) -> ContainerResponse:
    return ContainerResponse(
        id=container.id[:12],
        name=container.name,
        image=container.image.tags[0] if container.image.tags else container.image.id,
        status=container.status,
        state=container.attrs["State"]["Status"],
        created=container.attrs["Created"],
        ports=container.attrs["NetworkSettings"]["Ports"] or {},
        labels=container.labels or {}
    )


@router.get("/", response_model=List[ContainerResponse])
async def list_containers(
    all: bool = Query(False, description="Show all containers (default shows just running)"),
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    
    kwargs = {"all": all}
    if filters:
        import json
        try:
            kwargs["filters"] = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid filters format")
    
    containers = client.containers.list(**kwargs)
    return [format_container(c) for c in containers]


@router.post("/", response_model=ContainerResponse)
async def create_container(
    request: Request,
    config: ContainerCreate,
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db)
):
    client = get_docker_client()
    
    # Build container configuration
    kwargs = {
        "image": config.image,
        "detach": True
    }
    
    if config.name:
        kwargs["name"] = config.name
    if config.command:
        kwargs["command"] = config.command
    if config.environment:
        kwargs["environment"] = config.environment
    if config.ports:
        kwargs["ports"] = config.ports
    if config.volumes:
        kwargs["volumes"] = config.volumes
    if config.labels:
        kwargs["labels"] = config.labels
    if config.restart_policy:
        kwargs["restart_policy"] = {"Name": config.restart_policy}
    
    try:
        container = client.containers.run(**kwargs)
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.create",
            resource_type="container",
            resource_id=container.id[:12],
            details={
                "image": config.image,
                "name": config.name,
                "command": config.command
            },
            request=request
        )
        
        return format_container(container)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{container_id}", response_model=ContainerResponse)
async def get_container(
    container_id: str,
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        return format_container(container)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Container {container_id} not found")


@router.get("/{container_id}/inspect", response_model=ContainerInspect)
async def inspect_container(
    container_id: str,
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        attrs = container.attrs
        
        # Extract environment variables from Config
        env_list = attrs.get("Config", {}).get("Env", [])
        
        return ContainerInspect(
            id=container.id,
            name=container.name,
            image=attrs.get("Config", {}).get("Image", ""),
            config=attrs.get("Config", {}),
            environment=env_list,
            mounts=attrs.get("Mounts", []),
            network_settings=attrs.get("NetworkSettings", {}),
            state=attrs.get("State", {}),
            host_config=attrs.get("HostConfig", {})
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Container {container_id} not found")


@router.post("/{container_id}/start")
async def start_container(
    request: Request,
    container_id: str,
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db)
):
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        container.start()
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.start",
            resource_type="container",
            resource_id=container_id,
            request=request
        )
        
        return {"message": f"Container {container_id} started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{container_id}/stop")
async def stop_container(
    request: Request,
    container_id: str,
    timeout: int = Query(10, description="Timeout in seconds"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db)
):
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=timeout)
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.stop",
            resource_type="container",
            resource_id=container_id,
            request=request
        )
        
        return {"message": f"Container {container_id} stopped"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{container_id}/restart")
async def restart_container(
    request: Request,
    container_id: str,
    timeout: int = Query(10, description="Timeout in seconds"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db)
):
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        container.restart(timeout=timeout)
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.restart",
            resource_type="container",
            resource_id=container_id,
            request=request
        )
        
        return {"message": f"Container {container_id} restarted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{container_id}")
async def remove_container(
    request: Request,
    container_id: str,
    force: bool = Query(False, description="Force removal"),
    volumes: bool = Query(False, description="Remove associated volumes"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db)
):
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        container.remove(force=force, v=volumes)
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="container.delete",
            resource_type="container",
            resource_id=container_id,
            details={"force": force, "volumes": volumes},
            request=request
        )
        
        return {"message": f"Container {container_id} removed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{container_id}/logs")
async def get_container_logs(
    container_id: str,
    lines: int = Query(100, description="Number of lines to return"),
    timestamps: bool = Query(False, description="Add timestamps to logs"),
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        logs = container.logs(
            tail=lines,
            timestamps=timestamps,
            stream=False
        )
        
        return {
            "container_id": container_id,
            "logs": logs.decode("utf-8")
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{container_id}/stats", response_model=ContainerStats)
async def get_container_stats(
    container_id: str,
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        stats = container.stats(stream=False)
        
        # Calculate CPU percentage
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                    stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                      stats["precpu_stats"]["system_cpu_usage"]
        cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
        
        # Memory stats
        memory_usage = stats["memory_stats"]["usage"]
        memory_limit = stats["memory_stats"]["limit"]
        memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0
        
        # Network stats
        network_rx = sum(v["rx_bytes"] for v in stats["networks"].values()) if "networks" in stats else 0
        network_tx = sum(v["tx_bytes"] for v in stats["networks"].values()) if "networks" in stats else 0
        
        # Block I/O stats
        block_read = sum(item["value"] for item in stats["blkio_stats"]["io_service_bytes_recursive"] 
                        if item["op"] == "Read") if "blkio_stats" in stats else 0
        block_write = sum(item["value"] for item in stats["blkio_stats"]["io_service_bytes_recursive"] 
                         if item["op"] == "Write") if "blkio_stats" in stats else 0
        
        return ContainerStats(
            cpu_percent=cpu_percent,
            memory_usage=memory_usage,
            memory_limit=memory_limit,
            memory_percent=memory_percent,
            network_rx=network_rx,
            network_tx=network_tx,
            block_read=block_read,
            block_write=block_write,
            pids=stats["pids_stats"]["current"] if "pids_stats" in stats else 0
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))