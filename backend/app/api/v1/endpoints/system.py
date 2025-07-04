from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.services.docker_client import get_docker_client
from app.services.audit import AuditService
from app.models.user import User


router = APIRouter()


@router.get("/info")
async def get_system_info(
    current_user: User = Depends(get_current_active_user)
):
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
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    
    try:
        return client.version()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prune")
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
async def disk_usage(
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    
    try:
        df = client.df()
        
        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))