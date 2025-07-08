"""
Swarm node management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import DockerOperationError
from app.core.rate_limit import rate_limit
from app.schemas.node import Node, NodeUpdate, NodeListResponse
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


@router.get("/", response_model=NodeListResponse)
@handle_api_errors("list_nodes")
async def list_nodes(
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    role: Optional[str] = Query(None, description="Filter by role: 'worker' or 'manager'"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """List swarm nodes from specified manager host"""
    filters = {}
    if role:
        filters["role"] = [role]
    
    try:
        nodes = await docker_service.list_nodes(filters=filters, host_id=host_id)
        node_list = [Node(**node._attrs) for node in nodes]
        
        return NodeListResponse(
            nodes=node_list,
            total=len(node_list)
        )
    except DockerOperationError as e:
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.get("/{node_id}", response_model=Node)
@handle_api_errors("get_node")
async def get_node(
    node_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get swarm node details"""
    try:
        node = await docker_service.get_node(node_id, host_id)
        return Node(**node._attrs)
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Node not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.put("/{node_id}", response_model=Node)
@rate_limit("30/hour")
@handle_api_errors("update_node")
@audit_operation("node.update", "node")
async def update_node(
    request: Request,
    response: Response,
    node_id: str,
    update: NodeUpdate,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("admin")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Update swarm node (availability, role, labels)"""
    try:
        # Prepare update spec
        spec = {
            "Role": update.spec.role,
            "Availability": update.spec.availability
        }
        if update.spec.labels:
            spec["Labels"] = update.spec.labels
        
        node = await docker_service.update_node(
            node_id=node_id,
            version=update.version,
            spec=spec,
            host_id=host_id
        )
        
        logger.info(f"Updated node {node_id}: role={update.spec.role}, availability={update.spec.availability}")
        
        return Node(**node._attrs)
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Node not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.delete("/{node_id}")
@rate_limit("10/hour")
@handle_api_errors("remove_node")
@audit_operation("node.remove", "node")
async def remove_node(
    request: Request,
    response: Response,
    node_id: str,
    force: bool = Query(False, description="Force removal"),
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("admin")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove node from swarm"""
    try:
        await docker_service.remove_node(node_id, force, host_id)
        logger.info(f"Removed node {node_id} from swarm")
        
        return {"message": f"Node {node_id} removed successfully"}
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Node not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        if "remove a running node" in str(e).lower():
            raise HTTPException(status_code=400, detail="Cannot remove running node. Use force=true or stop the node first")
        raise