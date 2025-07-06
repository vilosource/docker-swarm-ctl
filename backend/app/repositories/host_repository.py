"""
Host Repository

Handles all database operations for Docker hosts.
Implements the Repository pattern to separate data access from business logic.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models import DockerHost, User, UserRole, HostTag, HostCredential
from app.core.exceptions import ResourceNotFoundError, ResourceConflictError


class HostRepository:
    """Repository for Docker host database operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(
        self,
        host_id: str,
        with_tags: bool = False,
        with_credentials: bool = False
    ) -> Optional[DockerHost]:
        """
        Get host by ID with optional relationships
        
        Args:
            host_id: Host UUID
            with_tags: Whether to load tags relationship
            with_credentials: Whether to load credentials relationship
            
        Returns:
            DockerHost or None if not found
        """
        query = select(DockerHost).where(DockerHost.id == host_id)
        
        if with_tags:
            query = query.options(selectinload(DockerHost.tags))
        if with_credentials:
            query = query.options(selectinload(DockerHost.credentials))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_id_or_404(
        self,
        host_id: str,
        with_tags: bool = False,
        with_credentials: bool = False
    ) -> DockerHost:
        """Get host by ID or raise ResourceNotFoundError"""
        host = await self.get_by_id(host_id, with_tags, with_credentials)
        if not host:
            raise ResourceNotFoundError("docker_host", host_id)
        return host
    
    async def get_by_name(self, name: str) -> Optional[DockerHost]:
        """Get host by name"""
        query = select(DockerHost).where(DockerHost.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def exists_by_name(self, name: str) -> bool:
        """Check if host with given name exists"""
        host = await self.get_by_name(name)
        return host is not None
    
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        with_tags: bool = False
    ) -> List[DockerHost]:
        """
        List all hosts with pagination
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            with_tags: Whether to load tags relationship
            
        Returns:
            List of DockerHost objects
        """
        query = select(DockerHost).offset(skip).limit(limit)
        
        if with_tags:
            query = query.options(selectinload(DockerHost.tags))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def list_active(
        self,
        skip: int = 0,
        limit: int = 100,
        with_tags: bool = False
    ) -> List[DockerHost]:
        """List only active hosts"""
        query = (
            select(DockerHost)
            .where(DockerHost.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        
        if with_tags:
            query = query.options(selectinload(DockerHost.tags))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def list_by_user_permissions(
        self,
        user: User,
        skip: int = 0,
        limit: int = 100,
        with_tags: bool = False
    ) -> List[DockerHost]:
        """
        List hosts accessible by user based on permissions
        
        Args:
            user: User object
            skip: Pagination offset
            limit: Pagination limit
            with_tags: Whether to load tags
            
        Returns:
            List of accessible hosts
        """
        if user.role == UserRole.admin:
            # Admins can see all hosts
            return await self.list_all(skip, limit, with_tags)
        
        # For non-admins, filter by permissions
        from app.models import UserHostPermission
        
        query = (
            select(DockerHost)
            .join(UserHostPermission)
            .where(
                and_(
                    UserHostPermission.user_id == user.id,
                    DockerHost.is_active == True
                )
            )
            .offset(skip)
            .limit(limit)
        )
        
        if with_tags:
            query = query.options(selectinload(DockerHost.tags))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create(self, host_data: Dict[str, Any]) -> DockerHost:
        """
        Create a new host
        
        Args:
            host_data: Dictionary with host attributes
            
        Returns:
            Created DockerHost object
        """
        # Check for duplicate name
        if await self.exists_by_name(host_data.get("name")):
            raise ResourceConflictError(
                "docker_host",
                f"Host with name '{host_data.get('name')}' already exists"
            )
        
        host = DockerHost(**host_data)
        self.db.add(host)
        await self.db.commit()
        await self.db.refresh(host)
        return host
    
    async def update(
        self,
        host_id: str,
        update_data: Dict[str, Any]
    ) -> DockerHost:
        """
        Update host attributes
        
        Args:
            host_id: Host UUID
            update_data: Dictionary with attributes to update
            
        Returns:
            Updated DockerHost object
        """
        host = await self.get_by_id_or_404(host_id)
        
        # Check for duplicate name if name is being changed
        if "name" in update_data and update_data["name"] != host.name:
            if await self.exists_by_name(update_data["name"]):
                raise ResourceConflictError(
                    "docker_host",
                    f"Host with name '{update_data['name']}' already exists"
                )
        
        for key, value in update_data.items():
            if hasattr(host, key):
                setattr(host, key, value)
        
        await self.db.commit()
        await self.db.refresh(host)
        return host
    
    async def update_status(
        self,
        host_id: str,
        status: str,
        version_info: Optional[Dict[str, Any]] = None
    ) -> DockerHost:
        """
        Update host connection status
        
        Args:
            host_id: Host UUID
            status: New status (healthy/unhealthy)
            version_info: Optional Docker version information
            
        Returns:
            Updated DockerHost object
        """
        update_data = {"status": status}
        
        if version_info:
            update_data.update({
                "docker_version": version_info.get("Version"),
                "api_version": version_info.get("ApiVersion"),
                "os_info": version_info.get("Os"),
                "arch": version_info.get("Arch")
            })
        
        return await self.update(host_id, update_data)
    
    async def delete(self, host_id: str) -> None:
        """
        Delete a host
        
        Args:
            host_id: Host UUID
        """
        host = await self.get_by_id_or_404(host_id)
        await self.db.delete(host)
        await self.db.commit()
    
    async def add_tag(self, host_id: str, tag: HostTag) -> None:
        """Add a tag to a host"""
        host = await self.get_by_id_or_404(host_id)
        host.tags.append(tag)
        await self.db.commit()
    
    async def add_credential(self, host_id: str, credential: HostCredential) -> None:
        """Add a credential to a host"""
        host = await self.get_by_id_or_404(host_id)
        host.credentials.append(credential)
        await self.db.commit()
    
    async def count_all(self) -> int:
        """Get total count of hosts"""
        query = select(DockerHost).count()
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def count_by_user_permissions(self, user: User) -> int:
        """Get count of hosts accessible by user"""
        if user.role == UserRole.admin:
            return await self.count_all()
        
        from app.models import UserHostPermission
        
        query = (
            select(DockerHost)
            .join(UserHostPermission)
            .where(
                and_(
                    UserHostPermission.user_id == user.id,
                    DockerHost.is_active == True
                )
            )
            .count()
        )
        result = await self.db.execute(query)
        return result.scalar() or 0