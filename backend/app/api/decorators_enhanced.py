"""
Enhanced API Decorators

Provides decorators to reduce boilerplate in API endpoints.
"""

import functools
from typing import Callable, Optional, Dict, Any, TypeVar, ParamSpec
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthorizationError, 
    DockerOperationError,
    ValidationError,
    ResourceNotFoundError,
    ResourceConflictError,
    ExternalServiceError
)
from app.services.audit import AuditService
from app.models import User
from app.core.logging import logger


P = ParamSpec('P')
T = TypeVar('T')


def handle_api_errors(
    operation_name: Optional[str] = None,
    success_status_code: int = 200
):
    """
    Decorator to handle common API errors with proper HTTP status codes
    
    Args:
        operation_name: Name of the operation for logging
        success_status_code: HTTP status code for successful response
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            op_name = operation_name or func.__name__
            try:
                result = await func(*args, **kwargs)
                return result
            except HTTPException:
                # Let HTTPException pass through unchanged
                raise
            except AuthorizationError as e:
                logger.warning(f"{op_name} failed - Authorization: {e}")
                raise HTTPException(status_code=403, detail=e.message)
            except DockerOperationError as e:
                logger.error(f"{op_name} failed - Docker operation: {e}")
                raise HTTPException(status_code=400, detail=e.message)
            except ResourceNotFoundError as e:
                logger.warning(f"{op_name} failed - Not found: {e}")
                raise HTTPException(status_code=404, detail=e.message)
            except ResourceConflictError as e:
                logger.warning(f"{op_name} failed - Conflict: {e}")
                raise HTTPException(status_code=409, detail=e.message)
            except ValidationError as e:
                logger.warning(f"{op_name} failed - Validation: {e}")
                raise HTTPException(status_code=422, detail=e.message)
            except ExternalServiceError as e:
                logger.error(f"{op_name} failed - External service: {e}")
                raise HTTPException(status_code=502, detail=e.message)
            except Exception as e:
                logger.error(f"{op_name} failed - Unexpected error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal server error during {op_name}: {str(e)}"
                )
        return wrapper
    return decorator


def audit_action(
    action: str,
    resource_type: str = "container",
    get_resource_id: Optional[Callable] = None,
    include_details: Optional[Callable] = None
):
    """
    Decorator to automatically log actions to audit trail
    
    Args:
        action: Action name (e.g., "container.start")
        resource_type: Type of resource being acted upon
        get_resource_id: Function to extract resource ID from args/kwargs
        include_details: Function to extract additional details for audit log
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Extract common dependencies
            request: Optional[Request] = None
            current_user: Optional[User] = None
            db: Optional[AsyncSession] = None
            
            # Find these in kwargs
            for key, value in kwargs.items():
                if key == "request" and isinstance(value, Request):
                    request = value
                elif key == "current_user" and hasattr(value, "id"):
                    current_user = value
                elif key == "db" and hasattr(value, "execute"):
                    db = value
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Log to audit trail if we have required dependencies
            if all([request, current_user, db]):
                try:
                    # Extract resource ID
                    resource_id = None
                    if get_resource_id:
                        resource_id = get_resource_id(*args, **kwargs)
                    else:
                        # Try common patterns
                        resource_id = kwargs.get("container_id") or kwargs.get("resource_id")
                    
                    # Extract additional details
                    details = {}
                    if include_details:
                        details = include_details(*args, **kwargs) or {}
                    
                    # Get host_id if available
                    host_id = kwargs.get("host_id")
                    
                    # Log the action
                    audit_service = AuditService(db)
                    await audit_service.log(
                        user=current_user,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        host_id=host_id,
                        details=details,
                        request=request
                    )
                except Exception as e:
                    # Don't fail the request if audit logging fails
                    logger.error(f"Failed to log audit action {action}: {e}")
            
            return result
        return wrapper
    return decorator


def with_standard_docker_params(func: Callable) -> Callable:
    """
    Decorator to inject standard Docker endpoint parameters.
    Reduces boilerplate for common parameters.
    """
    # This is a marker decorator - the actual injection happens in the endpoint
    func._has_standard_params = True
    return func


def standard_response(
    message_template: str,
    extract_params: Optional[Callable] = None
):
    """
    Decorator to standardize success responses
    
    Args:
        message_template: Template for success message (e.g., "Container {container_id} started")
        extract_params: Function to extract parameters for message formatting
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Dict[str, str]:
            # Execute the function
            await func(*args, **kwargs)
            
            # Build response message
            params = {}
            if extract_params:
                params = extract_params(*args, **kwargs) or {}
            else:
                # Try common patterns
                if "container_id" in kwargs:
                    params["container_id"] = kwargs["container_id"]
                if "action" in message_template:
                    # Extract action from function name (e.g., "start_container" -> "started")
                    action = func.__name__.replace("_container", "").replace("_", " ")
                    if action == "remove":
                        action = "removed"
                    elif action.endswith("e"):
                        action = action + "d"
                    else:
                        action = action + "ed"
                    params["action"] = action
            
            message = message_template.format(**params)
            return {"message": message}
        return wrapper
    return decorator


class ContainerConfigBuilder:
    """Helper class to build container configurations"""
    
    @staticmethod
    def from_create_schema(config) -> Dict[str, Any]:
        """
        Build Docker container configuration from ContainerCreate schema
        
        Args:
            config: ContainerCreate schema instance
            
        Returns:
            Dictionary ready for Docker API
        """
        # Start with required fields
        container_config = {
            "image": config.image,
            "detach": True
        }
        
        # Add optional fields if present
        optional_mappings = {
            "name": "name",
            "command": "command",
            "environment": "environment",
            "ports": "ports",
            "volumes": "volumes",
            "labels": "labels"
        }
        
        for schema_field, docker_field in optional_mappings.items():
            value = getattr(config, schema_field, None)
            if value is not None:
                container_config[docker_field] = value
        
        # Handle restart policy
        if config.restart_policy:
            container_config["restart_policy"] = {"Name": config.restart_policy}
        
        # Handle any additional advanced options
        if hasattr(config, "host_config") and config.host_config:
            container_config.update(config.host_config)
        
        return container_config


def validate_resource_access(
    resource_type: str,
    permission_level: str = "viewer"
):
    """
    Decorator to validate user has access to a resource
    
    Args:
        resource_type: Type of resource (e.g., "container", "image")
        permission_level: Required permission level
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Get current user
            current_user = kwargs.get("current_user")
            if not current_user:
                raise AuthorizationError("Authentication required")
            
            # Check permission level
            role_hierarchy = {"viewer": 0, "operator": 1, "admin": 2}
            user_level = role_hierarchy.get(current_user.role, 0)
            required_level = role_hierarchy.get(permission_level, 0)
            
            if user_level < required_level:
                raise AuthorizationError(
                    f"Insufficient permissions. Required: {permission_level}, "
                    f"Current: {current_user.role}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator