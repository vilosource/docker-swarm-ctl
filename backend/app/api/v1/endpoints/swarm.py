"""
Swarm management endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import DockerOperationError
from app.core.rate_limit import rate_limit
from app.schemas.swarm import SwarmInfo, SwarmInit, SwarmJoin, SwarmLeave, SwarmUpdate
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


@router.get("/", response_model=SwarmInfo)
@handle_api_errors("get_swarm_info")
async def get_swarm_info(
    host_id: str = Query(..., description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get swarm information from specified host"""
    try:
        swarm_attrs = await docker_service.get_swarm_info(host_id)
        # Just return the raw attrs, let Pydantic handle the conversion
        return SwarmInfo(**swarm_attrs)
    except DockerOperationError as e:
        error_msg = str(e)
        if "This node is not a swarm manager" in error_msg:
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        elif "not part of a swarm" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Host is not part of a swarm")
        raise
    except Exception as e:
        logger.error(f"Failed to get swarm info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get swarm info: {str(e)}")


@router.post("/init", response_model=SwarmInfo)
@rate_limit("5/hour")
@handle_api_errors("init_swarm")
@audit_operation("swarm.init", "swarm")
async def init_swarm(
    request: Request,
    response: Response,
    swarm_init: SwarmInit,
    host_id: str = Query(..., description="Docker host ID"),
    current_user: User = Depends(require_role("admin")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Initialize a new swarm on specified host"""
    # Initialize swarm
    node_id = await docker_service.init_swarm(
        advertise_addr=swarm_init.advertise_addr,
        listen_addr=swarm_init.listen_addr,
        force_new_cluster=swarm_init.force_new_cluster,
        default_addr_pool=swarm_init.default_addr_pool,
        subnet_size=swarm_init.subnet_size,
        data_path_addr=swarm_init.data_path_addr,
        data_path_port=swarm_init.data_path_port,
        host_id=host_id
    )
    
    logger.info(f"Swarm initialized on host {host_id} with node ID {node_id}")
    
    # Get updated swarm info
    swarm_attrs = await docker_service.get_swarm_info(host_id)
    return SwarmInfo(**swarm_attrs)


@router.post("/join")
@rate_limit("10/hour")
@handle_api_errors("join_swarm")
@audit_operation("swarm.join", "swarm")
async def join_swarm(
    request: Request,
    response: Response,
    swarm_join: SwarmJoin,
    host_id: str = Query(..., description="Docker host ID"),
    current_user: User = Depends(require_role("admin")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Join host to existing swarm"""
    await docker_service.join_swarm(
        remote_addrs=swarm_join.remote_addrs,
        join_token=swarm_join.join_token,
        advertise_addr=swarm_join.advertise_addr,
        listen_addr=swarm_join.listen_addr,
        data_path_addr=swarm_join.data_path_addr,
        host_id=host_id
    )
    
    logger.info(f"Host {host_id} joined swarm")
    
    return {"message": "Successfully joined swarm"}


@router.post("/leave")
@rate_limit("10/hour")
@handle_api_errors("leave_swarm")
@audit_operation("swarm.leave", "swarm")
async def leave_swarm(
    request: Request,
    response: Response,
    leave_data: SwarmLeave = SwarmLeave(),
    host_id: str = Query(..., description="Docker host ID"),
    current_user: User = Depends(require_role("admin")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove host from swarm"""
    await docker_service.leave_swarm(
        force=leave_data.force,
        host_id=host_id
    )
    
    logger.info(f"Host {host_id} left swarm")
    
    return {"message": "Successfully left swarm"}


@router.put("/", response_model=SwarmInfo)
@rate_limit("10/hour")
@handle_api_errors("update_swarm")
@audit_operation("swarm.update", "swarm")
async def update_swarm(
    request: Request,
    response: Response,
    update_data: SwarmUpdate,
    host_id: str = Query(..., description="Docker host ID"),
    current_user: User = Depends(require_role("admin")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Update swarm configuration"""
    await docker_service.update_swarm(
        rotate_worker_token=update_data.rotate_worker_token,
        rotate_manager_token=update_data.rotate_manager_token,
        rotate_manager_unlock_key=update_data.rotate_manager_unlock_key,
        host_id=host_id
    )
    
    # Get updated swarm info
    swarm_attrs = await docker_service.get_swarm_info(host_id)
    return SwarmInfo(**swarm_attrs)