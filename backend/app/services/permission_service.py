"""
Permission Service

Centralized service for handling all permission and authorization logic,
implementing the Policy pattern for different permission rules.
"""

from typing import Optional, List, Dict, Any, Protocol
from enum import Enum
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import User, UserRole, DockerHost, UserHostPermission
from app.core.exceptions import AuthorizationError
from app.core.logging import logger
from app.core.feature_flags import FeatureFlag, is_feature_enabled


class Permission(str, Enum):
    """Enumeration of all permissions in the system"""
    # Container permissions
    CONTAINER_VIEW = "container.view"
    CONTAINER_CREATE = "container.create"
    CONTAINER_START = "container.start"
    CONTAINER_STOP = "container.stop"
    CONTAINER_DELETE = "container.delete"
    CONTAINER_EXEC = "container.exec"
    CONTAINER_LOGS = "container.logs"
    CONTAINER_STATS = "container.stats"
    
    # Image permissions
    IMAGE_VIEW = "image.view"
    IMAGE_PULL = "image.pull"
    IMAGE_DELETE = "image.delete"
    IMAGE_BUILD = "image.build"
    
    # System permissions
    SYSTEM_INFO = "system.info"
    SYSTEM_PRUNE = "system.prune"
    SYSTEM_ADMIN = "system.admin"
    
    # Host permissions
    HOST_VIEW = "host.view"
    HOST_CREATE = "host.create"
    HOST_UPDATE = "host.update"
    HOST_DELETE = "host.delete"
    HOST_CONNECT = "host.connect"
    
    # User permissions
    USER_VIEW = "user.view"
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"


