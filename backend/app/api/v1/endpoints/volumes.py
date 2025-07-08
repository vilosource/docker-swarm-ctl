"""
Volume management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import ValidationError
from app.core.rate_limit import rate_limit
from app.schemas.volume import (
    VolumeCreate, VolumeResponse, VolumeInspect, VolumePruneResponse
)
from app.services.docker_service import IDockerService, DockerServiceFactory
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


def format_volume(volume_data) -> VolumeResponse:
    """Format volume data for response"""
    return VolumeResponse(
        name=volume_data.name,
        driver=volume_data.driver,
        mountpoint=volume_data.mountpoint,
        created_at=volume_data.created_at,
        status=volume_data.status,
        labels=volume_data.labels or {},  # Handle None labels
        scope=volume_data.scope,
        options=volume_data.options or {},  # Handle None options
        host_id=volume_data.host_id,
        host_name=None  # TODO: Add host name to VolumeData if needed
    )


@router.get("/", response_model=List[VolumeResponse])
@handle_api_errors("list_volumes")
async def list_volumes(
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """List volumes from specified or all Docker hosts"""
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise ValidationError("filters", "Invalid JSON format")
    
    volumes = await docker_service.list_volumes(filters=filter_dict, host_id=host_id)
    return [format_volume(vol) for vol in volumes]


@router.post("/", response_model=VolumeResponse)
@rate_limit("30/hour")
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
    
    return format_volume(created_volume)


@router.get("/{volume_name}", response_model=VolumeInspect)
@handle_api_errors("get_volume")
async def get_volume(
    volume_name: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get volume details"""
    volume_data = await docker_service.get_volume(volume_name, host_id)
    # Access the underlying volume object's attrs
    return VolumeInspect(**volume_data.volume.attrs)


@router.delete("/{volume_name}")
@rate_limit("50/hour")
@handle_api_errors("remove_volume")
@audit_operation("volume.delete", "volume")
@standard_response("Volume removed successfully")
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
@rate_limit("5/hour")
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