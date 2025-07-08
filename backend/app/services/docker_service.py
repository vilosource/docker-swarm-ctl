"""
Refactored Docker Service

Uses the unified DockerOperationExecutor to eliminate code duplication
between single and multi-host implementations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
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


class NodeData:
    """Docker Swarm node information"""
    def __init__(self, node_attrs: Dict[str, Any], host_id: Optional[str] = None):
        self._attrs = node_attrs
        self.host_id = host_id
    
    @property
    def id(self) -> str:
        return self._attrs.get("ID", "")
    
    @property
    def hostname(self) -> str:
        return self._attrs.get("Description", {}).get("Hostname", "")
    
    @property
    def role(self) -> str:
        return self._attrs.get("Spec", {}).get("Role", "")
    
    @property
    def availability(self) -> str:
        return self._attrs.get("Spec", {}).get("Availability", "")
    
    @property
    def status(self) -> str:
        return self._attrs.get("Status", {}).get("State", "")
    
    @property
    def state(self) -> str:
        return self.status  # Alias for consistency
    
    @property
    def addr(self) -> str:
        return self._attrs.get("Status", {}).get("Addr", "")
    
    @property
    def resources(self) -> Dict[str, Any]:
        desc = self._attrs.get("Description", {})
        return {
            "NanoCPUs": desc.get("Resources", {}).get("NanoCPUs", 0),
            "MemoryBytes": desc.get("Resources", {}).get("MemoryBytes", 0)
        }
    
    @property
    def engine_version(self) -> str:
        return self._attrs.get("Description", {}).get("Engine", {}).get("EngineVersion", "")
    
    @property
    def labels(self) -> Dict[str, str]:
        return self._attrs.get("Spec", {}).get("Labels", {})
    
    @property
    def created_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("CreatedAt", "").replace("Z", "+00:00"))
    
    @property
    def updated_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("UpdatedAt", "").replace("Z", "+00:00"))
    
    @property
    def version(self) -> Dict[str, int]:
        return self._attrs.get("Version", {})


class ServiceData:
    """Docker Swarm service information"""
    def __init__(self, service_attrs: Dict[str, Any], host_id: Optional[str] = None):
        self._attrs = service_attrs
        self.host_id = host_id
    
    @property
    def id(self) -> str:
        return self._attrs.get("ID", "")
    
    @property
    def name(self) -> str:
        return self._attrs.get("Spec", {}).get("Name", "")
    
    @property
    def mode(self) -> str:
        mode = self._attrs.get("Spec", {}).get("Mode", {})
        if "Replicated" in mode:
            return "replicated"
        elif "Global" in mode:
            return "global"
        return "unknown"
    
    @property
    def replicas(self) -> Optional[int]:
        if self.mode == "replicated":
            return self._attrs.get("Spec", {}).get("Mode", {}).get("Replicated", {}).get("Replicas", 0)
        return None
    
    @property
    def image(self) -> str:
        return self._attrs.get("Spec", {}).get("TaskTemplate", {}).get("ContainerSpec", {}).get("Image", "")
    
    @property
    def created_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("CreatedAt", "").replace("Z", "+00:00"))
    
    @property
    def updated_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("UpdatedAt", "").replace("Z", "+00:00"))
    
    @property
    def endpoint_spec(self) -> Dict[str, Any]:
        return self._attrs.get("Spec", {}).get("EndpointSpec", {})
    
    @property
    def update_config(self) -> Dict[str, Any]:
        return self._attrs.get("Spec", {}).get("UpdateConfig", {})
    
    @property
    def labels(self) -> Dict[str, str]:
        return self._attrs.get("Spec", {}).get("Labels", {})
    
    @property
    def constraints(self) -> List[str]:
        return self._attrs.get("Spec", {}).get("TaskTemplate", {}).get("Placement", {}).get("Constraints", [])
    
    @property
    def env(self) -> List[str]:
        return self._attrs.get("Spec", {}).get("TaskTemplate", {}).get("ContainerSpec", {}).get("Env", [])
    
    @property
    def mounts(self) -> List[Dict[str, Any]]:
        return self._attrs.get("Spec", {}).get("TaskTemplate", {}).get("ContainerSpec", {}).get("Mounts", [])
    
    @property
    def networks(self) -> List[str]:
        networks = self._attrs.get("Spec", {}).get("TaskTemplate", {}).get("Networks", [])
        return [net.get("Target", "") for net in networks]
    
    @property
    def secrets(self) -> List[str]:
        secrets = self._attrs.get("Spec", {}).get("TaskTemplate", {}).get("ContainerSpec", {}).get("Secrets", [])
        return [secret.get("SecretName", "") for secret in secrets]
    
    @property
    def configs(self) -> List[str]:
        configs = self._attrs.get("Spec", {}).get("TaskTemplate", {}).get("ContainerSpec", {}).get("Configs", [])
        return [config.get("ConfigName", "") for config in configs]
    
    @property
    def version(self) -> Dict[str, int]:
        return self._attrs.get("Version", {})
    
    @property
    def update_status(self) -> Optional[Dict[str, Any]]:
        return self._attrs.get("UpdateStatus")


class TaskData:
    """Docker Swarm task (service instance) information"""
    def __init__(self, task_attrs: Dict[str, Any], host_id: Optional[str] = None):
        self._attrs = task_attrs
        self.host_id = host_id
    
    @property
    def id(self) -> str:
        return self._attrs.get("ID", "")
    
    @property
    def service_id(self) -> str:
        return self._attrs.get("ServiceID", "")
    
    @property
    def node_id(self) -> str:
        return self._attrs.get("NodeID", "")
    
    @property
    def container_id(self) -> Optional[str]:
        container_status = self._attrs.get("Status", {}).get("ContainerStatus", {})
        return container_status.get("ContainerID") if container_status else None
    
    @property
    def slot(self) -> Optional[int]:
        return self._attrs.get("Slot")
    
    @property
    def status(self) -> Dict[str, Any]:
        return self._attrs.get("Status", {})
    
    @property
    def desired_state(self) -> str:
        return self._attrs.get("DesiredState", "")
    
    @property
    def created_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("CreatedAt", "").replace("Z", "+00:00"))
    
    @property
    def updated_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("UpdatedAt", "").replace("Z", "+00:00"))


class SecretData:
    """Docker Swarm secret information"""
    def __init__(self, secret_attrs: Dict[str, Any], host_id: Optional[str] = None):
        self._attrs = secret_attrs
        self.host_id = host_id
    
    @property
    def id(self) -> str:
        return self._attrs.get("ID", "")
    
    @property
    def name(self) -> str:
        return self._attrs.get("Spec", {}).get("Name", "")
    
    @property
    def created_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("CreatedAt", "").replace("Z", "+00:00"))
    
    @property
    def updated_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("UpdatedAt", "").replace("Z", "+00:00"))
    
    @property
    def labels(self) -> Dict[str, str]:
        return self._attrs.get("Spec", {}).get("Labels", {})
    
    @property
    def spec(self) -> Dict[str, Any]:
        # Return spec without the actual secret data
        spec_copy = self._attrs.get("Spec", {}).copy()
        spec_copy.pop("Data", None)  # Remove sensitive data
        return spec_copy
    
    @property
    def version(self) -> Dict[str, int]:
        return self._attrs.get("Version", {})


class ConfigData:
    """Docker Swarm config information"""
    def __init__(self, config_attrs: Dict[str, Any], host_id: Optional[str] = None):
        self._attrs = config_attrs
        self.host_id = host_id
    
    @property
    def id(self) -> str:
        return self._attrs.get("ID", "")
    
    @property
    def name(self) -> str:
        return self._attrs.get("Spec", {}).get("Name", "")
    
    @property
    def data(self) -> Optional[str]:
        # Config data is base64 encoded
        return self._attrs.get("Spec", {}).get("Data")
    
    @property
    def created_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("CreatedAt", "").replace("Z", "+00:00"))
    
    @property
    def updated_at(self) -> datetime:
        return datetime.fromisoformat(self._attrs.get("UpdatedAt", "").replace("Z", "+00:00"))
    
    @property
    def labels(self) -> Dict[str, str]:
        return self._attrs.get("Spec", {}).get("Labels", {})
    
    @property
    def version(self) -> Dict[str, int]:
        return self._attrs.get("Version", {})


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
    
    # Image operations
    async def list_images(
        self,
        name: Optional[str] = None,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[Any]:
        """List images from specified host"""
        image_tuples = await self._executor.list_images(name, all, filters, host_id)
        # Return just the image objects, not the tuples
        return [image for image, _ in image_tuples]
    
    async def get_image(
        self,
        image_id: str,
        host_id: Optional[str] = None
    ) -> Any:
        """Get a specific image"""
        # Since get_image might not be implemented in executor, let's use list_images
        # and find the specific image
        images = await self.list_images(host_id=host_id)
        for image in images:
            if image.id.startswith(image_id) or image_id in [tag.split(':')[-1] for tag in image.tags]:
                return image
        raise Exception(f"Image {image_id} not found")
    
    async def pull_image(
        self,
        repository: str,
        tag: Optional[str] = None,
        auth_config: Optional[Dict[str, str]] = None,
        host_id: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Pull an image from registry"""
        return await self._executor.pull_image(repository, tag, auth_config, host_id, **kwargs)
    
    async def remove_image(
        self,
        image_id: str,
        force: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove an image"""
        await self._executor.remove_image(image_id, force, False, host_id)
    
    async def get_image_history(
        self,
        image_id: str,
        host_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get image history"""
        image = await self._executor.get_image(image_id, host_id)
        history = image.history()
        return [
            {
                "created": h.get("Created"),
                "created_by": h.get("CreatedBy"),
                "size": h.get("Size", 0),
                "comment": h.get("Comment", "")
            }
            for h in history
        ]
    
    async def prune_images(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prune unused images"""
        return await self._executor.prune_images(filters, host_id)
    
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
    
    # Swarm operations
    async def get_swarm_info(
        self,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get swarm information"""
        return await self._executor.get_swarm_info(host_id)
    
    async def init_swarm(
        self,
        advertise_addr: str,
        listen_addr: str = "0.0.0.0:2377",
        force_new_cluster: bool = False,
        host_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Initialize a swarm"""
        return await self._executor.init_swarm(
            advertise_addr, listen_addr, force_new_cluster,
            host_id=host_id, **kwargs
        )
    
    async def join_swarm(
        self,
        remote_addrs: List[str],
        join_token: str,
        advertise_addr: Optional[str] = None,
        listen_addr: str = "0.0.0.0:2377",
        host_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Join a swarm"""
        await self._executor.join_swarm(
            remote_addrs, join_token, advertise_addr,
            listen_addr, host_id=host_id, **kwargs
        )
    
    async def leave_swarm(
        self,
        force: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Leave a swarm"""
        await self._executor.leave_swarm(force, host_id)
    
    async def update_swarm(
        self,
        host_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update swarm configuration"""
        await self._executor.update_swarm(host_id=host_id, **kwargs)
    
    # Node operations
    async def list_nodes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[NodeData]:
        """List swarm nodes"""
        node_tuples = await self._executor.list_nodes(filters, host_id)
        return [NodeData(node.attrs, host_id) for node, host_id in node_tuples]
    
    async def get_node(
        self,
        node_id: str,
        host_id: Optional[str] = None
    ) -> NodeData:
        """Get a swarm node"""
        node, resolved_host_id = await self._executor.get_node(node_id, host_id)
        return NodeData(node.attrs, resolved_host_id)
    
    async def update_node(
        self,
        node_id: str,
        version: int,
        spec: Dict[str, Any],
        host_id: Optional[str] = None
    ) -> NodeData:
        """Update a swarm node"""
        node, resolved_host_id = await self._executor.update_node(
            node_id, version, spec, host_id
        )
        return NodeData(node.attrs, resolved_host_id)
    
    async def remove_node(
        self,
        node_id: str,
        force: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a swarm node"""
        await self._executor.remove_node(node_id, force, host_id)
    
    # Service operations
    async def create_service(
        self,
        image: str,
        name: Optional[str] = None,
        command: Optional[List[str]] = None,
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
        labels: Optional[Dict[str, str]] = None,
        constraints: Optional[List[str]] = None,
        resources: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None,
        **kwargs
    ) -> ServiceData:
        """Create a swarm service"""
        service, resolved_host_id = await self._executor.create_service(
            image=image, name=name, command=command, mode=mode,
            mounts=mounts, networks=networks, endpoint_spec=endpoint_spec,
            update_config=update_config, rollback_config=rollback_config,
            restart_policy=restart_policy, secrets=secrets, configs=configs,
            env=env, labels=labels, constraints=constraints,
            resources=resources, host_id=host_id, **kwargs
        )
        return ServiceData(service.attrs, resolved_host_id)
    
    async def list_services(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[ServiceData]:
        """List swarm services"""
        service_tuples = await self._executor.list_services(filters, host_id)
        return [ServiceData(service.attrs, host_id) for service, host_id in service_tuples]
    
    async def get_service(
        self,
        service_id: str,
        host_id: Optional[str] = None
    ) -> ServiceData:
        """Get a swarm service"""
        service, resolved_host_id = await self._executor.get_service(service_id, host_id)
        return ServiceData(service.attrs, resolved_host_id)
    
    async def update_service(
        self,
        service_id: str,
        version: int,
        host_id: Optional[str] = None,
        **kwargs
    ) -> ServiceData:
        """Update a swarm service"""
        service, resolved_host_id = await self._executor.update_service(
            service_id, version, host_id=host_id, **kwargs
        )
        return ServiceData(service.attrs, resolved_host_id)
    
    async def remove_service(
        self,
        service_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a swarm service"""
        await self._executor.remove_service(service_id, host_id)
    
    async def scale_service(
        self,
        service_id: str,
        replicas: int,
        host_id: Optional[str] = None
    ) -> ServiceData:
        """Scale a swarm service"""
        service, resolved_host_id = await self._executor.scale_service(
            service_id, replicas, host_id
        )
        return ServiceData(service.attrs, resolved_host_id)
    
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
        return await self._executor.service_logs(
            service_id, details, follow, stdout, stderr,
            since, timestamps, tail, host_id
        )
    
    async def list_service_tasks(
        self,
        service_id: str,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[TaskData]:
        """List tasks for a service"""
        task_tuples = await self._executor.list_service_tasks(service_id, filters, host_id)
        return [TaskData(task.attrs, host_id) for task, host_id in task_tuples]
    
    # Secret operations
    async def create_secret(
        self,
        name: str,
        data: bytes,
        labels: Optional[Dict[str, str]] = None,
        host_id: Optional[str] = None
    ) -> SecretData:
        """Create a swarm secret"""
        secret, resolved_host_id = await self._executor.create_secret(
            name, data, labels, host_id=host_id
        )
        return SecretData(secret.attrs, resolved_host_id)
    
    async def list_secrets(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[SecretData]:
        """List swarm secrets"""
        secret_tuples = await self._executor.list_secrets(filters, host_id)
        return [SecretData(secret.attrs, host_id) for secret, host_id in secret_tuples]
    
    async def get_secret(
        self,
        secret_id: str,
        host_id: Optional[str] = None
    ) -> SecretData:
        """Get a swarm secret"""
        secret, resolved_host_id = await self._executor.get_secret(secret_id, host_id)
        return SecretData(secret.attrs, resolved_host_id)
    
    async def remove_secret(
        self,
        secret_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a swarm secret"""
        await self._executor.remove_secret(secret_id, host_id)
    
    # Config operations
    async def create_config(
        self,
        name: str,
        data: bytes,
        labels: Optional[Dict[str, str]] = None,
        host_id: Optional[str] = None
    ) -> ConfigData:
        """Create a swarm config"""
        config, resolved_host_id = await self._executor.create_config(
            name, data, labels, host_id=host_id
        )
        return ConfigData(config.attrs, resolved_host_id)
    
    async def list_configs(
        self,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[ConfigData]:
        """List swarm configs"""
        config_tuples = await self._executor.list_configs(filters, host_id)
        return [ConfigData(config.attrs, host_id) for config, host_id in config_tuples]
    
    async def get_config(
        self,
        config_id: str,
        host_id: Optional[str] = None
    ) -> ConfigData:
        """Get a swarm config"""
        config, resolved_host_id = await self._executor.get_config(config_id, host_id)
        return ConfigData(config.attrs, resolved_host_id)
    
    async def remove_config(
        self,
        config_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a swarm config"""
        await self._executor.remove_config(config_id, host_id)


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