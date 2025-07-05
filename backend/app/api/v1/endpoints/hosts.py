from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
import docker

from app.api import deps
from app.core.security import require_admin, require_role
from app.models import (
    User, DockerHost, HostCredential, HostTag, 
    UserHostPermission, UserRole, HostStatus
)
from app.schemas.docker_host import (
    DockerHostCreate, DockerHostUpdate, DockerHostResponse,
    DockerHostListResponse, HostConnectionTest, 
    UserHostPermissionCreate, UserHostPermissionResponse
)
from app.services.encryption import get_encryption_service
from app.services.docker_connection_manager import get_docker_connection_manager
from app.services.audit import audit_log
from app.core.logging import logger

router = APIRouter()


@router.get("/", response_model=DockerHostListResponse)
async def list_hosts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    active_only: bool = Query(True),
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """List Docker hosts accessible to the current user"""
    # Build base query
    query = select(DockerHost).options(selectinload(DockerHost.tags))
    
    # Filter by active status
    if active_only:
        query = query.where(DockerHost.is_active == True)
    
    # Apply permission filtering for non-admin users
    if current_user.role != UserRole.admin:
        # Get hosts user has permission to access
        permission_query = select(UserHostPermission.host_id).where(
            UserHostPermission.user_id == current_user.id
        )
        permitted_hosts = await db.execute(permission_query)
        permitted_host_ids = [row[0] for row in permitted_hosts]
        
        if permitted_host_ids:
            query = query.where(DockerHost.id.in_(permitted_host_ids))
        else:
            # User has no permissions
            return DockerHostListResponse(items=[], total=0, page=page, per_page=per_page)
    
    # Count total
    count_query = select(DockerHost).where(query.whereclause)
    total_result = await db.execute(count_query)
    total = len(total_result.all())
    
    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    hosts = result.scalars().all()
    
    return DockerHostListResponse(
        items=[DockerHostResponse.model_validate(host) for host in hosts],
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("/", response_model=DockerHostResponse, status_code=status.HTTP_201_CREATED)
async def create_host(
    host_data: DockerHostCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(deps.get_db)
):
    """Create a new Docker host (admin only)"""
    # Check if host with same name exists
    existing = await db.execute(
        select(DockerHost).where(DockerHost.name == host_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Host with name '{host_data.name}' already exists"
        )
    
    # If setting as default, unset other defaults
    if host_data.is_default:
        await db.execute(
            select(DockerHost).where(DockerHost.is_default == True)
        )
        # Update all to not default
        # In production, use proper UPDATE statement
    
    # Create host
    host = DockerHost(
        name=host_data.name,
        description=host_data.description,
        host_type=host_data.host_type,
        connection_type=host_data.connection_type,
        host_url=host_data.host_url,
        is_active=host_data.is_active,
        is_default=host_data.is_default,
        created_by=current_user.id,
        status=HostStatus.pending
    )
    db.add(host)
    await db.flush()  # Get the host ID
    
    # Add credentials if provided
    encryption = get_encryption_service()
    for cred_data in host_data.credentials:
        encrypted_value = encryption.encrypt(cred_data.credential_value)
        credential = HostCredential(
            host_id=host.id,
            credential_type=cred_data.credential_type,
            encrypted_value=encrypted_value,
            credential_metadata=cred_data.credential_metadata
        )
        db.add(credential)
    
    # Add tags if provided
    for tag_data in host_data.tags:
        tag = HostTag(
            host_id=host.id,
            tag_name=tag_data.tag_name,
            tag_value=tag_data.tag_value
        )
        db.add(tag)
    
    # Grant admin user full access
    permission = UserHostPermission(
        user_id=current_user.id,
        host_id=host.id,
        permission_level="admin",
        granted_by=current_user.id
    )
    db.add(permission)
    
    await db.commit()
    await db.refresh(host)
    
    # Audit log
    await audit_log(
        db,
        user=current_user,
        action="host.create",
        resource_type="docker_host",
        resource_id=str(host.id),
        details={"host_name": host.name, "host_url": host.host_url}
    )
    
    # Load relationships for response
    result = await db.execute(
        select(DockerHost)
        .options(selectinload(DockerHost.tags))
        .where(DockerHost.id == host.id)
    )
    host = result.scalar_one()
    
    return DockerHostResponse.model_validate(host)


@router.get("/{host_id}", response_model=DockerHostResponse)
async def get_host(
    host_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db),
    connection_manager: DockerConnectionManager = Depends(lambda: get_docker_connection_manager())
):
    """Get Docker host details"""
    # Check permissions
    await connection_manager._check_permissions(str(host_id), current_user, db)
    
    # Get host with relationships
    result = await db.execute(
        select(DockerHost)
        .options(selectinload(DockerHost.tags))
        .where(DockerHost.id == host_id)
    )
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )
    
    return DockerHostResponse.model_validate(host)


