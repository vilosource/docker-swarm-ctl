"""
Swarm config management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import DockerOperationError
from app.core.rate_limit import rate_limit
from app.schemas.config import Config, ConfigCreate, ConfigListResponse
from app.services.docker_service import IDockerService, DockerServiceFactory
from app.models.user import User
from app.api.decorators import audit_operation
from app.api.decorators_enhanced import handle_api_errors
from app.core.logging import logger


router = APIRouter()


async def get_docker_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> IDockerService:
    """Dependency to get Docker service instance"""
    return DockerServiceFactory.create(current_user, db, multi_host=True)


@router.post("/", response_model=Config)
@rate_limit("30/hour")
@handle_api_errors("create_config")
@audit_operation("config.create", "config", lambda r: r.name)
async def create_config(
    request: Request,
    response: Response,
    config: ConfigCreate,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Create a new swarm config"""
    try:
        # Get encoded data
        data = config.get_encoded_data()
        
        created_config = await docker_service.create_config(
            name=config.name,
            data=data,
            labels=config.labels,
            host_id=host_id
        )
        
        logger.info(f"Created config {config.name} with ID {created_config.id}")
        
        return Config(**created_config._attrs)
    except DockerOperationError as e:
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=f"Config with name '{config.name}' already exists")
        raise


@router.get("/", response_model=ConfigListResponse)
@handle_api_errors("list_configs")
async def list_configs(
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    label: Optional[str] = Query(None, description="Filter by label (e.g., 'key=value')"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """List swarm configs"""
    filters = {}
    if label:
        filters["label"] = [label]
    
    try:
        configs = await docker_service.list_configs(filters=filters, host_id=host_id)
        config_list = [Config(**config._attrs) for config in configs]
        
        return ConfigListResponse(
            configs=config_list,
            total=len(config_list)
        )
    except DockerOperationError as e:
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.get("/{config_id}", response_model=Config)
@handle_api_errors("get_config")
async def get_config(
    config_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get config details"""
    try:
        config = await docker_service.get_config(config_id, host_id)
        return Config(**config._attrs)
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Config not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.delete("/{config_id}")
@rate_limit("30/hour")
@handle_api_errors("remove_config")
@audit_operation("config.remove", "config")
async def remove_config(
    request: Request,
    response: Response,
    config_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove a swarm config"""
    try:
        await docker_service.remove_config(config_id, host_id)
        logger.info(f"Removed config {config_id}")
        
        return {"message": f"Config {config_id} removed successfully"}
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Config not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        if "is in use" in str(e).lower():
            raise HTTPException(status_code=409, detail="Config is in use by one or more services")
        raise