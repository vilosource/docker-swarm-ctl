"""
Swarm service management endpoints
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import json
import asyncio

from app.db.session import get_db, AsyncSessionLocal
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import DockerOperationError
from app.core.rate_limit import rate_limit
from app.schemas.service import (
    Service, ServiceCreate, ServiceUpdate, ServiceScale,
    ServiceListResponse, ServicePort, ServiceMode
)
from app.schemas.task import Task, TaskListResponse
from app.services.docker_service import IDockerService, DockerServiceFactory
from app.models.user import User
from app.api.decorators import audit_operation
from app.api.decorators_enhanced import handle_api_errors
from app.core.logging import logger
from app.api.v1.websocket.base import ConnectionManager
from app.api.v1.websocket.containers import authenticate_websocket_user
from app.api.v1.websocket.auth import check_permission
from app.services.logs import LogSourceType
from app.api.v1.websocket.unified_logs import handle_log_websocket


router = APIRouter()


async def get_docker_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> IDockerService:
    """Dependency to get Docker service instance"""
    return DockerServiceFactory.create(current_user, db, multi_host=True)


def build_service_spec(service_data: ServiceCreate) -> Dict[str, Any]:
    """Build service specification from creation data"""
    # Container spec
    container_spec = {
        "Image": service_data.image,
        "Labels": service_data.container_labels or {}
    }
    
    if service_data.command:
        container_spec["Command"] = service_data.command
    if service_data.args:
        container_spec["Args"] = service_data.args
    if service_data.env:
        container_spec["Env"] = service_data.env
    if service_data.workdir:
        container_spec["Dir"] = service_data.workdir
    if service_data.user:
        container_spec["User"] = service_data.user
    if service_data.groups:
        container_spec["Groups"] = service_data.groups
    if service_data.healthcheck:
        container_spec["Healthcheck"] = service_data.healthcheck.dict(by_alias=True)
    
    # Mounts
    if service_data.mounts:
        container_spec["Mounts"] = [mount.dict(by_alias=True) for mount in service_data.mounts]
    
    # Secrets
    if service_data.secrets:
        container_spec["Secrets"] = [
            {"SecretID": secret, "SecretName": secret} for secret in service_data.secrets
        ]
    
    # Configs
    if service_data.configs:
        container_spec["Configs"] = [
            {"ConfigID": config, "ConfigName": config} for config in service_data.configs
        ]
    
    # Task template
    task_template = {"ContainerSpec": container_spec}
    
    # Resources
    resources = {}
    if service_data.cpu_limit or service_data.memory_limit:
        resources["Limits"] = {}
        if service_data.cpu_limit:
            resources["Limits"]["NanoCPUs"] = int(service_data.cpu_limit * 1e9)
        if service_data.memory_limit:
            resources["Limits"]["MemoryBytes"] = service_data.memory_limit
    
    if service_data.cpu_reservation or service_data.memory_reservation:
        resources["Reservations"] = {}
        if service_data.cpu_reservation:
            resources["Reservations"]["NanoCPUs"] = int(service_data.cpu_reservation * 1e9)
        if service_data.memory_reservation:
            resources["Reservations"]["MemoryBytes"] = service_data.memory_reservation
    
    if resources:
        task_template["Resources"] = resources
    
    # Placement
    placement = {}
    if service_data.constraints:
        placement["Constraints"] = service_data.constraints
    if service_data.preferences:
        placement["Preferences"] = service_data.preferences
    if service_data.max_replicas:
        placement["MaxReplicas"] = service_data.max_replicas
    
    if placement:
        task_template["Placement"] = placement
    
    # Restart policy
    if service_data.restart_policy:
        task_template["RestartPolicy"] = service_data.restart_policy.dict(by_alias=True)
    
    # Networks
    if service_data.networks:
        task_template["Networks"] = [{"Target": net} for net in service_data.networks]
    
    # Service spec
    spec = {
        "Name": service_data.name,
        "Labels": service_data.labels or {},
        "TaskTemplate": task_template
    }
    
    # Mode
    if service_data.replicas is not None:
        spec["Mode"] = {"Replicated": {"Replicas": service_data.replicas}}
    elif service_data.mode:
        spec["Mode"] = service_data.mode.dict(by_alias=True, exclude_none=True)
    else:
        spec["Mode"] = {"Replicated": {"Replicas": 1}}
    
    # Endpoint spec
    if service_data.ports:
        spec["EndpointSpec"] = {
            "Mode": service_data.endpoint_mode,
            "Ports": [port.dict(by_alias=True) for port in service_data.ports]
        }
    
    # Update config
    if service_data.update_config:
        spec["UpdateConfig"] = service_data.update_config.dict(by_alias=True)
    
    # Rollback config
    if service_data.rollback_config:
        spec["RollbackConfig"] = service_data.rollback_config.dict(by_alias=True)
    
    return spec


@router.post("/", response_model=Service)
@rate_limit("20/hour")
@handle_api_errors("create_service")
@audit_operation("service.create", "service", lambda r: r.name)
async def create_service(
    request: Request,
    response: Response,
    service: ServiceCreate,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Create a new swarm service"""
    try:
        # Convert ServiceCreate to Docker API format
        created_service = await docker_service.create_service(
            image=service.image,
            name=service.name,
            command=service.command,
            mode={"Replicated": {"Replicas": service.replicas or 1}} if service.replicas is not None else service.mode.dict(by_alias=True) if service.mode else None,
            mounts=[mount.dict(by_alias=True) for mount in service.mounts] if service.mounts else None,
            networks=service.networks,
            endpoint_spec={
                "Mode": service.endpoint_mode,
                "Ports": [port.dict(by_alias=True) for port in service.ports]
            } if service.ports else None,
            env=service.env,
            labels=service.labels,
            constraints=service.constraints,
            container_labels=service.container_labels,
            resources={
                "Limits": {
                    "NanoCPUs": int(service.cpu_limit * 1e9) if service.cpu_limit else None,
                    "MemoryBytes": service.memory_limit
                },
                "Reservations": {
                    "NanoCPUs": int(service.cpu_reservation * 1e9) if service.cpu_reservation else None,
                    "MemoryBytes": service.memory_reservation
                }
            } if any([service.cpu_limit, service.memory_limit, service.cpu_reservation, service.memory_reservation]) else None,
            restart_policy=service.restart_policy.dict(by_alias=True) if service.restart_policy else None,
            update_config=service.update_config.dict(by_alias=True) if service.update_config else None,
            rollback_config=service.rollback_config.dict(by_alias=True) if service.rollback_config else None,
            host_id=host_id
        )
        
        logger.info(f"Created service {service.name} with ID {created_service.id}")
        
        return Service(**created_service._attrs)
    except DockerOperationError as e:
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        if "name conflicts with an existing object" in str(e):
            raise HTTPException(status_code=409, detail=f"Service with name '{service.name}' already exists")
        raise


