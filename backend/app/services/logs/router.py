"""
Log source router for directing log requests to appropriate providers.

This module provides a central registry for log sources and routes
requests to the appropriate provider based on the source type.
"""

from typing import Dict, Optional, Type
from app.core.exceptions import ResourceNotFoundError
from .base import LogSource, LogSourceType


class LogRouter:
    """
    Central router for log sources.
    
    This class maintains a registry of available log sources and
    routes requests to the appropriate provider based on source type.
    """
    
    def __init__(self):
        """Initialize the log router."""
        self._providers: Dict[LogSourceType, Type[LogSource]] = {}
        self._provider_instances: Dict[LogSourceType, LogSource] = {}
    
    def register_provider(
        self,
        source_type: LogSourceType,
        provider_class: Type[LogSource]
    ):
        """
        Register a log source provider.
        
        Args:
            source_type: The type of log source
            provider_class: The provider class (not instance)
        """
        self._providers[source_type] = provider_class
    
    def get_provider(
        self,
        source_type: LogSourceType,
        **kwargs
    ) -> LogSource:
        """
        Get a log source provider instance.
        
        Args:
            source_type: The type of log source
            **kwargs: Arguments to pass to provider constructor
            
        Returns:
            LogSource provider instance
            
        Raises:
            ValueError: If source type is not registered
        """
        if source_type not in self._providers:
            raise ValueError(f"Unknown log source type: {source_type}")
        
        # Create instance if not already created
        # Note: In a real implementation, we might want different instances
        # per connection or user, but for now we'll use singletons
        if source_type not in self._provider_instances:
            provider_class = self._providers[source_type]
            self._provider_instances[source_type] = provider_class(**kwargs)
        
        return self._provider_instances[source_type]
    
    def get_registered_types(self) -> list[LogSourceType]:
        """Get list of registered log source types."""
        return list(self._providers.keys())
    
    def is_registered(self, source_type: LogSourceType) -> bool:
        """Check if a source type is registered."""
        return source_type in self._providers


# Global router instance
_log_router: Optional[LogRouter] = None


def get_log_router() -> LogRouter:
    """Get the global log router instance."""
    global _log_router
    if _log_router is None:
        _log_router = LogRouter()
        # Register default providers
        _register_default_providers(_log_router)
    return _log_router


def _register_default_providers(router: LogRouter):
    """Register default log providers."""
    # Import here to avoid circular imports
    from .providers.container_logs import ContainerLogSource
    from .providers.service_logs import ServiceLogSource
    
    router.register_provider(LogSourceType.CONTAINER, ContainerLogSource)
    router.register_provider(LogSourceType.SERVICE, ServiceLogSource)