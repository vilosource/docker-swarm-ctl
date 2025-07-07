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


class VolumeData:
    """Data class for volume information"""
    def __init__(self, volume, host_id: Optional[str] = None):
        self.volume = volume
        self.host_id = host_id
        self._attrs = volume.attrs if hasattr(volume, 'attrs') else {}
    
    @property
    def name(self) -> str:
        return self._attrs.get("Name", self.volume.name if hasattr(self.volume, 'name') else "")
    
    @property
    def driver(self) -> str:
        return self._attrs.get("Driver", "")
    
    @property
    def mountpoint(self) -> str:
        return self._attrs.get("Mountpoint", "")
    
    @property
    def created_at(self) -> Optional[str]:
        return self._attrs.get("CreatedAt")
    
    @property
    def status(self) -> Optional[Dict[str, Any]]:
        return self._attrs.get("Status")
    
    @property
    def labels(self) -> Dict[str, str]:
        return self._attrs.get("Labels", {})
    
    @property
    def scope(self) -> str:
        return self._attrs.get("Scope", "local")
    
    @property
    def options(self) -> Optional[Dict[str, str]]:
        return self._attrs.get("Options")


class NetworkData:
    """Data class for network information"""
    def __init__(self, network, host_id: Optional[str] = None):
        self.network = network
        self.host_id = host_id
        self._attrs = network.attrs if hasattr(network, 'attrs') else {}
    
    @property
    def id(self) -> str:
        return self._attrs.get("Id", self.network.id if hasattr(self.network, 'id') else "")
    
    @property
    def name(self) -> str:
        return self._attrs.get("Name", self.network.name if hasattr(self.network, 'name') else "")
    
    @property
    def driver(self) -> str:
        return self._attrs.get("Driver", "")
    
    @property
    def scope(self) -> str:
        return self._attrs.get("Scope", "")
    
    @property
    def ipam(self) -> Optional[Dict[str, Any]]:
        return self._attrs.get("IPAM")
    
    @property
    def internal(self) -> bool:
        return self._attrs.get("Internal", False)
    
    @property
    def attachable(self) -> bool:
        return self._attrs.get("Attachable", False)
    
    @property
    def ingress(self) -> bool:
        return self._attrs.get("Ingress", False)
    
    @property
    def containers(self) -> Dict[str, Dict[str, Any]]:
        return self._attrs.get("Containers", {})
    
    @property
    def options(self) -> Optional[Dict[str, str]]:
        return self._attrs.get("Options")
    
    @property
    def labels(self) -> Dict[str, str]:
        return self._attrs.get("Labels", {})
    
    @property
    def created(self) -> Optional[str]:
        return self._attrs.get("Created")
    
    @property
    def enable_ipv6(self) -> bool:
        return self._attrs.get("EnableIPv6", False)


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
    
    # Volume operations
    async def list_volumes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[VolumeData]:
        """List volumes"""
        volume_tuples = await self._executor.list_volumes(filters, host_id)
        return [VolumeData(volume, host_id) for volume, host_id in volume_tuples]
    
    async def create_volume(
        self,
        name: Optional[str] = None,
        driver: str = "local",
        driver_opts: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        host_id: Optional[str] = None
    ) -> VolumeData:
        """Create a volume"""
        volume, resolved_host_id = await self._executor.create_volume(name, driver, driver_opts, labels, host_id)
        return VolumeData(volume, resolved_host_id)
    
    async def get_volume(
        self,
        volume_id: str,
        host_id: Optional[str] = None
    ) -> VolumeData:
        """Get a volume"""
        volume, resolved_host_id = await self._executor.get_volume(volume_id, host_id)
        return VolumeData(volume, resolved_host_id)
    
    async def remove_volume(
        self,
        volume_id: str,
        force: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a volume"""
        await self._executor.remove_volume(volume_id, force, host_id)
    
    async def prune_volumes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prune unused volumes"""
        return await self._executor.prune_volumes(filters, host_id)
    
    # Network operations
    async def list_networks(
        self,
        names: Optional[List[str]] = None,
        ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[NetworkData]:
        """List networks"""
        network_tuples = await self._executor.list_networks(names, ids, filters, host_id)
        return [NetworkData(network, resolved_host_id) for network, resolved_host_id in network_tuples]
    
    async def create_network(
        self,
        name: str,
        driver: Optional[str] = None,
        options: Optional[Dict[str, str]] = None,
        ipam: Optional[Dict[str, Any]] = None,
        check_duplicate: bool = True,
        internal: bool = False,
        labels: Optional[Dict[str, str]] = None,
        enable_ipv6: bool = False,
        attachable: bool = True,
        scope: Optional[str] = None,
        host_id: Optional[str] = None
    ) -> NetworkData:
        """Create a network"""
        network, resolved_host_id = await self._executor.create_network(
            name, driver, options, ipam, check_duplicate, 
            internal, labels, enable_ipv6, attachable, scope, host_id
        )
        return NetworkData(network, resolved_host_id)
    
    async def get_network(
        self,
        network_id: str,
        host_id: Optional[str] = None
    ) -> NetworkData:
        """Get a network"""
        network, resolved_host_id = await self._executor.get_network(network_id, host_id)
        return NetworkData(network, resolved_host_id)
    
    async def remove_network(
        self,
        network_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a network"""
        await self._executor.remove_network(network_id, host_id)
    
    async def prune_networks(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prune unused networks"""
        return await self._executor.prune_networks(filters, host_id)


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