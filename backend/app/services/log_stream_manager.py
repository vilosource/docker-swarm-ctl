"""
Log Stream Manager Service

Manages Docker log streams efficiently with proper lifecycle management,
avoiding duplicate streams and handling cleanup correctly.
"""

from typing import Dict, Optional, AsyncGenerator, Any, Set
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
from enum import Enum

from docker.models.containers import Container
from docker.errors import NotFound, APIError
from app.core.logging import logger
from app.services.log_buffer_service import get_log_buffer_service
from app.services.self_monitoring_detector import is_self_monitoring


class StreamStatus(str, Enum):
    """Status of a log stream"""
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class LogStream:
    """Represents an active log stream"""
    
    def __init__(
        self,
        container_id: str,
        container: Container,
        follow: bool = True,
        tail: int = 100
    ):
        self.container_id = container_id
        self.container = container
        self.follow = follow
        self.tail = tail
        self.status = StreamStatus.STARTING
        self.stream: Optional[AsyncGenerator] = None
        self.task: Optional[asyncio.Task] = None
        self.subscribers: Set[str] = set()
        self.created_at = datetime.utcnow()
        self.last_log_at: Optional[datetime] = None
        self.log_count = 0
        self.error: Optional[str] = None
    
    def add_subscriber(self, subscriber_id: str):
        """Add a subscriber to this stream"""
        self.subscribers.add(subscriber_id)
    
    def remove_subscriber(self, subscriber_id: str):
        """Remove a subscriber from this stream"""
        self.subscribers.discard(subscriber_id)
    
    @property
    def subscriber_count(self) -> int:
        """Get number of active subscribers"""
        return len(self.subscribers)
    
    @property
    def is_active(self) -> bool:
        """Check if stream is active"""
        return self.status == StreamStatus.ACTIVE
    
    def get_info(self) -> Dict[str, Any]:
        """Get stream information"""
        return {
            "container_id": self.container_id,
            "status": self.status,
            "follow": self.follow,
            "tail": self.tail,
            "subscribers": self.subscriber_count,
            "created_at": self.created_at.isoformat(),
            "last_log_at": self.last_log_at.isoformat() if self.last_log_at else None,
            "log_count": self.log_count,
            "error": self.error
        }