@router.get("/", response_model=ServiceListResponse)
@handle_api_errors("list_services")
async def list_services(
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    label: Optional[str] = Query(None, description="Filter by label (e.g., 'key=value')"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """List swarm services"""
    filters = {}
    if label:
        filters["label"] = [label]
    
    try:
        services = await docker_service.list_services(filters=filters, host_id=host_id)
        service_list = [Service(**svc._attrs) for svc in services]
        
        return ServiceListResponse(
            services=service_list,
            total=len(service_list)
        )
    except DockerOperationError as e:
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.get("/{service_id}", response_model=Service)
@handle_api_errors("get_service")
async def get_service(
    service_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get service details"""
    try:
        service = await docker_service.get_service(service_id, host_id)
        return Service(**service._attrs)
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Service not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.put("/{service_id}", response_model=Service)
@rate_limit("30/hour")
@handle_api_errors("update_service")
@audit_operation("service.update", "service")
async def update_service(
    request: Request,
    response: Response,
    service_id: str,
    update: ServiceUpdate,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Update a swarm service"""
    try:
        # Build update parameters
        update_params = {"version": update.version}
        
        if update.image:
            update_params["image"] = update.image
        if update.replicas is not None:
            update_params["mode"] = {"Replicated": {"Replicas": update.replicas}}
        if update.env:
            update_params["env"] = update.env
        if update.labels:
            update_params["labels"] = update.labels
        if update.constraints:
            update_params["constraints"] = update.constraints
        if update.force_update:
            update_params["force_update"] = update.force_update
        
        # Update the service
        updated_service = await docker_service.update_service(
            service_id=service_id,
            host_id=host_id,
            **update_params
        )
        
        logger.info(f"Updated service {service_id}")
        
        return Service(**updated_service._attrs)
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Service not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.delete("/{service_id}")
@rate_limit("20/hour")
@handle_api_errors("remove_service")
@audit_operation("service.remove", "service")
async def remove_service(
    request: Request,
    response: Response,
    service_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove a swarm service"""
    try:
        await docker_service.remove_service(service_id, host_id)
        logger.info(f"Removed service {service_id}")
        
        return {"message": f"Service {service_id} removed successfully"}
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Service not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.post("/{service_id}/scale", response_model=Service)
@rate_limit("60/hour")
@handle_api_errors("scale_service")
@audit_operation("service.scale", "service", lambda r: f"to {r.replicas} replicas")
async def scale_service(
    request: Request,
    response: Response,
    service_id: str,
    scale_data: ServiceScale,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Scale a swarm service"""
    try:
        scaled_service = await docker_service.scale_service(
            service_id=service_id,
            replicas=scale_data.replicas,
            host_id=host_id
        )
        
        logger.info(f"Scaled service {service_id} to {scale_data.replicas} replicas")
        
        return Service(**scaled_service._attrs)
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Service not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        if "service is not in replicated mode" in str(e).lower():
            raise HTTPException(status_code=400, detail="Can only scale replicated services")
        raise


@router.get("/{service_id}/tasks", response_model=TaskListResponse)
@handle_api_errors("list_service_tasks")
async def list_service_tasks(
    service_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """List tasks for a service"""
    try:
        tasks = await docker_service.list_service_tasks(service_id, host_id=host_id)
        task_list = [Task(**task._attrs) for task in tasks]
        
        return TaskListResponse(
            tasks=task_list,
            total=len(task_list)
        )
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Service not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.get("/{service_id}/logs")
@handle_api_errors("get_service_logs")
async def get_service_logs(
    service_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    tail: int = Query(100, description="Number of lines to show from the end"),
    timestamps: bool = Query(False, description="Add timestamps to log lines"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get service logs"""
    try:
        logs = await docker_service.service_logs(
            service_id=service_id,
            tail=str(tail),
            timestamps=timestamps,
            host_id=host_id
        )
        
        # Convert logs to string if they're bytes
        if isinstance(logs, bytes):
            logs = logs.decode('utf-8', errors='replace')
        
        return {"logs": logs}
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Service not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.websocket("/{service_id}/logs")
async def service_logs_ws(
    websocket: WebSocket,
    service_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    tail: int = Query(100, description="Number of lines to show from the end"),
    follow: bool = Query(True, description="Follow log output"),
    timestamps: bool = Query(False, description="Add timestamps"),
    token: Optional[str] = Query(None)
):
    """
    Stream service logs via WebSocket.
    
    This endpoint now uses the unified log streaming architecture,
    ensuring consistency with container logs and other log sources.
    """
    await handle_log_websocket(
        websocket=websocket,
        source_type=LogSourceType.SERVICE,
        resource_id=service_id,
        host_id=host_id,
        tail=tail,
        follow=follow,
        timestamps=timestamps,
        token=token
    )