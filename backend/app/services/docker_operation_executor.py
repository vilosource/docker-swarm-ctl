"""
Docker Operation Executor

Unified executor for Docker operations that works with both single and multi-host deployments.
Implements the Adapter pattern to abstract away the differences.
"""

from typing import Optional, Dict, Any, List, Callable, TypeVar
from functools import wraps
from abc import ABC, abstractmethod
import asyncio
from contextlib import asynccontextmanager

from docker.client import DockerClient
from docker.models.containers import Container
from docker.errors import DockerException, NotFound, APIError

from app.core.exceptions import DockerOperationError, DockerConnectionError
from app.core.logging import logger
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession


T = TypeVar('T')


class DockerClientAdapter(ABC):
    """
    Adapter that provides a unified interface for getting Docker clients
    regardless of single-host or multi-host deployment
    """
    
    @abstractmethod
    async def get_client(self, host_id: Optional[str] = None) -> tuple[DockerClient, str]:
        """Get Docker client and resolved host ID"""
        pass


class SingleHostAdapter(DockerClientAdapter):
    """Adapter for single-host deployments"""
    
    def __init__(self, docker_client: DockerClient):
        self._client = docker_client
        self._host_id = "localhost"
    
    async def get_client(self, host_id: Optional[str] = None) -> tuple[DockerClient, str]:
        """Always returns the same local Docker client"""
        return self._client, self._host_id


class MultiHostAdapter(DockerClientAdapter):
    """Adapter for multi-host deployments"""
    
    def __init__(
        self,
        connection_manager: 'DockerConnectionManager',
        user: User,
        db: AsyncSession
    ):
        self._connection_manager = connection_manager
        self._user = user
        self._db = db
    
    async def get_client(self, host_id: Optional[str] = None) -> tuple[DockerClient, str]:
        """Get Docker client for specified or default host"""
        if not host_id:
            # Get default host for user
            host_id = await self._connection_manager.get_default_host_id(self._db, self._user)
            if not host_id:
                raise DockerConnectionError("No accessible Docker hosts found")
        
        client = await self._connection_manager.get_client(host_id, self._user, self._db)
        return client, host_id


