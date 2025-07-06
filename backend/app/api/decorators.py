"""
Common decorators for API endpoints

These decorators implement cross-cutting concerns like audit logging,
error handling, and permission checking to reduce code duplication.
"""

from functools import wraps
from typing import Callable, Optional, Dict, Any, List, Type, Union
from fastapi import HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import traceback

from app.core.exceptions import DockerOperationError, AuthorizationError, DockerConnectionError
from app.services.audit import AuditService
from app.models.user import User
from app.db.session import get_db
from app.core.logging import logger
from app.core.feature_flags import FeatureFlag, is_feature_enabled


def audit_operation(
    action: str,
    resource_type: Optional[str] = None,
    extract_resource_id: Optional[Callable[[Any], str]] = None
):
    """
    Decorator to automatically audit log API operations
    
    Args:
        action: The action being performed (e.g., "container.create")
        resource_type: Type of resource being operated on
        extract_resource_id: Function to extract resource ID from response
    
    Usage:
        @audit_operation("container.create", "container", lambda r: r.id)
        async def create_container(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract common dependencies from kwargs
            request = kwargs.get('request')
            user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            # Skip if feature flag is disabled
            if not is_feature_enabled(FeatureFlag.USE_DECORATOR_PATTERN):
                return await func(*args, **kwargs)
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Log the audit event if we have necessary dependencies
                if request and user and db:
                    audit_service = AuditService(db)
                    
                    # Extract resource ID if extractor provided
                    resource_id = None
                    if extract_resource_id and result:
                        try:
                            resource_id = extract_resource_id(result)
                        except Exception as e:
                            logger.warning(f"Failed to extract resource ID: {e}")
                    
                    # Build audit details
                    details = {
                        "endpoint": str(request.url),
                        "method": request.method,
                    }
                    
                    # Add request body if it's a write operation
                    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
                        try:
                            if hasattr(request, '_json'):
                                details["request_body"] = request._json
                        except Exception:
                            pass
                    
                    # Log the audit event
                    await audit_service.log(
                        user=user,
                        action=action,
                        request=request,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        details=details
                    )
                
                return result
                
            except Exception as e:
                # Log error in audit trail
                if request and user and db:
                    audit_service = AuditService(db)
                    await audit_service.log(
                        user=user,
                        action=action,
                        request=request,
                        resource_type=resource_type,
                        details={
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )
                raise
                
        return wrapper
    return decorator


def handle_docker_errors(
    default_status_code: int = 400,
    error_mapping: Optional[Dict[Type[Exception], int]] = None
):
    """
    Decorator to handle Docker-related errors consistently
    
    Args:
        default_status_code: Default HTTP status code for errors
        error_mapping: Custom mapping of exception types to status codes
    
    Usage:
        @handle_docker_errors(
            error_mapping={
                DockerOperationError: 400,
                AuthorizationError: 403,
                DockerConnectionError: 503
            }
        )
        async def container_operation(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip if feature flag is disabled
            if not is_feature_enabled(FeatureFlag.USE_DECORATOR_PATTERN):
                return await func(*args, **kwargs)
            
            # Default error mappings
            default_mappings = {
                AuthorizationError: 403,
                DockerOperationError: 400,
                DockerConnectionError: 503,
            }
            
            # Merge with custom mappings
            mappings = {**default_mappings, **(error_mapping or {})}
            
            try:
                return await func(*args, **kwargs)
                
            except HTTPException:
                # Re-raise FastAPI exceptions as-is
                raise
                
            except Exception as e:
                # Log the full traceback
                logger.error(f"Error in {func.__name__}: {traceback.format_exc()}")
                
                # Determine status code
                status_code = default_status_code
                for exc_type, code in mappings.items():
                    if isinstance(e, exc_type):
                        status_code = code
                        break
                
                # Raise appropriate HTTP exception
                raise HTTPException(
                    status_code=status_code,
                    detail=str(e)
                )
                
        return wrapper
    return decorator


def require_host_permission(
    permission_level: str = "viewer",
    host_id_param: str = "host_id",
    use_default_if_none: bool = True
):
    """
    Decorator to check host-specific permissions
    
    Args:
        permission_level: Required permission level (viewer, operator, admin)
        host_id_param: Name of the parameter containing host ID
        use_default_if_none: Whether to use default host if host_id is None
    
    Usage:
        @require_host_permission("operator", host_id_param="host_id")
        async def container_create(host_id: Optional[str], ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip if feature flag is disabled
            if not is_feature_enabled(FeatureFlag.USE_DECORATOR_PATTERN):
                return await func(*args, **kwargs)
            
            # Extract dependencies
            user: Optional[User] = kwargs.get('current_user')
            db: Optional[AsyncSession] = kwargs.get('db')
            host_id = kwargs.get(host_id_param)
            
            if not user or not db:
                logger.error("Missing user or db in require_host_permission")
                return await func(*args, **kwargs)
            
            # Import here to avoid circular imports
            from app.services.docker_connection_manager import get_docker_connection_manager
            from app.models import UserRole
            
            # Admin users bypass permission checks
            if user.role == UserRole.admin:
                return await func(*args, **kwargs)
            
            # Get connection manager
            connection_manager = get_docker_connection_manager()
            
            # If no host_id and use_default_if_none, get default
            if not host_id and use_default_if_none:
                try:
                    host_id = await connection_manager.get_default_host_id(user, db)
                    # Update kwargs with the default host_id
                    kwargs[host_id_param] = host_id
                except Exception as e:
                    raise AuthorizationError(f"Failed to get default host: {str(e)}")
            
            # Check permissions
            if host_id:
                try:
                    await connection_manager._check_permissions(host_id, user, db)
                except AuthorizationError:
                    raise HTTPException(
                        status_code=403,
                        detail=f"You don't have {permission_level} permission for this host"
                    )
            
            return await func(*args, **kwargs)
            
        return wrapper
    return decorator


def validate_docker_config(
    required_fields: Optional[List[str]] = None,
    optional_fields: Optional[List[str]] = None
):
    """
    Decorator to validate Docker configuration objects
    
    Args:
        required_fields: List of required fields in the config
        optional_fields: List of optional fields (for documentation)
    
    Usage:
        @validate_docker_config(
            required_fields=["image"],
            optional_fields=["name", "command", "environment"]
        )
        async def create_container(config: ContainerCreate, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip if feature flag is disabled
            if not is_feature_enabled(FeatureFlag.USE_DECORATOR_PATTERN):
                return await func(*args, **kwargs)
            
            # Find config object in kwargs
            config = None
            for key, value in kwargs.items():
                if hasattr(value, '__dict__') and any(hasattr(value, field) for field in (required_fields or [])):
                    config = value
                    break
            
            if config and required_fields:
                missing_fields = []
                for field in required_fields:
                    if not hasattr(config, field) or getattr(config, field) is None:
                        missing_fields.append(field)
                
                if missing_fields:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Missing required fields: {', '.join(missing_fields)}"
                    )
            
            return await func(*args, **kwargs)
            
        return wrapper
    return decorator


def async_timeout(seconds: int = 30):
    """
    Decorator to add timeout to async operations
    
    Args:
        seconds: Timeout in seconds
    
    Usage:
        @async_timeout(60)
        async def long_running_operation(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=504,
                    detail=f"Operation timed out after {seconds} seconds"
                )
        return wrapper
    return decorator