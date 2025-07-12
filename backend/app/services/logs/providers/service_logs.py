"""
Service log source provider.

This module implements the LogSource interface for Docker Swarm service logs,
providing access to logs from Swarm services which may span multiple containers.
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator, Optional, List, Any, Dict
import re

from docker.errors import NotFound, APIError
from docker.models.services import Service

from app.core.exceptions import ResourceNotFoundError, DockerOperationError
from app.core.logging import logger
from app.services.async_docker_connection_manager import get_async_docker_connection_manager
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import LogSource, LogEntry, LogSourceMetadata, LogLevel, LogSourceType


class ServiceLogSource(LogSource):
    """
    Log source provider for Docker Swarm services.
    
    This provider handles retrieving logs from Docker Swarm services,
    which aggregate logs from all containers running the service.
    """
    
    def __init__(self, docker_client=None, connection_manager=None):
        """
        Initialize the service log source.
        
        Args:
            docker_client: Optional Docker client instance (for single-host)
            connection_manager: Optional connection manager (for multi-host)
        """
        self.docker_client = docker_client
        self.connection_manager = connection_manager or get_async_docker_connection_manager()
        self._timestamp_pattern = re.compile(
            r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+(.*)$'
        )
        # Service logs may include task/node info
        self._service_log_pattern = re.compile(
            r'^(?:(\S+)\s+\|\s+)?(.*)$'  # Optional task prefix
        )
    
    def get_source_type(self) -> LogSourceType:
        """Get the type of this log source."""
        return LogSourceType.SERVICE
    
    async def get_metadata(self, resource_id: str) -> LogSourceMetadata:
        """Get metadata about a service."""
        return LogSourceMetadata(
            source_type=LogSourceType.SERVICE,
            source_id=resource_id,
            name=f"Service {resource_id[:12]}",
            description="Docker Swarm service logs (aggregated from all replicas)",
            supports_follow=True,
            supports_tail=True,
            supports_timestamps=True,
            supports_filtering=False,
            supports_search=False,
            additional_info={
                "aggregated": True,
                "multi_container": True
            }
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
        Get log stream for a service.
        
        Args:
            resource_id: Service ID
            follow: Whether to follow/tail the logs
            tail: Number of lines to get from the end
            since: Get logs since this timestamp
            until: Get logs until this timestamp
            timestamps: Whether to include timestamps
            host_id: Swarm manager host ID (required)
            user: User for access control (required for multi-host)
            db: Database session (required for multi-host)
            **kwargs: Additional options
            
        Yields:
            LogEntry objects
        """
        # Get Docker client (must be a Swarm manager)
        if self.docker_client:
            client = self.docker_client
        else:
            # Multi-host mode - need host_id, user, and db
            if not all([host_id, user, db]):
                raise ValueError("host_id, user, and db required for multi-host mode")
            client = await self.connection_manager.get_client(host_id, user, db)
        
        # Get service
        try:
            service = await self._get_service(client, resource_id)
        except NotFound:
            raise ResourceNotFoundError("service", resource_id)
        except APIError as e:
            if "This node is not a swarm manager" in str(e):
                raise DockerOperationError("get_service", "Host is not a Swarm manager")
            raise DockerOperationError("get_service", str(e))
        
        # Prepare log options for service.logs()
        # Note: service.logs() has different parameters than container.logs()
        log_kwargs = {
            'follow': follow,
            'timestamps': timestamps,
            'stdout': True,
            'stderr': True
        }
        
        if tail is not None:
            log_kwargs['tail'] = tail
        
        # Note: Docker service logs don't support since/until directly
        # We'd need to filter these client-side if needed
        
        # Get logs from service
        loop = asyncio.get_event_loop()
        
        def get_logs_sync():
            try:
                return service.logs(**log_kwargs)
            except Exception as e:
                logger.error(f"Error getting service logs: {e}")
                raise
        
        # Get the log stream
        log_stream = await loop.run_in_executor(None, get_logs_sync)
        
        # Process log stream
        async for log_line in self._process_log_stream(
            log_stream, 
            resource_id, 
            service.name,
            host_id,
            follow
        ):
            yield log_line
    
    async def _get_service(self, client, service_id: str) -> Service:
        """Get service object."""
        loop = asyncio.get_event_loop()
        
        def get_service_sync():
            return client.services.get(service_id)
        
        return await loop.run_in_executor(None, get_service_sync)
    
    async def _process_log_stream(
        self,
        log_stream,
        service_id: str,
        service_name: str,
        host_id: Optional[str] = None,
        follow: bool = True
    ) -> AsyncIterator[LogEntry]:
        """Process the log stream and yield LogEntry objects."""
        loop = asyncio.get_event_loop()
        
        if follow and hasattr(log_stream, '__iter__'):
            # Streaming mode - log_stream is a generator
            log_iterator = iter(log_stream)
            
            def read_next_line():
                """Read next line from log stream."""
                try:
                    return next(log_iterator)
                except StopIteration:
                    # For service logs in follow mode, StopIteration might mean no new logs yet
                    # Return empty string to indicate no data but don't stop
                    return ""
                except Exception as e:
                    logger.error(f"Error reading service log line: {e}")
                    return None
            
            while True:
                # Read next line in executor
                line = await loop.run_in_executor(None, read_next_line)
                
                if line is None:
                    # None means error, break
                    break
                elif line == "":
                    # Empty string means no new logs, wait and continue
                    await asyncio.sleep(1.0)
                    continue
                
                # Process the line
                entry = self._process_log_line(line, service_id, service_name, host_id)
                if entry:
                    yield entry
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.001)
        else:
            # Non-follow mode - log_stream might be bytes or a list
            if isinstance(log_stream, bytes):
                lines = log_stream.decode('utf-8', errors='replace').split('\n')
            elif isinstance(log_stream, str):
                lines = log_stream.split('\n')
            else:
                # Might be a list or other iterable
                lines = list(log_stream)
            
            for line in lines:
                entry = self._process_log_line(line, service_id, service_name, host_id)
                if entry:
                    yield entry
    
    def _process_log_line(
        self,
        line: Any,
        service_id: str,
        service_name: str,
        host_id: Optional[str] = None
    ) -> Optional[LogEntry]:
        """Process a single log line."""
        # Decode line if needed
        if isinstance(line, bytes):
            line_str = line.decode('utf-8', errors='replace').strip()
        else:
            line_str = str(line).strip()
        
        if not line_str:
            return None
        
        # Parse the log line
        return self._parse_service_log(line_str, service_id, service_name, host_id)
    
    def _parse_service_log(
        self,
        line: str,
        service_id: str,
        service_name: str,
        host_id: Optional[str] = None
    ) -> LogEntry:
        """Parse a service log line into a LogEntry."""
        # Service logs may include task/replica information
        task_info = None
        message = line
        
        # Try to extract task info if present
        service_match = self._service_log_pattern.match(line)
        if service_match and service_match.group(1):
            task_info = service_match.group(1)
            message = service_match.group(2)
        
        # Try to extract timestamp if present
        timestamp_match = self._timestamp_pattern.match(message)
        
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            message = timestamp_match.group(2)
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
        
        # Try to detect log level from message
        level = self._detect_log_level(message)
        
        # Build metadata
        metadata = {
            "service_id": service_id[:12],
            "service_name": service_name
        }
        
        if task_info:
            metadata["task_info"] = task_info
        
        return LogEntry(
            timestamp=timestamp,
            source_type=LogSourceType.SERVICE,
            source_id=service_id,
            message=message,
            level=level,
            host_id=host_id,
            metadata=metadata,
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
        """Validate that the user has access to service logs."""
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
        """Search is not implemented for service logs."""
        raise NotImplementedError("Service log search is not yet implemented")