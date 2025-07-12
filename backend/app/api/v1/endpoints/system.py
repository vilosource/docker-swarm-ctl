from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role, require_admin
from app.core.rate_limit import rate_limit
from app.services.docker_client import get_docker_client
from app.services.docker_service import IDockerService, DockerServiceFactory
from app.services.audit import AuditService
from app.models.user import User
from app.core.feature_flags import get_all_feature_flags
from app.services.circuit_breaker import get_circuit_breaker_manager


router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "docker-control-platform"}


@router.get("/feature-flags", response_model=Dict[str, bool])
async def get_feature_flags(
    current_user: User = Depends(require_admin)
):
    """Get current feature flags status (admin only)"""
    return get_all_feature_flags()


@router.get("/circuit-breakers")
async def get_circuit_breakers(
    current_user: User = Depends(require_admin)
):
    """Get circuit breaker status for all hosts (admin only)"""
    manager = get_circuit_breaker_manager()
    return manager.get_all_status()


@router.post("/circuit-breakers/{breaker_name}/reset")
@rate_limit("10/minute")
async def reset_circuit_breaker(
    request: Request,
    breaker_name: str,
    current_user: User = Depends(require_admin)
):
    """Reset a specific circuit breaker (admin only)"""
    manager = get_circuit_breaker_manager()
    await manager.reset(breaker_name)
    return {"message": f"Circuit breaker '{breaker_name}' has been reset"}


@router.get("/info")
async def get_system_info(
    host_id: Optional[str] = Query(None, description="Docker host ID (defaults to local/default host)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Support both single-host (legacy) and multi-host modes
    if host_id:
        # Multi-host mode
        docker_service = DockerServiceFactory.create(current_user, db, multi_host=True)
        try:
            info = await docker_service.get_system_info(host_id=host_id)
            version = await docker_service.get_version(host_id=host_id)
            
            return {
                "host_id": host_id,
                "docker_version": version.get("Version"),
                "api_version": version.get("ApiVersion"),
                "os": info.get("OperatingSystem"),
                "kernel_version": info.get("KernelVersion"),
                "containers": info.get("Containers"),
                "containers_running": info.get("ContainersRunning"),
                "containers_paused": info.get("ContainersPaused"),
                "containers_stopped": info.get("ContainersStopped"),
                "images": info.get("Images"),
                "driver": info.get("Driver"),
                "memory_total": info.get("MemTotal"),
                "cpu_count": info.get("NCPU"),
                "architecture": info.get("Architecture"),
                "registry_config": info.get("RegistryConfig", {})
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Legacy single-host mode
        client = get_docker_client()
        try:
            info = client.info()
            version = client.version()
            
            return {
                "docker_version": version.get("Version"),
                "api_version": version.get("ApiVersion"),
                "os": info.get("OperatingSystem"),
                "kernel_version": info.get("KernelVersion"),
                "containers": info.get("Containers"),
                "containers_running": info.get("ContainersRunning"),
                "containers_paused": info.get("ContainersPaused"),
                "containers_stopped": info.get("ContainersStopped"),
                "images": info.get("Images"),
                "driver": info.get("Driver"),
                "memory_total": info.get("MemTotal"),
                "cpu_count": info.get("NCPU"),
                "architecture": info.get("Architecture"),
                "registry_config": info.get("RegistryConfig", {})
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/version")
async def get_version(
    host_id: Optional[str] = Query(None, description="Docker host ID (defaults to local/default host)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if host_id:
        # Multi-host mode
        docker_service = DockerServiceFactory.create(current_user, db, multi_host=True)
        try:
            return await docker_service.get_version(host_id=host_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Legacy single-host mode
        client = get_docker_client()
        try:
            return client.version()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/prune")
@rate_limit("5/hour")
async def system_prune(
    request: Request,
    volumes: bool = False,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    client = get_docker_client()
    
    try:
        result = client.system.prune(volumes=volumes)
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="system.prune",
            details={
                "volumes": volumes,
                "result": result
            },
            request=request
        )
        
        return {
            "message": "System prune completed",
            "space_reclaimed": result.get("SpaceReclaimed", 0),
            "deleted": {
                "containers": result.get("ContainersDeleted", []),
                "images": result.get("ImagesDeleted", []),
                "volumes": result.get("VolumesDeleted", []) if volumes else [],
                "networks": result.get("NetworksDeleted", [])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/df")
@rate_limit("60/minute")
async def disk_usage(
    request: Request,
    host_id: Optional[str] = Query(None, description="Docker host ID (defaults to local/default host)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from fastapi.responses import JSONResponse
    if host_id:
        # Multi-host mode
        docker_service = DockerServiceFactory.create(current_user, db, multi_host=True)
        try:
            df = await docker_service.get_disk_usage(host_id=host_id)
            
            return JSONResponse(content={
                "host_id": host_id,
                "layers_size": df.get("LayersSize", 0),
                "images": {
                    "count": len(df.get("Images", [])),
                    "size": sum(img.get("Size", 0) for img in df.get("Images", [])),
                    "reclaimable": sum(
                        img.get("Size", 0) for img in df.get("Images", []) 
                        if img.get("Containers") == 0
                    )
                },
                "containers": {
                    "count": len(df.get("Containers", [])),
                    "size": sum(cnt.get("SizeRw", 0) for cnt in df.get("Containers", [])),
                    "running": len([c for c in df.get("Containers", []) if c.get("State") == "running"])
                },
                "volumes": {
                    "count": len(df.get("Volumes", [])),
                    "size": sum(vol.get("Size", 0) for vol in df.get("Volumes", [])),
                    "reclaimable": sum(
                        vol.get("Size", 0) for vol in df.get("Volumes", [])
                        if vol.get("RefCount") == 0
                    )
                }
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Legacy single-host mode
        client = get_docker_client()
        try:
            df = client.df()
            
            return JSONResponse(content={
                "layers_size": df.get("LayersSize", 0),
                "images": {
                    "count": len(df.get("Images", [])),
                    "size": sum(img.get("Size", 0) for img in df.get("Images", [])),
                    "reclaimable": sum(
                        img.get("Size", 0) for img in df.get("Images", []) 
                        if img.get("Containers") == 0
                    )
                },
                "containers": {
                    "count": len(df.get("Containers", [])),
                    "size": sum(cnt.get("SizeRw", 0) for cnt in df.get("Containers", [])),
                    "running": len([c for c in df.get("Containers", []) if c.get("State") == "running"])
                },
                "volumes": {
                    "count": len(df.get("Volumes", [])),
                    "size": sum(vol.get("Size", 0) for vol in df.get("Volumes", [])),
                    "reclaimable": sum(
                        vol.get("Size", 0) for vol in df.get("Volumes", [])
                        if vol.get("RefCount") == 0
                    )
                }
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))