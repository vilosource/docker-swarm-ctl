"""
Async Docker Service

Uses aiodocker and the async connection manager for better performance and SSH support.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    import aiodocker

from app.services.async_docker_operation_executor import (
    AsyncDockerOperationExecutor,
    AsyncMultiHostAdapter
)
from app.services.async_docker_connection_manager import get_async_docker_connection_manager
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession


class AsyncContainerData:
    """Async data class for container information using aiodocker"""
    
    def __init__(self, container: 'aiodocker.containers.Container', host_id: Optional[str] = None):
        self.container = container
        self.host_id = host_id
        self._container_data = container._container  # Raw container data
    
    @property
    def id(self) -> str:
        return self._container_data['Id'][:12]
    
    @property
    def name(self) -> str:
        # Remove leading slash from name
        name = self._container_data['Names'][0] if self._container_data.get('Names') else self._container_data.get('Name', '')
        return name.lstrip('/')
    
    @property
    def image(self) -> str:
        return self._container_data.get('Image', '')
    
    @property
    def status(self) -> str:
        return self._container_data.get('Status', '')
    
    @property
    def state(self) -> str:
        state_data = self._container_data.get('State', '')
        if isinstance(state_data, dict):
            # aiodocker returns a dict like {'Status': 'running', 'Running': True, ...}
            # Extract the Status string from it
            return state_data.get('Status', 'unknown')
        return str(state_data)
    
    @property
    def created(self) -> str:
        created_timestamp = self._container_data.get('Created', 0)
        if isinstance(created_timestamp, (int, float)):
            return datetime.fromtimestamp(created_timestamp).isoformat()
        return str(created_timestamp)
    
    @property
    def ports(self) -> List[Dict[str, Any]]:
        ports = self._container_data.get('Ports', [])
        if isinstance(ports, list):
            return ports
        return []
    
    @property
    def labels(self) -> Dict[str, str]:
        return self._container_data.get('Labels') or {}


class AsyncImageData:
    """Async data class for image information using aiodocker"""
    
    def __init__(self, image: Dict[str, Any], host_id: Optional[str] = None):
        self.image = image
        self.host_id = host_id
    
    @property
    def id(self) -> str:
        return self.image['Id'][:12] if self.image.get('Id') else ''
    
    @property
    def tags(self) -> List[str]:
        return self.image.get('RepoTags', []) or []
    
    @property
    def size(self) -> int:
        return self.image.get('Size', 0)
    
    @property
    def created(self) -> str:
        created_timestamp = self.image.get('Created', 0)
        if isinstance(created_timestamp, (int, float)):
            return datetime.fromtimestamp(created_timestamp).isoformat()
        return str(created_timestamp)


class AsyncNetworkData:
    """Async data class for network information using aiodocker"""
    
    def __init__(self, network: Dict[str, Any], host_id: Optional[str] = None):
        self.network = network
        self.host_id = host_id
    
    @property
    def id(self) -> str:
        return self.network.get('id', '')
    
    @property
    def name(self) -> str:
        return self.network.get('name', '')
    
    @property
    def driver(self) -> str:
        return self.network.get('driver', '')
    
    @property
    def scope(self) -> str:
        return self.network.get('scope', '')
    
    @property
    def ipam(self) -> Dict[str, Any]:
        return self.network.get('ipam', {})
    
    @property
    def internal(self) -> bool:
        return self.network.get('internal', False)
    
    @property
    def attachable(self) -> bool:
        return self.network.get('attachable', False)
    
    @property
    def ingress(self) -> bool:
        return self.network.get('ingress', False)
    
    @property
    def containers(self) -> Dict[str, Any]:
        return self.network.get('containers', {})
    
    @property
    def options(self) -> Dict[str, Any]:
        return self.network.get('options', {})
    
    @property
    def labels(self) -> Dict[str, Any]:
        return self.network.get('labels', {})
    
    @property
    def created(self) -> str:
        return self.network.get('created', '')


class AsyncUnifiedDockerService:
    """
    Async unified Docker service using aiodocker and SSH tunneling
    """
    
    def __init__(self, executor: AsyncDockerOperationExecutor):
        self._executor = executor
    
    async def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[AsyncContainerData]:
        """List containers from the specified or default host"""
        container_tuples = await self._executor.list_containers(all, filters, host_id)
        return [AsyncContainerData(container, host_id) for container, host_id in container_tuples]
    
    async def get_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> AsyncContainerData:
        """Get a specific container"""
        container, resolved_host_id = await self._executor.get_container(container_id, host_id)
        return AsyncContainerData(container, resolved_host_id)
    
    async def create_container(
        self,
        config: Dict[str, Any],
        name: Optional[str] = None,
        host_id: Optional[str] = None
    ) -> AsyncContainerData:
        """Create a new container"""
        container, resolved_host_id = await self._executor.create_container(config, name, host_id)
        return AsyncContainerData(container, resolved_host_id)
    
    async def start_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Start a container"""
        resolved_host_id = await self._executor.start_container(container_id, host_id)
        return {"host_id": resolved_host_id}
    
    async def stop_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Stop a container"""
        resolved_host_id = await self._executor.stop_container(container_id, timeout, host_id)
        return {"host_id": resolved_host_id}
    
    async def restart_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Restart a container"""
        resolved_host_id = await self._executor.restart_container(container_id, timeout, host_id)
        return {"host_id": resolved_host_id}
    
    async def remove_container(
        self,
        container_id: str,
        force: bool = False,
        remove_volumes: bool = False,
        host_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Remove a container"""
        resolved_host_id = await self._executor.remove_container(container_id, force, remove_volumes, host_id)
        return {"host_id": resolved_host_id}
    
    async def get_container_logs(
        self,
        container_id: str,
        tail: str = "all",
        follow: bool = False,
        timestamps: bool = False,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get container logs"""
        logs, resolved_host_id = await self._executor.get_container_logs(
            container_id, tail, follow, timestamps, host_id
        )
        return {"logs": logs, "host_id": resolved_host_id}
    
    async def inspect_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inspect a container"""
        inspect_data, resolved_host_id = await self._executor.inspect_container(container_id, host_id)
        return {"inspect": inspect_data, "host_id": resolved_host_id}
    
    async def get_container_stats(
        self,
        container_id: str,
        stream: bool = False,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get container statistics"""
        stats, resolved_host_id = await self._executor.get_container_stats(container_id, stream, host_id)
        return {"stats": stats, "host_id": resolved_host_id}
    
    async def list_images(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[AsyncImageData]:
        """List images from the specified or default host"""
        # We'll need to add this to the executor
        client, resolved_host_id = await self._executor._adapter.get_client(host_id)
        
        try:
            images = await client.images.list(all=all, filters=filters)
            # Handle both dict objects and image objects
            result = []
            for img in images:
                if hasattr(img, '_image'):
                    result.append(AsyncImageData(img._image, resolved_host_id))
                elif isinstance(img, dict):
                    result.append(AsyncImageData(img, resolved_host_id))
                else:
                    # Convert to dict if it's another type
                    result.append(AsyncImageData(dict(img), resolved_host_id))
            return result
        except Exception as e:
            from app.core.exceptions import DockerOperationError
            raise DockerOperationError("docker.image.list", f"Image listing failed: {str(e)}")
    
    async def list_networks(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[AsyncNetworkData]:
        """List networks from the specified or default host"""
        client, resolved_host_id = await self._executor._adapter.get_client(host_id)
        
        try:
            networks = await client.networks.list(filters=filters)
            # aiodocker returns network objects, we need to extract the data
            result = []
            for net in networks:
                # Get network details
                net_data = {
                    'id': net['Id'],
                    'name': net['Name'],
                    'driver': net.get('Driver', ''),
                    'scope': net.get('Scope', ''),
                    'ipam': net.get('IPAM', {}),
                    'internal': net.get('Internal', False),
                    'attachable': net.get('Attachable', False),
                    'ingress': net.get('Ingress', False),
                    'containers': net.get('Containers', {}),
                    'options': net.get('Options', {}),
                    'labels': net.get('Labels', {}),
                    'created': net.get('Created', ''),
                    'host_id': resolved_host_id
                }
                result.append(AsyncNetworkData(net_data, resolved_host_id))
            return result
        except Exception as e:
            from app.core.exceptions import DockerOperationError
            raise DockerOperationError("docker.network.list", f"Network listing failed: {str(e)}")
    
    async def list_volumes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List['AsyncVolumeData']:
        """List volumes from the specified or default host"""
        client, resolved_host_id = await self._executor._adapter.get_client(host_id)
        
        try:
            volumes_response = await client.volumes.list(filters=filters)
            # aiodocker returns a dict with 'Volumes' key containing the list
            volumes = volumes_response.get('Volumes', []) if isinstance(volumes_response, dict) else volumes_response
            
            result = []
            for vol in volumes:
                # Handle both dict and object formats
                if isinstance(vol, dict):
                    vol_data = {
                        'name': vol.get('Name', ''),
                        'driver': vol.get('Driver', ''),
                        'mountpoint': vol.get('Mountpoint', ''),
                        'created_at': vol.get('CreatedAt', ''),
                        'status': vol.get('Status', {}),
                        'labels': vol.get('Labels', {}),
                        'scope': vol.get('Scope', ''),
                        'options': vol.get('Options', {}),
                        'host_id': resolved_host_id
                    }
                else:
                    # If it's not a dict, try to access as attributes
                    vol_data = {
                        'name': getattr(vol, 'Name', ''),
                        'driver': getattr(vol, 'Driver', ''),
                        'mountpoint': getattr(vol, 'Mountpoint', ''),
                        'created_at': getattr(vol, 'CreatedAt', ''),
                        'status': getattr(vol, 'Status', {}),
                        'labels': getattr(vol, 'Labels', {}),
                        'scope': getattr(vol, 'Scope', ''),
                        'options': getattr(vol, 'Options', {}),
                        'host_id': resolved_host_id
                    }
                result.append(AsyncVolumeData(vol_data, resolved_host_id))
            return result
        except Exception as e:
            from app.core.exceptions import DockerOperationError
            raise DockerOperationError("docker.volume.list", f"Volume listing failed: {str(e)}")


class AsyncVolumeData:
    """Async data class for volume information using aiodocker"""
    
    def __init__(self, volume: Dict[str, Any], host_id: Optional[str] = None):
        self.volume = volume
        self.host_id = host_id
    
    @property
    def name(self) -> str:
        return self.volume.get('name', '')
    
    @property
    def driver(self) -> str:
        return self.volume.get('driver', '')
    
    @property
    def mountpoint(self) -> str:
        return self.volume.get('mountpoint', '')
    
    @property
    def created_at(self) -> str:
        return self.volume.get('created_at', '')
    
    @property
    def status(self) -> Dict[str, Any]:
        return self.volume.get('status', {})
    
    @property
    def labels(self) -> Dict[str, str]:
        return self.volume.get('labels', {})
    
    @property
    def scope(self) -> str:
        return self.volume.get('scope', '')
    
    @property
    def options(self) -> Dict[str, Any]:
        return self.volume.get('options', {})


class AsyncDockerServiceFactory:
    """Factory for creating async Docker service instances"""
    
    @staticmethod
    def create(
        user: User,
        db: AsyncSession,
        multi_host: bool = True
    ) -> AsyncUnifiedDockerService:
        """Create async Docker service instance"""
        if multi_host:
            return AsyncDockerServiceFactory.create_for_multi_host(user, db)
        else:
            raise NotImplementedError("Single host mode not yet implemented for async service")
    
    @staticmethod
    def create_for_multi_host(
        user: User,
        db: AsyncSession
    ) -> AsyncUnifiedDockerService:
        """Create service for multi-host deployment"""
        connection_manager = get_async_docker_connection_manager()
        adapter = AsyncMultiHostAdapter(connection_manager, user, db)
        executor = AsyncDockerOperationExecutor(adapter)
        return AsyncUnifiedDockerService(executor)


# For backward compatibility
IAsyncDockerService = AsyncUnifiedDockerService