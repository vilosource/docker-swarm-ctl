"""
Docker Service Abstraction Layer

This module provides a unified interface for Docker operations across single and multiple hosts.
It follows SOLID principles and provides backward compatibility for single-host deployments.
"""

from typing import List, Optional, Dict, Any, Protocol
from abc import ABC, abstractmethod
from uuid import UUID
import json
import asyncio
from docker.client import DockerClient
from docker.models.containers import Container
from docker.models.images import Image
from docker.errors import DockerException, APIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DockerConnectionError, DockerOperationError, AuthorizationError
from app.models import User, DockerHost
from app.services.docker_connection_manager import DockerConnectionManager, get_docker_connection_manager
from app.services.docker_client import get_docker_client
from app.core.logging import logger


class ContainerData:
    """Data class for container information"""
    def __init__(self, container: Container, host_id: Optional[str] = None):
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


class IDockerService(Protocol):
    """Interface for Docker operations"""
    
    async def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[ContainerData]:
        ...
    
    async def get_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> ContainerData:
        ...
    
    async def create_container(
        self,
        config: Dict[str, Any],
        host_id: Optional[str] = None
    ) -> ContainerData:
        ...
    
    async def start_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> None:
        ...
    
    async def stop_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        ...
    
    async def restart_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        ...
    
    async def remove_container(
        self,
        container_id: str,
        force: bool = False,
        volumes: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        ...
    
    async def get_container_logs(
        self,
        container_id: str,
        lines: int = 100,
        timestamps: bool = False,
        host_id: Optional[str] = None
    ) -> str:
        ...
    
    async def get_container_stats(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        ...
    
    async def inspect_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        ...


class SingleHostDockerService:
    """Docker service implementation for single-host deployments (backward compatible)"""
    
    def __init__(self):
        self._client = get_docker_client()
    
    async def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[ContainerData]:
        """List containers from the local Docker daemon"""
        kwargs = {"all": all}
        if filters:
            kwargs["filters"] = filters
        
        containers = self._client.containers.list(**kwargs)
        return [ContainerData(c) for c in containers]
    
    async def get_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> ContainerData:
        """Get a specific container"""
        try:
            container = self._client.containers.get(container_id)
            return ContainerData(container)
        except Exception as e:
            raise DockerOperationError("get_container", f"Container {container_id} not found")
    
    async def create_container(
        self,
        config: Dict[str, Any],
        host_id: Optional[str] = None
    ) -> ContainerData:
        """Create a new container"""
        try:
            container = self._client.containers.run(**config)
            return ContainerData(container)
        except Exception as e:
            raise DockerOperationError("create_container", str(e))
    
    async def start_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Start a container"""
        try:
            container = self._client.containers.get(container_id)
            container.start()
        except Exception as e:
            raise DockerOperationError("start_container", str(e))
    
    async def stop_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        """Stop a container"""
        try:
            container = self._client.containers.get(container_id)
            container.stop(timeout=timeout)
        except Exception as e:
            raise DockerOperationError("stop_container", str(e))
    
    async def restart_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        """Restart a container"""
        try:
            container = self._client.containers.get(container_id)
            container.restart(timeout=timeout)
        except Exception as e:
            raise DockerOperationError("restart_container", str(e))
    
    async def remove_container(
        self,
        container_id: str,
        force: bool = False,
        volumes: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a container"""
        try:
            container = self._client.containers.get(container_id)
            container.remove(force=force, v=volumes)
        except Exception as e:
            raise DockerOperationError("remove_container", str(e))
    
    async def get_container_logs(
        self,
        container_id: str,
        lines: int = 100,
        timestamps: bool = False,
        host_id: Optional[str] = None
    ) -> str:
        """Get container logs"""
        try:
            container = self._client.containers.get(container_id)
            logs = container.logs(tail=lines, timestamps=timestamps, stream=False)
            return logs.decode("utf-8")
        except Exception as e:
            raise DockerOperationError("get_container_logs", str(e))
    
    async def get_container_stats(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get container stats"""
        try:
            container = self._client.containers.get(container_id)
            return container.stats(stream=False)
        except Exception as e:
            raise DockerOperationError("get_container_stats", str(e))
    
    async def inspect_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inspect a container"""
        try:
            container = self._client.containers.get(container_id)
            return container.attrs
        except Exception as e:
            raise DockerOperationError("inspect_container", str(e))


class MultiHostDockerService:
    """Docker service implementation for multi-host deployments"""
    
    def __init__(
        self,
        connection_manager: DockerConnectionManager,
        user: User,
        db: AsyncSession
    ):
        self._connection_manager = connection_manager
        self._user = user
        self._db = db
    
    async def _get_client(self, host_id: Optional[str] = None) -> tuple[DockerClient, str]:
        """Get Docker client for the specified host or default host"""
        if not host_id:
            # Get default host for user
            host_id = await self._connection_manager.get_default_host_id(self._db, self._user)
            if not host_id:
                raise DockerConnectionError("No accessible Docker hosts found")
        
        client = await self._connection_manager.get_client(host_id, self._user, self._db)
        return client, host_id
    
    async def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        host_id: Optional[str] = None
    ) -> List[ContainerData]:
        """List containers from specified or default host"""
        client, resolved_host_id = await self._get_client(host_id)
        
        kwargs = {"all": all}
        if filters:
            kwargs["filters"] = filters
        
        containers = client.containers.list(**kwargs)
        return [ContainerData(c, resolved_host_id) for c in containers]
    
    async def get_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> ContainerData:
        """Get a specific container"""
        client, resolved_host_id = await self._get_client(host_id)
        
        try:
            container = client.containers.get(container_id)
            return ContainerData(container, resolved_host_id)
        except Exception as e:
            raise DockerOperationError("get_container", f"Container {container_id} not found")
    
    async def create_container(
        self,
        config: Dict[str, Any],
        host_id: Optional[str] = None
    ) -> ContainerData:
        """Create a new container"""
        client, resolved_host_id = await self._get_client(host_id)
        
        try:
            container = client.containers.run(**config)
            return ContainerData(container, resolved_host_id)
        except Exception as e:
            raise DockerOperationError("create_container", str(e))
    
    async def start_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> None:
        """Start a container"""
        client, resolved_host_id = await self._get_client(host_id)
        
        try:
            container = client.containers.get(container_id)
            container.start()
        except Exception as e:
            raise DockerOperationError("start_container", str(e))
    
    async def stop_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        """Stop a container"""
        client, resolved_host_id = await self._get_client(host_id)
        
        try:
            container = client.containers.get(container_id)
            container.stop(timeout=timeout)
        except Exception as e:
            raise DockerOperationError("stop_container", str(e))
    
    async def restart_container(
        self,
        container_id: str,
        timeout: int = 10,
        host_id: Optional[str] = None
    ) -> None:
        """Restart a container"""
        client, resolved_host_id = await self._get_client(host_id)
        
        try:
            container = client.containers.get(container_id)
            container.restart(timeout=timeout)
        except Exception as e:
            raise DockerOperationError("restart_container", str(e))
    
    async def remove_container(
        self,
        container_id: str,
        force: bool = False,
        volumes: bool = False,
        host_id: Optional[str] = None
    ) -> None:
        """Remove a container"""
        client, resolved_host_id = await self._get_client(host_id)
        
        try:
            container = client.containers.get(container_id)
            container.remove(force=force, v=volumes)
        except Exception as e:
            raise DockerOperationError("remove_container", str(e))
    
    async def get_container_logs(
        self,
        container_id: str,
        lines: int = 100,
        timestamps: bool = False,
        host_id: Optional[str] = None
    ) -> str:
        """Get container logs"""
        client, resolved_host_id = await self._get_client(host_id)
        
        try:
            container = client.containers.get(container_id)
            logs = container.logs(tail=lines, timestamps=timestamps, stream=False)
            return logs.decode("utf-8")
        except Exception as e:
            raise DockerOperationError("get_container_logs", str(e))
    
    async def get_container_stats(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get container stats"""
        client, resolved_host_id = await self._get_client(host_id)
        
        try:
            container = client.containers.get(container_id)
            return container.stats(stream=False)
        except Exception as e:
            raise DockerOperationError("get_container_stats", str(e))
    
    async def inspect_container(
        self,
        container_id: str,
        host_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inspect a container"""
        client, resolved_host_id = await self._get_client(host_id)
        
        try:
            container = client.containers.get(container_id)
            return container.attrs
        except Exception as e:
            raise DockerOperationError("inspect_container", str(e))


class DockerServiceFactory:
    """Factory for creating appropriate Docker service implementation"""
    
    @staticmethod
    def create(
        user: Optional[User] = None,
        db: Optional[AsyncSession] = None,
        multi_host_enabled: bool = True
    ) -> IDockerService:
        """
        Create Docker service instance based on configuration
        
        Args:
            user: Current user (required for multi-host)
            db: Database session (required for multi-host)
            multi_host_enabled: Whether multi-host support is enabled
            
        Returns:
            Appropriate Docker service implementation
        """
        if multi_host_enabled and user and db:
            connection_manager = get_docker_connection_manager()
            return MultiHostDockerService(connection_manager, user, db)
        else:
            return SingleHostDockerService()


# Dependency injection helper
async def get_docker_service(
    user: User,
    db: AsyncSession,
    multi_host_enabled: bool = True
) -> IDockerService:
    """Get Docker service instance for dependency injection"""
    return DockerServiceFactory.create(user, db, multi_host_enabled)