"""
Async Docker Operation Executor

Updated version that uses aiodocker and the new async connection manager.
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from abc import ABC, abstractmethod
import asyncio

if TYPE_CHECKING:
    import aiodocker

from app.core.exceptions import DockerOperationError, DockerConnectionError, ResourceNotFoundError
from app.core.logging import logger
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession


class AsyncDockerClientAdapter(ABC):
    """
    Adapter that provides a unified interface for getting async Docker clients
    """
    
    @abstractmethod
    async def get_client(self, host_id: Optional[str] = None) -> tuple['aiodocker.Docker', str]:
        """Get async Docker client and resolved host ID"""
        pass


class AsyncMultiHostAdapter(AsyncDockerClientAdapter):
    """Adapter for multi-host deployments using aiodocker"""
    
    def __init__(
        self,
        connection_manager: 'AsyncDockerConnectionManager',
        user: User,
        db: AsyncSession
    ):
        self._connection_manager = connection_manager
        self._user = user
        self._db = db
    
    async def get_client(self, host_id: Optional[str] = None) -> tuple['aiodocker.Docker', str]:
        """Get aiodocker client for specified or default host"""
        if not host_id:
            # Get default host for user
            host_id = await self._connection_manager.get_default_host_id(self._db, self._user)
            if not host_id:
                raise DockerConnectionError("No Docker hosts available for user")
        
        client = await self._connection_manager.get_client(host_id, self._user, self._db)
        return client, host_id


class AsyncDockerOperationExecutor:
    """
    Async executor for Docker operations using aiodocker
    """
    
    def __init__(self, adapter: AsyncDockerClientAdapter):
        self._adapter = adapter
    
    async def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple['aiodocker.containers.Container', str]]:
        """List containers and return (container, host_id) tuples"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            # Convert filters to aiodocker format if needed
            aiodocker_filters = {}
            if filters:
                # aiodocker uses slightly different filter format
                for key, value in filters.items():
                    if isinstance(value, list):
                        aiodocker_filters[key] = value
                    else:
                        aiodocker_filters[key] = [value] if value else []
            
            containers = await client.containers.list(
                all=all,
                filters=aiodocker_filters if aiodocker_filters else None
            )
            
            return [(container, resolved_host_id) for container in containers]
            
        except Exception as e:
            logger.error(f"Failed to list containers on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container listing failed: {str(e)}")
    
    async def get_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> tuple['aiodocker.containers.Container', str]:
        """Get a specific container"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            container = await client.containers.get(container_id)
            return container, resolved_host_id
            
        except Exception as e:
            if "No such container" in str(e) or "404" in str(e):
                raise ResourceNotFoundError("container", container_id)
            logger.error(f"Failed to get container {container_id} on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container retrieval failed: {str(e)}")
    
    async def create_container(
        self,
        config: Dict[str, Any],
        name: Optional[str] = None,
        host_id: Optional[str] = None
    ) -> tuple['aiodocker.containers.Container', str]:
        """Create a new container"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            # aiodocker expects config in a specific format
            container_config = {
                'Image': config.get('image', config.get('Image')),
                'Cmd': config.get('command', config.get('Cmd')),
                'Env': config.get('environment', config.get('Env', [])),
                'ExposedPorts': config.get('ports', config.get('ExposedPorts')),
                'Labels': config.get('labels', config.get('Labels', {})),
                'WorkingDir': config.get('working_dir', config.get('WorkingDir')),
                'User': config.get('user', config.get('User')),
                'Volumes': config.get('volumes', config.get('Volumes')),
                'Entrypoint': config.get('entrypoint', config.get('Entrypoint')),
                'AttachStdout': True,
                'AttachStderr': True,
            }
            
            # Remove None values
            container_config = {k: v for k, v in container_config.items() if v is not None}
            
            # Handle host config (port bindings, volume mounts, etc.)
            host_config = {}
            if 'port_bindings' in config or 'PortBindings' in config:
                host_config['PortBindings'] = config.get('port_bindings', config.get('PortBindings'))
            if 'binds' in config or 'Binds' in config:
                host_config['Binds'] = config.get('binds', config.get('Binds'))
            if 'restart_policy' in config or 'RestartPolicy' in config:
                host_config['RestartPolicy'] = config.get('restart_policy', config.get('RestartPolicy'))
            
            create_config = {
                'config': container_config,
                'name': name
            }
            
            if host_config:
                create_config['host_config'] = host_config
            
            container = await client.containers.create_or_replace(**create_config)
            return container, resolved_host_id
            
        except Exception as e:
            logger.error(f"Failed to create container on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container creation failed: {str(e)}")
    
    async def start_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> str:
        """Start a container"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            container = await client.containers.get(container_id)
            await container.start()
            return resolved_host_id
            
        except Exception as e:
            if "No such container" in str(e):
                raise ResourceNotFoundError("container", container_id)
            logger.error(f"Failed to start container {container_id} on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container start failed: {str(e)}")
    
    async def stop_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> str:
        """Stop a container"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            container = await client.containers.get(container_id)
            await container.stop(timeout=timeout)
            return resolved_host_id
            
        except Exception as e:
            if "No such container" in str(e):
                raise ResourceNotFoundError("container", container_id)
            logger.error(f"Failed to stop container {container_id} on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container stop failed: {str(e)}")
    
    async def restart_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> str:
        """Restart a container"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            container = await client.containers.get(container_id)
            await container.restart(timeout=timeout)
            return resolved_host_id
            
        except Exception as e:
            if "No such container" in str(e):
                raise ResourceNotFoundError("container", container_id)
            logger.error(f"Failed to restart container {container_id} on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container restart failed: {str(e)}")
    
    async def remove_container(
        self,
        container_id: str,
        force: bool = False,
        remove_volumes: bool = False,
        host_id: Optional[str] = None
    ) -> str:
        """Remove a container"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            container = await client.containers.get(container_id)
            await container.delete(force=force, v=remove_volumes)
            return resolved_host_id
            
        except Exception as e:
            if "No such container" in str(e):
                raise ResourceNotFoundError("container", container_id)
            logger.error(f"Failed to remove container {container_id} on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container removal failed: {str(e)}")
    
    async def get_container_logs(
        self,
        container_id: str,
        tail: str = "all",
        follow: bool = False,
        timestamps: bool = False,
        host_id: Optional[str] = None
    ) -> tuple[str, str]:
        """Get container logs"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            container = await client.containers.get(container_id)
            
            # aiodocker logs parameters
            logs = await container.log(
                stdout=True,
                stderr=True,
                timestamps=timestamps,
                tail=None if tail == "all" else int(tail),
                follow=follow
            )
            
            # Combine stdout and stderr
            if isinstance(logs, list):
                log_text = ''.join(logs)
            else:
                log_text = str(logs)
            
            return log_text, resolved_host_id
            
        except Exception as e:
            if "No such container" in str(e):
                raise ResourceNotFoundError("container", container_id)
            logger.error(f"Failed to get logs for container {container_id} on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container logs retrieval failed: {str(e)}")
    
    async def inspect_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> tuple[Dict[str, Any], str]:
        """Inspect a container"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            container = await client.containers.get(container_id)
            # Get detailed container information
            inspect_data = container._container
            return inspect_data, resolved_host_id
            
        except Exception as e:
            if "No such container" in str(e):
                raise ResourceNotFoundError("container", container_id)
            logger.error(f"Failed to inspect container {container_id} on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container inspection failed: {str(e)}")
    
    async def get_container_stats(
        self,
        container_id: str,
        stream: bool = False,
        host_id: Optional[str] = None
    ) -> tuple[Dict[str, Any], str]:
        """Get container statistics"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        
        try:
            container = await client.containers.get(container_id)
            stats = await container.stats(stream=stream)
            return stats, resolved_host_id
            
        except Exception as e:
            if "No such container" in str(e):
                raise ResourceNotFoundError("container", container_id)
            logger.error(f"Failed to get stats for container {container_id} on host {resolved_host_id}: {str(e)}")
            raise DockerOperationError(f"Container stats retrieval failed: {str(e)}")