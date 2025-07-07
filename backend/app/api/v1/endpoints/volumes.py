"""
Volume management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import ValidationError
from app.schemas.volume import (
    VolumeCreate, VolumeResponse, VolumeInspect, VolumePruneResponse
)
from app.services.docker_service import IDockerService, DockerServiceFactory
from app.services.host_service import get_host_service
from app.models.user import User
from app.api.decorators import audit_operation
from app.api.decorators_enhanced import handle_api_errors, standard_response
from app.core.logging import logger


router = APIRouter()


async def get_docker_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> IDockerService:
    """Dependency to get Docker service instance"""
    return DockerServiceFactory.create(current_user, db, multi_host=True)


def format_volume(volume_data, host_id: Optional[str] = None, host_name: Optional[str] = None) -> VolumeResponse:
    """Format volume data for response"""
    attrs = volume_data.attrs if hasattr(volume_data, 'attrs') else volume_data
    
    return VolumeResponse(
        name=attrs.get("Name", volume_data.name if hasattr(volume_data, 'name') else ""),
        driver=attrs.get("Driver", ""),
        mountpoint=attrs.get("Mountpoint", ""),
        created_at=attrs.get("CreatedAt"),
        status=attrs.get("Status"),
        labels=attrs.get("Labels", {}),
        scope=attrs.get("Scope", "local"),
        options=attrs.get("Options"),
        host_id=host_id,
        host_name=host_name
    )


@router.get("/", response_model=List[VolumeResponse])
@handle_api_errors("list_volumes")
async def list_volumes(
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """List volumes from specified or all Docker hosts"""
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise ValidationError("filters", "Invalid JSON format")
    
    if host_id:
        # Single host query
        volumes = await docker_service.list_volumes(filters=filter_dict, host_id=host_id)
        
        # Get host info
        host_service = await get_host_service(db)
        host = await host_service.get_by_id(host_id)
        host_name = host.display_name or host.name if host else None
        
        return [format_volume(vol, host_id, host_name) for vol in volumes]
    else:
        # Multi-host query - get volumes from all active hosts
        host_service = await get_host_service(db)
        hosts = await host_service.get_all_active()
        
        all_volumes = []
        for host in hosts:
            try:
                volumes = await docker_service.list_volumes(
                    filters=filter_dict, 
                    host_id=str(host.id)
                )
                host_name = host.display_name or host.name
                all_volumes.extend([
                    format_volume(vol, str(host.id), host_name) 
                    for vol in volumes
                ])
            except Exception as e:
                logger.warning(f"Failed to get volumes from host {host.name}: {e}")
                
        return all_volumes


@router.post("/", response_model=VolumeResponse)
@handle_api_errors("create_volume")
@audit_operation("volume.create", "volume", lambda r: r.name)
async def create_volume(
    request: Request,
    volume: VolumeCreate,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Create a new volume on specified or default Docker host"""
    created_volume = await docker_service.create_volume(
        name=volume.name,
        driver=volume.driver,
        driver_opts=volume.driver_opts,
        labels=volume.labels,
        host_id=host_id
    )
    
    # Get host info for response
    if host_id:
        host_service = await get_host_service(db)
        host = await host_service.get_by_id(host_id)
        host_name = host.display_name or host.name if host else None
    else:
        host_name = None
    
    return format_volume(created_volume, host_id, host_name)


@router.get("/{volume_name}", response_model=VolumeInspect)
@handle_api_errors("get_volume")
async def get_volume(
    volume_name: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get volume details"""
    volume = await docker_service.get_volume(volume_name, host_id)
    return VolumeInspect(**volume.attrs)


@router.delete("/{volume_name}")
@handle_api_errors("remove_volume")
@audit_operation("volume.delete", "volume")
@standard_response("Volume {volume_name} removed")
async def remove_volume(
    request: Request,
    volume_name: str,
    force: bool = Query(False, description="Force removal"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove a volume"""
    await docker_service.remove_volume(volume_name, force, host_id)


@router.post("/prune")
@handle_api_errors("prune_volumes")
@audit_operation("volume.prune", "system")
async def prune_volumes(
    request: Request,
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("admin")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove all unused volumes"""
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise ValidationError("filters", "Invalid JSON format")
    
    result = await docker_service.prune_volumes(filters=filter_dict, host_id=host_id)
    
    return VolumePruneResponse(
        volumes_deleted=result.get("VolumesDeleted", []),
        space_reclaimed=result.get("SpaceReclaimed", 0)
    )