class IPermissionPolicy(Protocol):
    """Interface for permission policies"""
    
    async def check_permission(
        self,
        user: User,
        permission: Permission,
        context: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """Check if user has the specified permission"""
        ...


class RoleBasedPolicy:
    """Role-based permission policy"""
    
    # Permission mappings by role
    ROLE_PERMISSIONS = {
        UserRole.viewer: [
            Permission.CONTAINER_VIEW,
            Permission.CONTAINER_LOGS,
            Permission.CONTAINER_STATS,
            Permission.IMAGE_VIEW,
            Permission.SYSTEM_INFO,
            Permission.HOST_VIEW,
        ],
        UserRole.operator: [
            # Includes all viewer permissions
            Permission.CONTAINER_VIEW,
            Permission.CONTAINER_LOGS,
            Permission.CONTAINER_STATS,
            Permission.IMAGE_VIEW,
            Permission.SYSTEM_INFO,
            Permission.HOST_VIEW,
            # Additional operator permissions
            Permission.CONTAINER_CREATE,
            Permission.CONTAINER_START,
            Permission.CONTAINER_STOP,
            Permission.CONTAINER_DELETE,
            Permission.CONTAINER_EXEC,
            Permission.IMAGE_PULL,
            Permission.IMAGE_DELETE,
            Permission.HOST_CONNECT,
        ],
        UserRole.admin: [
            # Admin has all permissions
            permission for permission in Permission
        ]
    }
    
    async def check_permission(
        self,
        user: User,
        permission: Permission,
        context: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """Check permission based on user role"""
        allowed_permissions = self.ROLE_PERMISSIONS.get(user.role, [])
        return permission in allowed_permissions


class HostSpecificPolicy:
    """Host-specific permission policy"""
    
    async def check_permission(
        self,
        user: User,
        permission: Permission,
        context: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """Check permission for host-specific operations"""
        host_id = context.get("host_id")
        if not host_id:
            # No host specified, check default permissions
            return True
        
        # Admin always has access
        if user.role == UserRole.admin:
            return True
        
        # Check host-specific permissions
        result = await db.execute(
            select(UserHostPermission).where(
                UserHostPermission.user_id == user.id,
                UserHostPermission.host_id == host_id
            )
        )
        host_permission = result.scalar_one_or_none()
        
        if not host_permission:
            return False
        
        # Map permission levels to allowed operations
        if host_permission.permission_level == "viewer":
            allowed = [
                Permission.CONTAINER_VIEW,
                Permission.CONTAINER_LOGS,
                Permission.CONTAINER_STATS,
                Permission.IMAGE_VIEW,
                Permission.HOST_VIEW,
            ]
        elif host_permission.permission_level == "operator":
            allowed = [
                Permission.CONTAINER_VIEW,
                Permission.CONTAINER_LOGS,
                Permission.CONTAINER_STATS,
                Permission.CONTAINER_CREATE,
                Permission.CONTAINER_START,
                Permission.CONTAINER_STOP,
                Permission.CONTAINER_DELETE,
                Permission.CONTAINER_EXEC,
                Permission.IMAGE_VIEW,
                Permission.IMAGE_PULL,
                Permission.IMAGE_DELETE,
                Permission.HOST_VIEW,
                Permission.HOST_CONNECT,
            ]
        elif host_permission.permission_level == "admin":
            # Host admin has all host-related permissions
            return True
        else:
            allowed = []
        
        return permission in allowed


class OwnershipPolicy:
    """Resource ownership permission policy"""
    
    async def check_permission(
        self,
        user: User,
        permission: Permission,
        context: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """Check permission based on resource ownership"""
        # For now, we don't track container/image ownership
        # This could be extended to check container labels, etc.
        return True


class PermissionService:
    """Service for checking permissions with multiple policies"""
    
    def __init__(self):
        self.policies: List[IPermissionPolicy] = [
            RoleBasedPolicy(),
            HostSpecificPolicy(),
            OwnershipPolicy(),
        ]
        self._cache: Dict[str, bool] = {}
    
    async def check_permission(
        self,
        user: User,
        permission: Permission,
        context: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Check if user has the specified permission
        
        Args:
            user: User to check
            permission: Permission to check
            context: Additional context (e.g., host_id, resource_id)
            db: Database session for queries
            
        Returns:
            True if user has permission, False otherwise
        """
        if not is_feature_enabled(FeatureFlag.USE_PERMISSION_SERVICE):
            # Fall back to simple role check
            return self._legacy_check(user, permission)
        
        context = context or {}
        
        # Generate cache key
        cache_key = f"{user.id}:{permission}:{context.get('host_id', 'default')}"
        
        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Check all policies (all must pass)
        for policy in self.policies:
            if db and not await policy.check_permission(user, permission, context, db):
                self._cache[cache_key] = False
                return False
        
        self._cache[cache_key] = True
        return True
    
    async def require_permission(
        self,
        user: User,
        permission: Permission,
        context: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> None:
        """
        Require user to have permission, raise exception if not
        
        Raises:
            AuthorizationError if user lacks permission
        """
        if not await self.check_permission(user, permission, context, db):
            logger.warning(
                f"Permission denied for user {user.username} ({user.id}): {permission}"
            )
            raise AuthorizationError(
                f"You don't have permission to perform this action: {permission}"
            )
    
    async def get_user_permissions(
        self,
        user: User,
        host_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> List[Permission]:
        """Get all permissions for a user"""
        permissions = []
        context = {"host_id": host_id} if host_id else {}
        
        for permission in Permission:
            if await self.check_permission(user, permission, context, db):
                permissions.append(permission)
        
        return permissions
    
    async def get_accessible_hosts(
        self,
        user: User,
        db: AsyncSession
    ) -> List[DockerHost]:
        """Get all hosts user has access to"""
        if user.role == UserRole.admin:
            # Admin has access to all active hosts
            result = await db.execute(
                select(DockerHost)
                .where(DockerHost.is_active == True)
                .options(selectinload(DockerHost.tags))
            )
            return list(result.scalars().all())
        
        # Get hosts with explicit permissions
        result = await db.execute(
            select(DockerHost)
            .join(UserHostPermission)
            .where(
                UserHostPermission.user_id == user.id,
                DockerHost.is_active == True
            )
            .options(selectinload(DockerHost.tags))
        )
        return list(result.scalars().all())
    
    def clear_cache(self, user_id: Optional[str] = None):
        """Clear permission cache"""
        if user_id:
            # Clear cache for specific user
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            # Clear entire cache
            self._cache.clear()
    
    def _legacy_check(self, user: User, permission: Permission) -> bool:
        """Legacy permission check based on role only"""
        role_permissions = RoleBasedPolicy.ROLE_PERMISSIONS.get(user.role, [])
        return permission in role_permissions


# Global instance
_permission_service = PermissionService()


async def check_permission(
    user: User,
    permission: Permission,
    context: Optional[Dict[str, Any]] = None,
    db: Optional[AsyncSession] = None
) -> bool:
    """Check if user has permission (convenience function)"""
    return await _permission_service.check_permission(user, permission, context, db)


async def require_permission(
    user: User,
    permission: Permission,
    context: Optional[Dict[str, Any]] = None,
    db: Optional[AsyncSession] = None
) -> None:
    """Require user to have permission (convenience function)"""
    await _permission_service.require_permission(user, permission, context, db)


def get_permission_service() -> PermissionService:
    """Get the permission service instance"""
    return _permission_service