def docker_operation(operation_name: str):
    """
    Decorator for Docker operations that provides consistent error handling
    and logging across all operations
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            host_id = kwargs.get('host_id')
            try:
                logger.debug(f"Executing {operation_name} on host {host_id or 'default'}")
                result = await func(self, *args, **kwargs)
                logger.debug(f"Successfully completed {operation_name}")
                return result
            except DockerException as e:
                logger.error(f"Docker error in {operation_name}: {e}")
                raise DockerOperationError(operation_name, str(e))
            except Exception as e:
                logger.error(f"Unexpected error in {operation_name}: {e}")
                raise DockerOperationError(operation_name, f"Unexpected error: {str(e)}")
        return wrapper
    return decorator


class DockerOperationExecutor:
    """
    Unified executor for Docker operations
    
    This class implements all Docker operations in a single place,
    eliminating code duplication between single and multi-host services.
    """
    
    def __init__(self, client_adapter: DockerClientAdapter):
        self._adapter = client_adapter
    
    @asynccontextmanager
    async def _get_client_context(self, host_id: Optional[str] = None):
        """Context manager for getting Docker client"""
        client, resolved_host_id = await self._adapter.get_client(host_id)
        yield client, resolved_host_id
    
    @docker_operation("list_containers")
    async def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple[Container, str]]:
        """List containers from specified host or all accessible hosts"""
        # If host_id is specified, query only that host
        if host_id:
            async with self._get_client_context(host_id) as (client, resolved_host_id):
                kwargs = {"all": all}
                if filters:
                    kwargs["filters"] = filters
                
                containers = client.containers.list(**kwargs)
                return [(c, resolved_host_id) for c in containers]
        
        # If no host_id, query all accessible hosts (for multi-host adapter)
        if isinstance(self._adapter, MultiHostAdapter):
            from app.services.permission_service import get_permission_service
            permission_service = get_permission_service()
            
            # Get all accessible hosts
            accessible_hosts = await permission_service.get_accessible_hosts(
                self._adapter._user, 
                self._adapter._db
            )
            
            # Query containers from all accessible hosts
            all_containers = []
            for host in accessible_hosts:
                try:
                    async with self._get_client_context(str(host.id)) as (client, resolved_host_id):
                        kwargs = {"all": all}
                        if filters:
                            kwargs["filters"] = filters
                        
                        containers = client.containers.list(**kwargs)
                        all_containers.extend([(c, resolved_host_id) for c in containers])
                except Exception as e:
                    logger.warning(f"Failed to list containers from host {host.id}: {e}")
                    continue
            
            return all_containers
        else:
            # Single host adapter - use default behavior
            async with self._get_client_context(host_id) as (client, resolved_host_id):
                kwargs = {"all": all}
                if filters:
                    kwargs["filters"] = filters
                
                containers = client.containers.list(**kwargs)
                return [(c, resolved_host_id) for c in containers]
    
    @docker_operation("get_container")
    async def get_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> tuple[Container, str]:
        """Get a specific container"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            try:
                container = client.containers.get(container_id)
                return container, resolved_host_id
            except NotFound:
                raise DockerOperationError(
                    "get_container",
                    f"Container {container_id} not found"
                )
    
    @docker_operation("create_container")
    async def create_container(
        self,
        config: Dict[str, Any],
        host_id: Optional[str] = None
    ) -> tuple[Container, str]:
        """Create a new container"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            container = client.containers.run(**config)
            return container, resolved_host_id
    
    @docker_operation("start_container")
    async def start_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Start a container"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            container = client.containers.get(container_id)
            container.start()
    
    @docker_operation("stop_container")
    async def stop_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        """Stop a container"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            container = client.containers.get(container_id)
            container.stop(timeout=timeout)
    
    @docker_operation("restart_container")
    async def restart_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        """Restart a container"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            container = client.containers.get(container_id)
            container.restart(timeout=timeout)
    
    @docker_operation("remove_container")
    async def remove_container(
        self,
        container_id: str,
        force: bool = False,
        volumes: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a container"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            container = client.containers.get(container_id)
            container.remove(force=force, v=volumes)
    
    @docker_operation("get_container_logs")
    async def get_container_logs(
        self,
        container_id: str,
        lines: int = 100,
        timestamps: bool = False,
        host_id: Optional[str] = None
    ) -> str:
        """Get container logs"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            container = client.containers.get(container_id)
            logs = container.logs(tail=lines, timestamps=timestamps, stream=False)
            return logs.decode("utf-8") if isinstance(logs, bytes) else logs
    
    @docker_operation("get_container_stats")
    async def get_container_stats(
        self,
        container_id: str,
        stream: bool = False,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get container statistics"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            container = client.containers.get(container_id)
            return container.stats(stream=stream)
    
    @docker_operation("inspect_container")
    async def inspect_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inspect a container"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            container = client.containers.get(container_id)
            return container.attrs
    
    @docker_operation("exec_run")
    async def exec_run(
        self,
        container_id: str,
        cmd: str,
        stdout: bool = True,
        stderr: bool = True,
        stdin: bool = False,
        tty: bool = False,
        privileged: bool = False,
        user: str = '',
        detach: bool = False,
        stream: bool = False,
        socket: bool = False,
        environment: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
        host_id: Optional[str] = None
    ) -> Any:
        """Execute a command in a container"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            container = client.containers.get(container_id)
            return container.exec_run(
                cmd,
                stdout=stdout,
                stderr=stderr,
                stdin=stdin,
                tty=tty,
                privileged=privileged,
                user=user,
                detach=detach,
                stream=stream,
                socket=socket,
                environment=environment,
                workdir=workdir
            )
    
    # Image operations
    @docker_operation("list_images")
    async def list_images(
        self,
        name: Optional[str] = None,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple[Any, str]]:
        """List images from specified host or all accessible hosts"""
        # If host_id is specified, query only that host
        if host_id:
            async with self._get_client_context(host_id) as (client, resolved_host_id):
                kwargs = {"all": all}
                if name:
                    kwargs["name"] = name
                if filters:
                    kwargs["filters"] = filters
                
                images = client.images.list(**kwargs)
                return [(img, resolved_host_id) for img in images]
        
        # If no host_id, query all accessible hosts (for multi-host adapter)
        if isinstance(self._adapter, MultiHostAdapter):
            from app.services.permission_service import get_permission_service
            permission_service = get_permission_service()
            
            # Get all accessible hosts
            accessible_hosts = await permission_service.get_accessible_hosts(
                self._adapter._user, 
                self._adapter._db
            )
            
            # Query images from all accessible hosts
            all_images = []
            for host in accessible_hosts:
                try:
                    async with self._get_client_context(str(host.id)) as (client, resolved_host_id):
                        kwargs = {"all": all}
                        if name:
                            kwargs["name"] = name
                        if filters:
                            kwargs["filters"] = filters
                        
                        images = client.images.list(**kwargs)
                        all_images.extend([(img, resolved_host_id) for img in images])
                except Exception as e:
                    logger.warning(f"Failed to list images from host {host.id}: {e}")
                    continue
            
            return all_images
        else:
            # Single host adapter - use default behavior
            async with self._get_client_context(host_id) as (client, resolved_host_id):
                kwargs = {"all": all}
                if name:
                    kwargs["name"] = name
                if filters:
                    kwargs["filters"] = filters
                
                images = client.images.list(**kwargs)
                return [(img, resolved_host_id) for img in images]
    
    @docker_operation("pull_image")
    async def pull_image(
        self,
        repository: str,
        tag: Optional[str] = None,
        auth_config: Optional[Dict[str, str]] = None,
        host_id: Optional[str] = None
    ) -> Any:
        """Pull an image"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            return client.images.pull(repository, tag=tag, auth_config=auth_config)
    
    @docker_operation("remove_image")
    async def remove_image(
        self,
        image: str,
        force: bool = False,
        noprune: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove an image"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            client.images.remove(image, force=force, noprune=noprune)
    
    # System operations
    @docker_operation("get_system_info")
    async def get_system_info(
        self,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get Docker system information"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            return client.info()
    
    @docker_operation("get_version")
    async def get_version(
        self,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get Docker version information"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            return client.version()
    
    @docker_operation("ping")
    async def ping(
        self,
        host_id: Optional[str] = None
    ) -> bool:
        """Ping Docker daemon"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            return client.ping()
    
    @docker_operation("get_disk_usage")
    async def get_disk_usage(
        self,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get disk usage information from Docker"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            return client.df()
    
    # Volume operations
    @docker_operation("list_volumes")
    async def list_volumes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple[Any, str]]:
        """List volumes from specified host or all accessible hosts"""
        # If host_id is specified, query only that host
        if host_id:
            async with self._get_client_context(host_id) as (client, resolved_host_id):
                volumes = client.volumes.list(filters=filters)
                return [(v, resolved_host_id) for v in volumes]
        
        # If no host_id, query all accessible hosts (for multi-host adapter)
        if isinstance(self._adapter, MultiHostAdapter):
            from app.services.permission_service import get_permission_service
            permission_service = get_permission_service()
            
            # Get all accessible hosts
            accessible_hosts = await permission_service.get_accessible_hosts(
                self._adapter._user, 
                self._adapter._db
            )
            
            # Query volumes from all accessible hosts
            all_volumes = []
            for host in accessible_hosts:
                try:
                    async with self._get_client_context(str(host.id)) as (client, resolved_host_id):
                        volumes = client.volumes.list(filters=filters)
                        all_volumes.extend([(v, resolved_host_id) for v in volumes])
                except Exception as e:
                    logger.warning(f"Failed to list volumes from host {host.id}: {e}")
                    continue
            
            return all_volumes
        else:
            # Single host adapter - use default behavior
            async with self._get_client_context(host_id) as (client, resolved_host_id):
                volumes = client.volumes.list(filters=filters)
                return [(v, resolved_host_id) for v in volumes]
    
    @docker_operation("create_volume")
    async def create_volume(
        self,
        name: Optional[str] = None,
        driver: str = "local",
        driver_opts: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Create a volume"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            volume = client.volumes.create(
                name=name,
                driver=driver,
                driver_opts=driver_opts,
                labels=labels
            )
            return volume, resolved_host_id
    
    @docker_operation("get_volume")
    async def get_volume(
        self,
        volume_id: str,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Get a volume"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            volume = client.volumes.get(volume_id)
            return volume, resolved_host_id
    
    @docker_operation("remove_volume")
    async def remove_volume(
        self,
        volume_id: str,
        force: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a volume"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            volume = client.volumes.get(volume_id)
            volume.remove(force=force)
    
    @docker_operation("prune_volumes")
    async def prune_volumes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prune unused volumes"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            return client.volumes.prune(filters=filters)
    
    # Network operations
    @docker_operation("list_networks")
    async def list_networks(
        self,
        names: Optional[List[str]] = None,
        ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple[Any, str]]:
        """List networks from specified host or all accessible hosts"""
        # If host_id is specified, query only that host
        if host_id:
            async with self._get_client_context(host_id) as (client, resolved_host_id):
                networks = client.networks.list(names=names, ids=ids, filters=filters)
                return [(n, resolved_host_id) for n in networks]
        
        # If no host_id, query all accessible hosts (for multi-host adapter)
        if isinstance(self._adapter, MultiHostAdapter):
            from app.services.permission_service import get_permission_service
            permission_service = get_permission_service()
            
            # Get all accessible hosts
            accessible_hosts = await permission_service.get_accessible_hosts(
                self._adapter._user, 
                self._adapter._db
            )
            
            # Query networks from all accessible hosts
            all_networks = []
            for host in accessible_hosts:
                try:
                    async with self._get_client_context(str(host.id)) as (client, resolved_host_id):
                        networks = client.networks.list(names=names, ids=ids, filters=filters)
                        all_networks.extend([(n, resolved_host_id) for n in networks])
                except Exception as e:
                    logger.warning(f"Failed to list networks from host {host.id}: {e}")
                    continue
            
            return all_networks
        else:
            # Single host adapter - use default behavior
            async with self._get_client_context(host_id) as (client, resolved_host_id):
                networks = client.networks.list(names=names, ids=ids, filters=filters)
                return [(n, resolved_host_id) for n in networks]
    
    @docker_operation("create_network")
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
    ) -> tuple[Any, str]:
        """Create a network"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            network = client.networks.create(
                name=name,
                driver=driver,
                options=options,
                ipam=ipam,
                check_duplicate=check_duplicate,
                internal=internal,
                labels=labels,
                enable_ipv6=enable_ipv6,
                attachable=attachable,
                scope=scope
            )
            return network, resolved_host_id
    
    @docker_operation("get_network")
    async def get_network(
        self,
        network_id: str,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Get a network"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            network = client.networks.get(network_id)
            return network, resolved_host_id
    
    @docker_operation("remove_network")
    async def remove_network(
        self,
        network_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a network"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            network = client.networks.get(network_id)
            network.remove()
    
    @docker_operation("prune_networks")
    async def prune_networks(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prune unused networks"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            return client.networks.prune(filters=filters)
    
    # Swarm operations
    @docker_operation("get_swarm_info")
    async def get_swarm_info(
        self,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get swarm information"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            return client.swarm.attrs
    
    @docker_operation("init_swarm")
    async def init_swarm(
        self,
        advertise_addr: str,
        listen_addr: str = "0.0.0.0:2377",
        force_new_cluster: bool = False,
        default_addr_pool: Optional[List[str]] = None,
        subnet_size: Optional[int] = None,
        data_path_addr: Optional[str] = None,
        data_path_port: Optional[int] = None,
        host_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Initialize a swarm"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            return client.swarm.init(
                advertise_addr=advertise_addr,
                listen_addr=listen_addr,
                force_new_cluster=force_new_cluster,
                default_addr_pool=default_addr_pool,
                subnet_size=subnet_size,
                data_path_addr=data_path_addr,
                data_path_port=data_path_port,
                **kwargs
            )
    
    @docker_operation("join_swarm")
    async def join_swarm(
        self,
        remote_addrs: List[str],
        join_token: str,
        advertise_addr: Optional[str] = None,
        listen_addr: str = "0.0.0.0:2377",
        data_path_addr: Optional[str] = None,
        host_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Join a swarm"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            client.swarm.join(
                remote_addrs=remote_addrs,
                join_token=join_token,
                advertise_addr=advertise_addr,
                listen_addr=listen_addr,
                data_path_addr=data_path_addr,
                **kwargs
            )
    
    @docker_operation("leave_swarm")
    async def leave_swarm(
        self,
        force: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Leave a swarm"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            client.swarm.leave(force=force)
    
    @docker_operation("update_swarm")
    async def update_swarm(
        self,
        rotate_worker_token: bool = False,
        rotate_manager_token: bool = False,
        rotate_manager_unlock_key: bool = False,
        host_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update swarm configuration"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            client.swarm.update(
                rotate_worker_token=rotate_worker_token,
                rotate_manager_token=rotate_manager_token,
                rotate_manager_unlock_key=rotate_manager_unlock_key,
                **kwargs
            )
    
    # Node operations
    @docker_operation("list_nodes")
    async def list_nodes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple[Any, str]]:
        """List swarm nodes"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            nodes = client.nodes.list(filters=filters)
            return [(node, resolved_host_id) for node in nodes]
    
    @docker_operation("get_node")
    async def get_node(
        self,
        node_id: str,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Get a swarm node"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            node = client.nodes.get(node_id)
            return node, resolved_host_id
    
    @docker_operation("update_node")
    async def update_node(
        self,
        node_id: str,
        version: int,
        spec: Dict[str, Any],
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Update a swarm node"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            node = client.nodes.get(node_id)
            updated = node.update(spec)
            return updated, resolved_host_id
    
    @docker_operation("remove_node")
    async def remove_node(
        self,
        node_id: str,
        force: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a swarm node"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            node = client.nodes.get(node_id)
            node.remove(force=force)
    
    # Service operations
    @docker_operation("create_service")
    async def create_service(
        self,
        image: str,
        command: Optional[List[str]] = None,
        name: Optional[str] = None,
        mode: Optional[Dict[str, Any]] = None,
        mounts: Optional[List[Dict[str, Any]]] = None,
        networks: Optional[List[str]] = None,
        endpoint_spec: Optional[Dict[str, Any]] = None,
        update_config: Optional[Dict[str, Any]] = None,
        rollback_config: Optional[Dict[str, Any]] = None,
        restart_policy: Optional[Dict[str, Any]] = None,
        secrets: Optional[List[Dict[str, Any]]] = None,
        configs: Optional[List[Dict[str, Any]]] = None,
        env: Optional[List[str]] = None,
        workdir: Optional[str] = None,
        user: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        constraints: Optional[List[str]] = None,
        preferences: Optional[List[Dict[str, Any]]] = None,
        platforms: Optional[List[Dict[str, Any]]] = None,
        container_labels: Optional[Dict[str, str]] = None,
        resources: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None,
        **kwargs
    ) -> tuple[Any, str]:
        """Create a swarm service"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            service = client.services.create(
                image=image,
                command=command,
                name=name,
                mode=mode,
                mounts=mounts,
                networks=networks,
                endpoint_spec=endpoint_spec,
                update_config=update_config,
                rollback_config=rollback_config,
                restart_policy=restart_policy,
                secrets=secrets,
                configs=configs,
                env=env,
                workdir=workdir,
                user=user,
                labels=labels,
                constraints=constraints,
                preferences=preferences,
                platforms=platforms,
                container_labels=container_labels,
                resources=resources,
                **kwargs
            )
            return service, resolved_host_id
    
    @docker_operation("list_services")
    async def list_services(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple[Any, str]]:
        """List swarm services"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            services = client.services.list(filters=filters)
            return [(service, resolved_host_id) for service in services]
    
    @docker_operation("get_service")
    async def get_service(
        self,
        service_id: str,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Get a swarm service"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            service = client.services.get(service_id)
            return service, resolved_host_id
    
    @docker_operation("update_service")
    async def update_service(
        self,
        service_id: str,
        version: int,
        task_template: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        mode: Optional[Dict[str, Any]] = None,
        update_config: Optional[Dict[str, Any]] = None,
        networks: Optional[List[str]] = None,
        endpoint_spec: Optional[Dict[str, Any]] = None,
        rollback_config: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None,
        **kwargs
    ) -> tuple[Any, str]:
        """Update a swarm service"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            service = client.services.get(service_id)
            updated = service.update(
                version=version,
                task_template=task_template,
                name=name,
                labels=labels,
                mode=mode,
                update_config=update_config,
                networks=networks,
                endpoint_spec=endpoint_spec,
                rollback_config=rollback_config,
                **kwargs
            )
            return updated, resolved_host_id
    
    @docker_operation("remove_service")
    async def remove_service(
        self,
        service_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a swarm service"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            service = client.services.get(service_id)
            service.remove()
    
    @docker_operation("scale_service")
    async def scale_service(
        self,
        service_id: str,
        replicas: int,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Scale a swarm service"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            service = client.services.get(service_id)
            service.scale(replicas)
            return service, resolved_host_id
    
    @docker_operation("service_logs")
    async def service_logs(
        self,
        service_id: str,
        details: bool = False,
        follow: bool = False,
        stdout: bool = True,
        stderr: bool = True,
        since: Optional[int] = None,
        timestamps: bool = False,
        tail: Optional[str] = None,
        host_id: Optional[str] = None
    ):
        """Get service logs"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            service = client.services.get(service_id)
            return service.logs(
                details=details,
                follow=follow,
                stdout=stdout,
                stderr=stderr,
                since=since,
                timestamps=timestamps,
                tail=tail
            )
    
    @docker_operation("list_service_tasks")
    async def list_service_tasks(
        self,
        service_id: str,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple[Any, str]]:
        """List tasks for a service"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            service = client.services.get(service_id)
            tasks = service.tasks(filters=filters)
            return [(task, resolved_host_id) for task in tasks]
    
    # Secret operations
    @docker_operation("create_secret")
    async def create_secret(
        self,
        name: str,
        data: bytes,
        labels: Optional[Dict[str, str]] = None,
        driver: Optional[Dict[str, Any]] = None,
        templating: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Create a swarm secret"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            secret = client.secrets.create(
                name=name,
                data=data,
                labels=labels,
                driver=driver,
                templating=templating
            )
            return secret, resolved_host_id
    
    @docker_operation("list_secrets")
    async def list_secrets(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple[Any, str]]:
        """List swarm secrets"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            secrets = client.secrets.list(filters=filters)
            return [(secret, resolved_host_id) for secret in secrets]
    
    @docker_operation("get_secret")
    async def get_secret(
        self,
        secret_id: str,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Get a swarm secret"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            secret = client.secrets.get(secret_id)
            return secret, resolved_host_id
    
    @docker_operation("remove_secret")
    async def remove_secret(
        self,
        secret_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a swarm secret"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            secret = client.secrets.get(secret_id)
            secret.remove()
    
    # Config operations
    @docker_operation("create_config")
    async def create_config(
        self,
        name: str,
        data: bytes,
        labels: Optional[Dict[str, str]] = None,
        templating: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Create a swarm config"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            config = client.configs.create(
                name=name,
                data=data,
                labels=labels,
                templating=templating
            )
            return config, resolved_host_id
    
    @docker_operation("list_configs")
    async def list_configs(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[tuple[Any, str]]:
        """List swarm configs"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            configs = client.configs.list(filters=filters)
            return [(config, resolved_host_id) for config in configs]
    
    @docker_operation("get_config")
    async def get_config(
        self,
        config_id: str,
        host_id: Optional[str] = None
    ) -> tuple[Any, str]:
        """Get a swarm config"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            config = client.configs.get(config_id)
            return config, resolved_host_id
    
    @docker_operation("remove_config")
    async def remove_config(
        self,
        config_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a swarm config"""
        async with self._get_client_context(host_id) as (client, resolved_host_id):
            config = client.configs.get(config_id)
            config.remove()