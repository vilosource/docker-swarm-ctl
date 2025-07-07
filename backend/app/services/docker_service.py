"""
Refactored Docker Service

Uses the unified DockerOperationExecutor to eliminate code duplication
between single and multi-host implementations.
"""

from typing import List, Optional, Dict, Any
from app.services.docker_operation_executor import (
    DockerOperationExecutor,
    SingleHostAdapter,
    MultiHostAdapter,
    DockerClientAdapter
)
from app.services.docker_client import get_docker_client
from app.services.docker_connection_manager import get_docker_connection_manager
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession


class ContainerData:
    """Data class for container information"""
    def __init__(self, container, host_id: Optional[str] = None):
        self.container = container
        self.host_id = host_id
        
    @property
    def id(self) -> str:
        return self.container.id[:12]
    
    @property
    def name(self) -> str:
        return self.container.name
    
    @property
    def image(self) -> str:
        tags = self.container.image.tags
        return tags[0] if tags else self.container.image.id
    
    @property
    def status(self) -> str:
        return self.container.status
    
    @property
    def state(self) -> str:
        return self.container.attrs["State"]["Status"]
    
    @property
    def created(self) -> str:
        return self.container.attrs["Created"]
    
    @property
    def ports(self) -> Dict[str, Any]:
        return self.container.attrs["NetworkSettings"]["Ports"] or {}
    
    @property
    def labels(self) -> Dict[str, str]:
        return self.container.labels or {}


class UnifiedDockerService:
    """
    Unified Docker service that works for both single and multi-host deployments
    
    This replaces both SingleHostDockerService and MultiHostDockerService
    with a single implementation using the Adapter pattern.
    """
    
    def __init__(self, executor: DockerOperationExecutor):
        self._executor = executor
    
    async def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[ContainerData]:
        """List containers from the specified or default host"""
        container_tuples = await self._executor.list_containers(all, filters, host_id)
        return [ContainerData(container, host_id) for container, host_id in container_tuples]
    
    async def get_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> ContainerData:
        """Get a specific container"""
        container, resolved_host_id = await self._executor.get_container(container_id, host_id)
        return ContainerData(container, resolved_host_id)
    
    async def create_container(
        self,
        config: Dict[str, Any],
        host_id: Optional[str] = None
    ) -> ContainerData:
        """Create a new container"""
        container, resolved_host_id = await self._executor.create_container(config, host_id)
        return ContainerData(container, resolved_host_id)
    
    async def start_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Start a container"""
        await self._executor.start_container(container_id, host_id)
    
    async def stop_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        """Stop a container"""
        await self._executor.stop_container(container_id, timeout, host_id)
    
    async def restart_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        """Restart a container"""
        await self._executor.restart_container(container_id, timeout, host_id)
    
    async def remove_container(
        self,
        container_id: str,
        force: bool = False,
        volumes: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a container"""
        await self._executor.remove_container(container_id, force, volumes, host_id)
    
    async def get_container_logs(
        self,
        container_id: str,
        lines: int = 100,
        timestamps: bool = False,
        host_id: Optional[str] = None
    ) -> str:
        """Get container logs"""
        return await self._executor.get_container_logs(container_id, lines, timestamps, host_id)
    
    async def get_container_stats(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get container statistics"""
        return await self._executor.get_container_stats(container_id, False, host_id)
    
    async def inspect_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inspect a container"""
        return await self._executor.inspect_container(container_id, host_id)
    
    async def get_system_info(
        self,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get Docker system information"""
        return await self._executor.get_system_info(host_id)
    
    async def get_disk_usage(
        self,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get disk usage information"""
        return await self._executor.get_disk_usage(host_id)
    
    async def get_version(
        self,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get Docker version information"""
        return await self._executor.get_version(host_id)


class DockerServiceFactory:
    """
    Factory for creating Docker service instances
    
    Now creates UnifiedDockerService with appropriate adapter
    """
    
    @staticmethod
    def create_for_single_host() -> UnifiedDockerService:
        """Create service for single-host deployment"""
        docker_client = get_docker_client()
        adapter = SingleHostAdapter(docker_client)
        executor = DockerOperationExecutor(adapter)
        return UnifiedDockerService(executor)
    
    @staticmethod
    def create_for_multi_host(
        user: User,
        db: AsyncSession
    ) -> UnifiedDockerService:
        """Create service for multi-host deployment"""
        connection_manager = get_docker_connection_manager()
        adapter = MultiHostAdapter(connection_manager, user, db)
        executor = DockerOperationExecutor(adapter)
        return UnifiedDockerService(executor)
    
    @staticmethod
    def create(
        user: Optional[User] = None,
        db: Optional[AsyncSession] = None,
        multi_host: bool = True
    ) -> UnifiedDockerService:
        """
        Create appropriate Docker service based on deployment type
        
        Args:
            user: Current user (required for multi-host)
            db: Database session (required for multi-host)
            multi_host: Whether to use multi-host implementation
            
        Returns:
            UnifiedDockerService instance
        """
        if multi_host and user and db:
            return DockerServiceFactory.create_for_multi_host(user, db)
        else:
            return DockerServiceFactory.create_for_single_host()


# For backward compatibility, keep the same interface names
IDockerService = UnifiedDockerService
SingleHostDockerService = UnifiedDockerService  # They're now the same
MultiHostDockerService = UnifiedDockerService   # They're now the same