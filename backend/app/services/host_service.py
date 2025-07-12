"""
Host Service

Handles business logic for Docker host management.
Separates business rules from API endpoints and database operations.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.repositories.host_repository import HostRepository
from app.models import DockerHost, User, HostTag, HostCredential, UserHostPermission
from app.schemas.docker_host import DockerHostCreate as HostCreate, DockerHostUpdate as HostUpdate
from app.services.encryption import get_encryption_service
from app.services.docker_connection_manager import get_docker_connection_manager
from app.core.exceptions import DockerConnectionError, ValidationError
from app.core.logging import logger


async def get_host_service(db: AsyncSession) -> "HostService":
    """Get host service instance"""
    return HostService(db)


class HostService:
    """Service layer for Docker host operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = HostRepository(db)
        self.encryption = get_encryption_service()
        self.connection_manager = get_docker_connection_manager()
    
    async def create_host(
        self,
        host_data: HostCreate,
        user: User
    ) -> DockerHost:
        """
        Create a new Docker host with associated entities
        
        Args:
            host_data: Host creation data
            user: User creating the host
            
        Returns:
            Created DockerHost with relationships loaded
        """
        # Prepare host data
        host_dict = host_data.dict(exclude={"tags", "credentials"})
        
        # Create the host
        host = await self.repository.create(host_dict)
        
        try:
            # Add tags if provided
            if host_data.tags:
                for tag_name in host_data.tags:
                    tag = HostTag(
                        host_id=host.id,
                        name=tag_name,
                        created_by_id=user.id
                    )
                    self.db.add(tag)
            
            # Add credentials if provided
            if host_data.credentials:
                for cred_data in host_data.credentials:
                    # Encrypt sensitive values
                    encrypted_value = self.encryption.encrypt(cred_data.value)
                    
                    credential = HostCredential(
                        host_id=host.id,
                        name=cred_data.name,
                        type=cred_data.type,
                        value=encrypted_value,
                        created_by_id=user.id
                    )
                    self.db.add(credential)
            
            # Grant creator admin permission on the host
            permission = UserHostPermission(
                user_id=user.id,
                host_id=host.id,
                permission_level="admin"
            )
            self.db.add(permission)
            
            await self.db.commit()
            
            # Reload with relationships
            return await self.repository.get_by_id(
                str(host.id),
                with_tags=True,
                with_credentials=False  # Don't load credentials by default
            )
            
        except Exception as e:
            # Rollback on any error
            await self.db.rollback()
            # The host was created, so delete it
            await self.repository.delete(str(host.id))
            raise
    
    async def update_host(
        self,
        host_id: str,
        update_data: HostUpdate,
        user: User
    ) -> DockerHost:
        """
        Update a Docker host
        
        Args:
            host_id: Host UUID
            update_data: Update data
            user: User performing the update
            
        Returns:
            Updated DockerHost
        """
        # Get update dict excluding unset fields
        update_dict = update_data.dict(exclude_unset=True)
        
        # Update the host
        host = await self.repository.update(host_id, update_dict)
        
        # Test connection if requested
        if update_data.test_connection:
            await self.test_and_update_connection(host_id, user)
        
        # Reload with relationships
        return await self.repository.get_by_id(
            host_id,
            with_tags=True
        )
    
    async def test_and_update_connection(
        self,
        host_id: str,
        user: User
    ) -> Dict[str, Any]:
        """
        Test Docker host connection and update status
        
        Args:
            host_id: Host UUID
            user: User performing the test
            
        Returns:
            Test result dictionary
        """
        host = await self.repository.get_by_id_or_404(host_id)
        
        try:
            # Test connection
            client = await self.connection_manager.get_client(
                str(host.id),
                user,
                self.db
            )
            
            # Get Docker info
            info = client.info()
            version = client.version()
            
            # Update host status
            await self.repository.update_status(
                host_id,
                status="healthy",
                version_info=version
            )
            
            logger.info(f"Host {host.name} connection test successful")
            
            return {
                "success": True,
                "message": "Connection successful",
                "docker_version": version.get("Version"),
                "api_version": version.get("ApiVersion")
            }
            
        except DockerConnectionError as e:
            # Update host status to unhealthy
            await self.repository.update_status(host_id, status="unhealthy")
            
            logger.error(f"Host {host.name} connection test failed: {e}")
            
            return {
                "success": False,
                "message": str(e),
                "error": "connection_failed"
            }
        except Exception as e:
            # Update host status to unhealthy
            await self.repository.update_status(host_id, status="unhealthy")
            
            logger.error(f"Host {host.name} connection test error: {e}")
            
            return {
                "success": False,
                "message": "Unexpected error during connection test",
                "error": str(e)
            }
    
    async def list_hosts_for_user(
        self,
        user: User,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        List hosts accessible by user with pagination
        
        Args:
            user: User requesting hosts
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Dictionary with hosts and pagination info
        """
        # Get hosts based on user permissions
        hosts = await self.repository.list_by_user_permissions(
            user,
            skip=skip,
            limit=limit,
            with_tags=True
        )
        
        # Get total count
        total = await self.repository.count_by_user_permissions(user)
        
        return {
            "hosts": hosts,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    
    async def delete_host(self, host_id: str) -> None:
        """
        Delete a Docker host and clean up connections
        
        Args:
            host_id: Host UUID
        """
        # Close any active connections
        await self.connection_manager.close_connection(host_id)
        
        # Delete from database (cascades to related entities)
        await self.repository.delete(host_id)
        
        logger.info(f"Deleted host {host_id}")
    
    async def get_host_for_user(
        self,
        host_id: str,
        user: User,
        with_credentials: bool = False
    ) -> Optional[DockerHost]:
        """
        Get host if user has permission
        
        Args:
            host_id: Host UUID
            user: User requesting the host
            with_credentials: Whether to include credentials
            
        Returns:
            DockerHost if user has permission, None otherwise
        """
        host = await self.repository.get_by_id(
            host_id,
            with_tags=True,
            with_credentials=with_credentials
        )
        
        if not host:
            return None
        
        # Check permissions
        if user.role == "admin":
            return host
        
        # Check if user has permission
        permission = await self.db.execute(
            select(UserHostPermission).where(
                and_(
                    UserHostPermission.user_id == user.id,
                    UserHostPermission.host_id == host.id
                )
            )
        )
        
        if permission.scalar_one_or_none():
            return host
        
        return None
    
    async def check_host_access(
        self,
        host_id: str,
        user: User,
        required_level: str = "viewer"
    ) -> bool:
        """
        Check if user has required permission level on host
        
        Args:
            host_id: Host UUID
            user: User to check
            required_level: Required permission level
            
        Returns:
            True if user has access, False otherwise
        """
        if user.role == "admin":
            return True
        
        permission = await self.db.execute(
            select(UserHostPermission).where(
                and_(
                    UserHostPermission.user_id == user.id,
                    UserHostPermission.host_id == host_id
                )
            )
        )
        
        user_permission = permission.scalar_one_or_none()
        if not user_permission:
            return False
        
        # Check permission hierarchy
        levels = {"viewer": 0, "operator": 1, "admin": 2}
        user_level = levels.get(user_permission.permission_level, 0)
        required = levels.get(required_level, 0)
        
        return user_level >= required