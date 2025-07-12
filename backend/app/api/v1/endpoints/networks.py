"""
Network management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import ValidationError
from app.core.rate_limit import rate_limit
from app.schemas.network import (
    NetworkCreate, NetworkResponse, NetworkInspect, 
    NetworkConnect, NetworkDisconnect, NetworkPruneResponse
)
from app.services.async_docker_service import IAsyncDockerService, AsyncDockerServiceFactory
from app.models.user import User
from app.api.decorators import audit_operation
from app.api.decorators_enhanced import handle_api_errors, standard_response
from app.core.logging import logger


router = APIRouter()


async def get_docker_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> IAsyncDockerService:
    """Dependency to get async Docker service instance"""
    return AsyncDockerServiceFactory.create(current_user, db, multi_host=True)


def format_network(network_data) -> NetworkResponse:
    """Format network data for response"""
    return NetworkResponse(
        Id=network_data.id,
        Name=network_data.name,
        Driver=network_data.driver,
        Scope=network_data.scope,
        IPAM=network_data.ipam,
        Internal=network_data.internal,
        Attachable=network_data.attachable,
        Ingress=network_data.ingress,
        Containers=network_data.containers or {},  # Handle None containers
        Options=network_data.options or {},  # Handle None options
        Labels=network_data.labels or {},  # Handle None labels
        Created=network_data.created,
        EnableIPv6=getattr(network_data, 'enable_ipv6', False),  # Default to False if not present
        host_id=network_data.host_id,
        host_name=None  # TODO: Add host name to NetworkData if needed
    )


@router.get("/", response_model=List[NetworkResponse])
@handle_api_errors("list_networks")
async def list_networks(
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IAsyncDockerService = Depends(get_docker_service)
):
    """List networks from specified or all Docker hosts"""
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise ValidationError("filters", "Invalid JSON format")
    
    networks = await docker_service.list_networks(filters=filter_dict, host_id=host_id)
    return [format_network(net) for net in networks]


@router.post("/", response_model=NetworkResponse)
@rate_limit("30/hour")
@handle_api_errors("create_network")
@audit_operation("network.create", "network", lambda r: r.name)
async def create_network(
    request: Request,
    response: Response,
    network: NetworkCreate,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IAsyncDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Create a new network on specified or default Docker host"""
    created_network = await docker_service.create_network(
        name=network.name,
        driver=network.driver,
        options=network.options,
        ipam=network.ipam,
        internal=network.internal,
        labels=network.labels,
        enable_ipv6=network.enable_ipv6,
        attachable=network.attachable,
        host_id=host_id
    )
    
    return format_network(created_network)


@router.get("/{network_id}", response_model=NetworkInspect)
@handle_api_errors("get_network")
async def get_network(
    network_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IAsyncDockerService = Depends(get_docker_service)
):
    """Get network details"""
    network_data = await docker_service.get_network(network_id, host_id)
    # Access the underlying network object's attrs
    return NetworkInspect(**network_data.network.attrs)


@router.delete("/{network_id}")
@rate_limit("30/hour")
@handle_api_errors("remove_network")
@audit_operation("network.delete", "network")
@standard_response("Network removed successfully")
async def remove_network(
    request: Request,
    response: Response,
    network_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IAsyncDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove a network"""
    await docker_service.remove_network(network_id, host_id)


@router.post("/{network_id}/connect")
@rate_limit("60/minute")
@handle_api_errors("connect_container")
@audit_operation("network.connect", "network")
@standard_response("Container connected to network")
async def connect_container(
    request: Request,
    response: Response,
    network_id: str,
    connection: NetworkConnect,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IAsyncDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Connect a container to a network"""
    network_data = await docker_service.get_network(network_id, host_id)
    # Get container to ensure it exists on the same host
    container = await docker_service.get_container(connection.container, host_id)
    
    # Use the network object to connect
    # Note: Docker SDK methods are synchronous
    network_data.network.connect(connection.container, **(connection.endpoint_config or {}))


@router.post("/{network_id}/disconnect")
@rate_limit("60/minute")
@handle_api_errors("disconnect_container")
@audit_operation("network.disconnect", "network")
@standard_response("Container disconnected from network")
async def disconnect_container(
    request: Request,
    response: Response,
    network_id: str,
    disconnection: NetworkDisconnect,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IAsyncDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect a container from a network"""
    network_data = await docker_service.get_network(network_id, host_id)
    
    # Use the network object to disconnect
    # Note: Docker SDK methods are synchronous
    network_data.network.disconnect(disconnection.container, force=disconnection.force)


@router.post("/prune")
@rate_limit("5/hour")
@handle_api_errors("prune_networks")
@audit_operation("network.prune", "system")
async def prune_networks(
    request: Request,
    response: Response,
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("admin")),
    docker_service: IAsyncDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove all unused networks"""
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise ValidationError("filters", "Invalid JSON format")
    
    result = await docker_service.prune_networks(filters=filter_dict, host_id=host_id)
    
    return NetworkPruneResponse(
        networks_deleted=result.get("NetworksDeleted", [])
    )