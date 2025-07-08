"""
Swarm secret management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.exceptions import DockerOperationError
from app.core.rate_limit import rate_limit
from app.schemas.secret import Secret, SecretCreate, SecretListResponse
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


@router.post("/", response_model=Secret)
@rate_limit("30/hour")
@handle_api_errors("create_secret")
@audit_operation("secret.create", "secret", lambda r: r.name)
async def create_secret(
    request: Request,
    response: Response,
    secret: SecretCreate,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Create a new swarm secret"""
    try:
        # Get encoded data
        data = secret.get_encoded_data()
        
        created_secret = await docker_service.create_secret(
            name=secret.name,
            data=data,
            labels=secret.labels,
            host_id=host_id
        )
        
        logger.info(f"Created secret {secret.name} with ID {created_secret.id}")
        
        return Secret(**created_secret._attrs)
    except DockerOperationError as e:
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=f"Secret with name '{secret.name}' already exists")
        raise


@router.get("/", response_model=SecretListResponse)
@handle_api_errors("list_secrets")
async def list_secrets(
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    label: Optional[str] = Query(None, description="Filter by label (e.g., 'key=value')"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """List swarm secrets"""
    filters = {}
    if label:
        filters["label"] = [label]
    
    try:
        secrets = await docker_service.list_secrets(filters=filters, host_id=host_id)
        secret_list = [Secret(**secret._attrs) for secret in secrets]
        
        return SecretListResponse(
            secrets=secret_list,
            total=len(secret_list)
        )
    except DockerOperationError as e:
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.get("/{secret_id}", response_model=Secret)
@handle_api_errors("get_secret")
async def get_secret(
    secret_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    docker_service: IDockerService = Depends(get_docker_service)
):
    """Get secret details (metadata only, not the secret value)"""
    try:
        secret = await docker_service.get_secret(secret_id, host_id)
        return Secret(**secret._attrs)
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Secret not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        raise


@router.delete("/{secret_id}")
@rate_limit("30/hour")
@handle_api_errors("remove_secret")
@audit_operation("secret.remove", "secret")
async def remove_secret(
    request: Request,
    response: Response,
    secret_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    current_user: User = Depends(require_role("operator")),
    docker_service: IDockerService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db)
):
    """Remove a swarm secret"""
    try:
        await docker_service.remove_secret(secret_id, host_id)
        logger.info(f"Removed secret {secret_id}")
        
        return {"message": f"Secret {secret_id} removed successfully"}
    except DockerOperationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Secret not found")
        if "This node is not a swarm manager" in str(e):
            raise HTTPException(status_code=400, detail="Host is not a swarm manager")
        if "is in use" in str(e).lower():
            raise HTTPException(status_code=409, detail="Secret is in use by one or more services")
        raise