@router.put("/{host_id}", response_model=DockerHostResponse)
async def update_host(
    host_id: UUID,
    host_update: DockerHostUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(deps.get_db)
):
    """Update Docker host (admin only)"""
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == host_id)
    )
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )
    
    # Update fields
    update_data = host_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(host, field, value)
    
    await db.commit()
    await db.refresh(host)
    
    # Audit log
    await audit_log(
        db,
        user=current_user,
        action="host.update",
        resource_type="docker_host",
        resource_id=str(host.id),
        details={"updates": update_data}
    )
    
    # Load relationships for response
    result = await db.execute(
        select(DockerHost)
        .options(selectinload(DockerHost.tags))
        .where(DockerHost.id == host.id)
    )
    host = result.scalar_one()
    
    return DockerHostResponse.model_validate(host)


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(
    host_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(deps.get_db),
    connection_manager: DockerConnectionManager = Depends(lambda: get_docker_connection_manager())
):
    """Delete Docker host (admin only)"""
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == host_id)
    )
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )
    
    # Close any existing connections
    await connection_manager.close_connection(str(host_id))
    
    # Delete host (cascades to related records)
    await db.delete(host)
    await db.commit()
    
    # Audit log
    await audit_log(
        db,
        user=current_user,
        action="host.delete",
        resource_type="docker_host",
        resource_id=str(host_id),
        details={"host_name": host.name}
    )


@router.post("/{host_id}/test", response_model=HostConnectionTest)
async def test_host_connection(
    host_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db),
    connection_manager: DockerConnectionManager = Depends(lambda: get_docker_connection_manager())
):
    """Test connection to a Docker host"""
    try:
        # Get client (checks permissions)
        client = await connection_manager.get_client(str(host_id), current_user, db)
        
        # Test connection
        info = client.info()
        
        return HostConnectionTest(
            success=True,
            message="Connection successful",
            docker_version=info.get("ServerVersion"),
            api_version=info.get("ApiVersion")
        )
    except Exception as e:
        logger.error(f"Connection test failed for host {host_id}: {str(e)}")
        return HostConnectionTest(
            success=False,
            message="Connection failed",
            error=str(e)
        )


@router.get("/{host_id}/permissions", response_model=List[UserHostPermissionResponse])
async def list_host_permissions(
    host_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(deps.get_db)
):
    """List permissions for a host (admin only)"""
    result = await db.execute(
        select(UserHostPermission)
        .where(UserHostPermission.host_id == host_id)
    )
    permissions = result.scalars().all()
    
    return [
        UserHostPermissionResponse.model_validate(perm) 
        for perm in permissions
    ]


@router.post("/{host_id}/permissions", response_model=UserHostPermissionResponse)
async def grant_host_permission(
    host_id: UUID,
    permission_data: UserHostPermissionCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(deps.get_db)
):
    """Grant user permission to access a host (admin only)"""
    # Check if permission already exists
    existing = await db.execute(
        select(UserHostPermission).where(
            and_(
                UserHostPermission.user_id == permission_data.user_id,
                UserHostPermission.host_id == host_id
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has permission for this host"
        )
    
    # Create permission
    permission = UserHostPermission(
        user_id=permission_data.user_id,
        host_id=host_id,
        permission_level=permission_data.permission_level,
        granted_by=current_user.id
    )
    db.add(permission)
    await db.commit()
    await db.refresh(permission)
    
    # Audit log
    await audit_log(
        db,
        user=current_user,
        action="host.permission.grant",
        resource_type="docker_host",
        resource_id=str(host_id),
        host_id=host_id,
        details={
            "user_id": str(permission_data.user_id),
            "permission_level": permission_data.permission_level
        }
    )
    
    return UserHostPermissionResponse.model_validate(permission)


@router.delete("/{host_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_host_permission(
    host_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(deps.get_db)
):
    """Revoke user permission to access a host (admin only)"""
    result = await db.execute(
        select(UserHostPermission).where(
            and_(
                UserHostPermission.user_id == user_id,
                UserHostPermission.host_id == host_id
            )
        )
    )
    permission = result.scalar_one_or_none()
    
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    await db.delete(permission)
    await db.commit()
    
    # Audit log
    await audit_log(
        db,
        user=current_user,
        action="host.permission.revoke",
        resource_type="docker_host",
        resource_id=str(host_id),
        host_id=host_id,
        details={"user_id": str(user_id)}
    )