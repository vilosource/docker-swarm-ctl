"""
Container log source provider.

This module implements the LogSource interface for Docker container logs,
providing access to logs from individual containers.
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator, Optional, List, Any, Dict
import re

# Remove docker-py imports - using aiodocker now

from app.core.exceptions import ResourceNotFoundError, DockerOperationError
from app.core.logging import logger
from app.services.async_docker_connection_manager import get_async_docker_connection_manager
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import LogSource, LogEntry, LogSourceMetadata, LogLevel, LogSourceType


class ContainerLogSource(LogSource):
    """
    Log source provider for Docker containers.
    
    This provider handles retrieving logs from Docker containers,
    including support for following logs, tail selection, and timestamps.
    """
    
    def __init__(self, docker_client=None, connection_manager=None):
        """
        Initialize the container log source.
        
        Args:
            docker_client: Optional Docker client instance (for single-host)
            connection_manager: Optional connection manager (for multi-host)
        """
        self.docker_client = docker_client
        self.connection_manager = connection_manager or get_async_docker_connection_manager()
        self._timestamp_pattern = re.compile(
            r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+(.*)$'
        )
    
    def get_source_type(self) -> LogSourceType:
        """Get the type of this log source."""
        return LogSourceType.CONTAINER
    
    async def get_metadata(self, resource_id: str) -> LogSourceMetadata:
        """Get metadata about a container."""
        # For now, we'll use a simplified approach
        # In a full implementation, this would get the container info
        return LogSourceMetadata(
            source_type=LogSourceType.CONTAINER,
            source_id=resource_id,
            name=f"Container {resource_id[:12]}",
            description="Docker container logs",
            supports_follow=True,
            supports_tail=True,
            supports_timestamps=True,
            supports_filtering=False,
            supports_search=False
        )
    
    async def get_logs(
        self,
        resource_id: str,
        follow: bool = True,
        tail: Optional[int] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        timestamps: bool = True,
        host_id: Optional[str] = None,
        user: Optional[User] = None,
        db: Optional[AsyncSession] = None,
        **kwargs
    ) -> AsyncIterator[LogEntry]:
        """
        Get log stream for a container.
        
        Args:
            resource_id: Container ID
            follow: Whether to follow/tail the logs
            tail: Number of lines to get from the end
            since: Get logs since this timestamp
            until: Get logs until this timestamp
            timestamps: Whether to include timestamps
            host_id: Optional host ID for multi-host deployments
            user: Optional user for access control
            db: Optional database session
            **kwargs: Additional options
            
        Yields:
            LogEntry objects
        """
        # Get Docker client
        if self.docker_client:
            client = self.docker_client
        else:
            # Multi-host mode - need host_id, user, and db
            if not all([host_id, user, db]):
                raise ValueError("host_id, user, and db required for multi-host mode")
            client = await self.connection_manager.get_client(host_id, user, db)
        
        # Get container using aiodocker
        container = await self._get_container(client, resource_id)
        
        # Prepare log options for aiodocker
        log_kwargs = {
            'stdout': True,
            'stderr': True,
            'follow': follow,
            'timestamps': timestamps
        }
        
        if tail is not None:
            log_kwargs['tail'] = tail if tail != 'all' else None
        if since is not None:
            log_kwargs['since'] = since
        if until is not None:
            log_kwargs['until'] = until
        
        # Get logs from container using aiodocker async interface
        try:
            # aiodocker log() returns different types based on follow parameter
            if follow:
                # For follow=True, it returns an async generator
                log_stream = container.log(**log_kwargs)
            else:
                # For follow=False, it returns a list/string that can be awaited
                log_stream = await container.log(**log_kwargs)
        except Exception as e:
            logger.error(f"Error getting container logs: {e}")
            raise DockerOperationError("get_logs", str(e))
        
        # Process log stream
        async for log_line in self._process_log_stream(log_stream, resource_id, host_id):
            yield log_line
    
    async def _get_container(self, client, container_id: str):
        """Get container object using aiodocker."""
        try:
            return await client.containers.get(container_id)
        except Exception as e:
            if "No such container" in str(e) or "404" in str(e):
                raise ResourceNotFoundError("container", container_id)
            raise DockerOperationError("get_container", str(e))
    
    async def _process_log_stream(
        self,
        log_stream,
        container_id: str,
        host_id: Optional[str] = None
    ) -> AsyncIterator[LogEntry]:
        """Process the aiodocker log stream and yield LogEntry objects."""
        try:
            # Check if log_stream is an async generator (follow=True case)
            if hasattr(log_stream, '__aiter__'):
                # Handle async generator for follow=True
                async for log_chunk in log_stream:
                    if log_chunk and log_chunk.strip():
                        yield self._parse_container_log(log_chunk.strip(), container_id, host_id)
            elif isinstance(log_stream, list):
                # Handle list of log lines (follow=False case)
                for line in log_stream:
                    if line and line.strip():
                        yield self._parse_container_log(line.strip(), container_id, host_id)
            elif isinstance(log_stream, str):
                # Handle single string with newlines (follow=False case)
                for line in log_stream.split('\n'):
                    if line.strip():
                        yield self._parse_container_log(line.strip(), container_id, host_id)
            else:
                # Handle other formats
                logger.warning(f"Unexpected log stream format: {type(log_stream)}")
                
        except Exception as e:
            logger.error(f"Error processing log stream: {e}")
            raise
    
    def _parse_container_log(
        self,
        line: str,
        container_id: str,
        host_id: Optional[str] = None
    ) -> LogEntry:
        """Parse a container log line into a LogEntry."""
        # Try to extract timestamp if present
        timestamp_match = self._timestamp_pattern.match(line)
        
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            message = timestamp_match.group(2)
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
            message = line
        
        # Try to detect log level from message
        level = self._detect_log_level(message)
        
        return LogEntry(
            timestamp=timestamp,
            source_type=LogSourceType.CONTAINER,
            source_id=container_id,
            message=message,
            level=level,
            host_id=host_id,
            metadata={
                "container_id": container_id[:12]
            },
            raw_line=line
        )
    
    def _detect_log_level(self, message: str) -> LogLevel:
        """Detect log level from message content."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['error', 'err', 'fail']):
            return LogLevel.ERROR
        elif any(word in message_lower for word in ['warn', 'warning']):
            return LogLevel.WARNING
        elif any(word in message_lower for word in ['debug', 'trace']):
            return LogLevel.DEBUG
        elif any(word in message_lower for word in ['info', 'notice']):
            return LogLevel.INFO
        elif any(word in message_lower for word in ['critical', 'fatal', 'panic']):
            return LogLevel.CRITICAL
        else:
            return LogLevel.INFO  # Default to INFO
    
    async def validate_access(self, resource_id: str, user: Any) -> bool:
        """Validate that the user has access to container logs."""
        # For now, we'll implement basic role checking
        # In a full implementation, this would check specific permissions
        if hasattr(user, 'role'):
            return user.role in ['admin', 'operator', 'viewer']
        return False
    
    async def search_logs(
        self,
        resource_id: str,
        query: str,
        limit: Optional[int] = None,
        **kwargs
    ) -> List[LogEntry]:
        """Search is not implemented for container logs."""
        raise NotImplementedError("Container log search is not yet implemented")