class LogStreamManager:
    """
    Singleton service for managing Docker log streams
    
    Features:
    - Prevents duplicate streams for the same container
    - Manages stream lifecycle (start, stop, cleanup)
    - Handles subscriber tracking
    - Integrates with LogBufferService
    - Provides stream statistics
    """
    
    _instance: Optional['LogStreamManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.streams: Dict[str, LogStream] = {}
            self.locks: Dict[str, asyncio.Lock] = {}
            self._global_lock = asyncio.Lock()
            self._log_handlers: Dict[str, callable] = {}
            self._initialized = True
            logger.info("LogStreamManager initialized")
    
    @asynccontextmanager
    async def get_stream(
        self,
        container_id: str,
        docker_client: Any,
        follow: bool = True,
        tail: int = 100,
        subscriber_id: Optional[str] = None
    ) -> AsyncGenerator[Optional[LogStream], None]:
        """
        Get or create a log stream for a container
        
        Usage:
            async with manager.get_stream(container_id, docker_client) as stream:
                if stream:
                    # Use the stream
        """
        stream = None
        
        try:
            # Get or create stream
            stream = await self._get_or_create_stream(
                container_id, docker_client, follow, tail
            )
            
            # Add subscriber if provided
            if stream and subscriber_id:
                stream.add_subscriber(subscriber_id)
            
            yield stream
            
        finally:
            # Cleanup: remove subscriber and potentially stop stream
            if stream and subscriber_id:
                stream.remove_subscriber(subscriber_id)
                
                # Check if we should stop the stream
                if stream.subscriber_count == 0 and stream.follow:
                    await self.stop_stream(container_id)
    
    async def _get_or_create_stream(
        self,
        container_id: str,
        docker_client: Any,
        follow: bool,
        tail: int
    ) -> Optional[LogStream]:
        """Get existing stream or create a new one"""
        # Ensure we have a lock for this container
        if container_id not in self.locks:
            async with self._global_lock:
                if container_id not in self.locks:
                    self.locks[container_id] = asyncio.Lock()
        
        async with self.locks[container_id]:
            # Check for existing stream
            if container_id in self.streams:
                stream = self.streams[container_id]
                
                # If existing stream matches requirements, return it
                if stream.follow == follow and stream.is_active:
                    return stream
                
                # Otherwise, stop the old stream and create new one
                await self._stop_stream_internal(container_id)
            
            # Check if self-monitoring
            if is_self_monitoring(container_id, docker_client):
                logger.info(f"Skipping log stream for self-monitoring container {container_id}")
                return None
            
            # Create new stream
            try:
                container = docker_client.containers.get(container_id)
                stream = LogStream(container_id, container, follow, tail)
                self.streams[container_id] = stream
                
                # Start the stream
                await self._start_stream(stream)
                
                return stream
                
            except NotFound:
                logger.error(f"Container {container_id} not found")
                raise ValueError(f"Container {container_id} not found")
            except APIError as e:
                logger.error(f"Docker API error for container {container_id}: {str(e)}")
                raise ValueError(f"Docker API error: {str(e)}")
    
    async def _start_stream(self, stream: LogStream):
        """Start streaming logs for a container"""
        logger.info(f"Starting log stream for container {stream.container_id}")
        
        # Create the log stream
        try:
            docker_stream = stream.container.logs(
                stream=True,
                follow=stream.follow,
                timestamps=True,
                tail=stream.tail
            )
            
            # Start the streaming task
            stream.task = asyncio.create_task(
                self._stream_logs(stream, docker_stream)
            )
            
            stream.status = StreamStatus.ACTIVE
            
        except Exception as e:
            logger.error(f"Failed to start log stream: {e}")
            stream.status = StreamStatus.ERROR
            stream.error = str(e)
            raise
    
    async def _stream_logs(self, stream: LogStream, docker_stream):
        """Stream logs from Docker to subscribers and buffer"""
        log_buffer_service = await get_log_buffer_service()
        
        try:
            for log_line in docker_stream:
                # Decode log line
                if isinstance(log_line, bytes):
                    log_line = log_line.decode('utf-8', errors='replace')
                
                log_line = log_line.strip()
                if not log_line:
                    continue
                
                # Update stream stats
                stream.last_log_at = datetime.utcnow()
                stream.log_count += 1
                
                # Add to buffer
                await log_buffer_service.add_log(
                    stream.container_id,
                    log_line,
                    timestamp=stream.last_log_at
                )
                
                # Call any registered handlers
                if stream.container_id in self._log_handlers:
                    handler = self._log_handlers[stream.container_id]
                    try:
                        await handler(log_line)
                    except Exception as e:
                        logger.error(f"Error in log handler: {e}")
                
                # Allow other tasks to run
                await asyncio.sleep(0)
                
        except asyncio.CancelledError:
            logger.info(f"Log stream cancelled for container {stream.container_id}")
        except Exception as e:
            logger.error(f"Error in log stream: {e}")
            stream.status = StreamStatus.ERROR
            stream.error = str(e)
        finally:
            # Cleanup
            stream.status = StreamStatus.STOPPED
            if hasattr(docker_stream, 'close'):
                docker_stream.close()
    
    async def stop_stream(self, container_id: str):
        """Stop a log stream for a container"""
        async with self.locks.get(container_id, self._global_lock):
            await self._stop_stream_internal(container_id)
    
    async def _stop_stream_internal(self, container_id: str):
        """Internal method to stop a stream (must be called with lock held)"""
        if container_id not in self.streams:
            return
        
        stream = self.streams[container_id]
        
        if stream.status == StreamStatus.STOPPING:
            # Already stopping
            return
        
        logger.info(f"Stopping log stream for container {container_id}")
        stream.status = StreamStatus.STOPPING
        
        # Cancel the streaming task
        if stream.task and not stream.task.done():
            stream.task.cancel()
            try:
                await stream.task
            except asyncio.CancelledError:
                pass
        
        # Remove from active streams
        del self.streams[container_id]
        
        # Remove handler if exists
        self._log_handlers.pop(container_id, None)
    
    async def stop_all_streams(self):
        """Stop all active streams"""
        container_ids = list(self.streams.keys())
        
        for container_id in container_ids:
            await self.stop_stream(container_id)
    
    def register_log_handler(self, container_id: str, handler: callable):
        """Register a handler to be called for each log line"""
        self._log_handlers[container_id] = handler
    
    def unregister_log_handler(self, container_id: str):
        """Unregister a log handler"""
        self._log_handlers.pop(container_id, None)
    
    def get_stream_info(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific stream"""
        stream = self.streams.get(container_id)
        return stream.get_info() if stream else None
    
    def get_all_streams_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active streams"""
        return {
            container_id: stream.get_info()
            for container_id, stream in self.streams.items()
        }
    
    @property
    def active_stream_count(self) -> int:
        """Get count of active streams"""
        return sum(1 for s in self.streams.values() if s.is_active)
    
    @property
    def total_subscriber_count(self) -> int:
        """Get total subscriber count across all streams"""
        return sum(s.subscriber_count for s in self.streams.values())


# Global instance
_log_stream_manager = LogStreamManager()


def get_log_stream_manager() -> LogStreamManager:
    """Get the global LogStreamManager instance"""
    return _log_stream_manager