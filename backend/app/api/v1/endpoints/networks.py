"""
Network management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import ValidationError
from app.schemas.network import (
    NetworkCreate, NetworkResponse, NetworkInspect, 
    NetworkConnect, NetworkDisconnect, NetworkPruneResponse
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


def format_network(network_data, host_id: Optional[str] = None, host_name: Optional[str] = None) -> NetworkResponse:
    """Format network data for response"""
    attrs = network_data.attrs if hasattr(network_data, 'attrs') else network_data
    
    return NetworkResponse(
        Id=attrs.get("Id", network_data.id if hasattr(network_data, 'id') else ""),
        Name=attrs.get("Name", network_data.name if hasattr(network_data, 'name') else ""),
        Driver=attrs.get("Driver", ""),
        Scope=attrs.get("Scope", ""),
        IPAM=attrs.get("IPAM"),
        Internal=attrs.get("Internal", False),
        Attachable=attrs.get("Attachable", False),
        Ingress=attrs.get("Ingress", False),
        Containers=attrs.get("Containers", {}),
        Options=attrs.get("Options"),
        Labels=attrs.get("Labels", {}),
        Created=attrs.get("Created"),
        EnableIPv6=attrs.get("EnableIPv6", False),
        host_id=host_id,
        host_name=host_name
    )


@router.get("/", response_model=List[NetworkResponse])
@handle_api_errors("list_networks")
async def list_networks(
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """List networks from specified or all Docker hosts"""
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise ValidationError("filters", "Invalid JSON format")
    
    if host_id:
        # Single host query
        networks = await docker_service.list_networks(filters=filter_dict, host_id=host_id)
        
        # Get host info
        host_service = await get_host_service(db)
        host = await host_service.get_by_id(host_id)
        host_name = host.display_name or host.name if host else None
        
        return [format_network(net, host_id, host_name) for net in networks]
    else:
        # Multi-host query - get networks from all active hosts
        host_service = await get_host_service(db)
        hosts = await host_service.get_all_active()
        
        all_networks = []
        for host in hosts:
            try:
                networks = await docker_service.list_networks(
                    filters=filter_dict, 
                    host_id=str(host.id)
                )
                host_name = host.display_name or host.name
                all_networks.extend([
                    format_network(net, str(host.id), host_name) 
                    for net in networks
                ])
            except Exception as e:
                logger.warning(f"Failed to get networks from host {host.name}: {e}")
                
        return all_networks


@router.post("/", response_model=NetworkResponse)
@handle_api_errors("create_network")
@audit_operation("network.create", "network", lambda r: r.name)
async def create_network(
    request: Request,
    network: NetworkCreate,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
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
    
    # Get host info for response
    if host_id:
        host_service = await get_host_service(db)
        host = await host_service.get_by_id(host_id)
        host_name = host.display_name or host.name if host else None
    else:
        host_name = None
    
    return format_network(created_network, host_id, host_name)


@router.get("/{network_id}", response_model=NetworkInspect)
@handle_api_errors("get_network")
async def get_network(
    network_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get network details"""
    network = await docker_service.get_network(network_id, host_id)
    return NetworkInspect(**network.attrs)


@router.delete("/{network_id}")
@handle_api_errors("remove_network")
@audit_operation("network.delete", "network")
@standard_response("Network {network_id} removed")
async def remove_network(
    request: Request,
    network_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove a network"""
    await docker_service.remove_network(network_id, host_id)


@router.post("/{network_id}/connect")
@handle_api_errors("connect_container")
@audit_operation("network.connect", "network")
@standard_response("Container connected to network {network_id}")
async def connect_container(
    request: Request,
    network_id: str,
    connection: NetworkConnect,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Connect a container to a network"""
    network = await docker_service.get_network(network_id, host_id)
    # Get container to ensure it exists on the same host
    container = await docker_service.get_container(connection.container, host_id)
    
    # Use the network object to connect
    # Note: Docker SDK methods are synchronous
    network.connect(connection.container, **(connection.endpoint_config or {}))


@router.post("/{network_id}/disconnect")
@handle_api_errors("disconnect_container")
@audit_operation("network.disconnect", "network")
@standard_response("Container disconnected from network {network_id}")
async def disconnect_container(
    request: Request,
    network_id: str,
    disconnection: NetworkDisconnect,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect a container from a network"""
    network = await docker_service.get_network(network_id, host_id)
    
    # Use the network object to disconnect
    # Note: Docker SDK methods are synchronous
    network.disconnect(disconnection.container, force=disconnection.force)


@router.post("/prune")
@handle_api_errors("prune_networks")
@audit_operation("network.prune", "system")
async def prune_networks(
    request: Request,
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("admin")),
    docker_service: IDockerService = Depends(get_docker_service),
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