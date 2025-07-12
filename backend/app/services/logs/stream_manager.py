"""
Unified stream management for log sources.

This module provides connection pooling, buffering, and broadcast capabilities
for efficiently managing multiple WebSocket connections to the same log stream.
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Set, Optional, AsyncIterator, Deque, Any
from contextlib import asynccontextmanager
from fastapi import WebSocket

from app.core.logging import logger
from .base import LogEntry, LogSource, LogSourceType


@dataclass
class LogStream:
    """Represents an active log stream."""
    resource_id: str
    source_type: LogSourceType
    provider: LogSource
    task: Optional[asyncio.Task] = None
    is_active: bool = False
    buffer: Deque[LogEntry] = field(default_factory=lambda: deque(maxlen=1000))
    connections: Set[WebSocket] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)


class UnifiedLogStreamManager:
    """
    Manages log streams with connection pooling and buffering.
    
    This class ensures that:
    - Only one log stream exists per resource
    - Multiple WebSocket connections can share the same stream
    - Recent logs are buffered for late-joining connections
    - Streams are properly cleaned up when no longer needed
    """
    
    def __init__(self, buffer_size: int = 1000, stream_timeout: int = 300):
        """
        Initialize the stream manager.
        
        Args:
            buffer_size: Number of recent log entries to buffer per stream
            stream_timeout: Seconds to keep idle streams alive
        """
        self.buffer_size = buffer_size
        self.stream_timeout = stream_timeout
        self.streams: Dict[str, LogStream] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the stream manager and cleanup task."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_streams())
        logger.info("Unified log stream manager started")
    
    async def stop(self):
        """Stop the stream manager and cleanup all streams."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all active streams
        for stream_key in list(self.streams.keys()):
            await self._close_stream(stream_key)
        
        logger.info("Unified log stream manager stopped")
    
    def _get_stream_key(self, source_type: LogSourceType, resource_id: str) -> str:
        """Generate a unique key for a log stream."""
        return f"{source_type}:{resource_id}"
    
    async def connect(
        self,
        websocket: WebSocket,
        source_type: LogSourceType,
        resource_id: str,
        provider: LogSource,
        tail: int = 100
    ) -> bool:
        """
        Connect a WebSocket to a log stream.
        
        Args:
            websocket: The WebSocket connection
            source_type: Type of log source
            resource_id: ID of the resource
            provider: Log source provider
            tail: Number of buffered entries to send
            
        Returns:
            True if connection successful, False otherwise
        """
        stream_key = self._get_stream_key(source_type, resource_id)
        
        # Get or create lock for this stream
        if stream_key not in self.locks:
            self.locks[stream_key] = asyncio.Lock()
        
        async with self.locks[stream_key]:
            # Get or create stream
            if stream_key not in self.streams:
                stream = LogStream(
                    resource_id=resource_id,
                    source_type=source_type,
                    provider=provider
                )
                self.streams[stream_key] = stream
                stream.is_active = True
                logger.info(f"Started new log stream for {stream_key}")
            else:
                stream = self.streams[stream_key]
            
            # Add connection to stream
            stream.connections.add(websocket)
            stream.last_activity = datetime.utcnow()
            
            # Send buffered logs to new connection
            if tail > 0 and stream.buffer:
                buffered_entries = list(stream.buffer)[-tail:]
                for entry in buffered_entries:
                    await self._send_log_entry(websocket, entry)
            
            logger.info(f"Connected WebSocket to stream {stream_key} "
                       f"(total connections: {len(stream.connections)})")
            return True
    
    async def disconnect(
        self,
        websocket: WebSocket,
        source_type: LogSourceType,
        resource_id: str
    ):
        """
        Disconnect a WebSocket from a log stream.
        
        Args:
            websocket: The WebSocket connection
            source_type: Type of log source
            resource_id: ID of the resource
        """
        stream_key = self._get_stream_key(source_type, resource_id)
        
        if stream_key in self.streams:
            stream = self.streams[stream_key]
            stream.connections.discard(websocket)
            stream.last_activity = datetime.utcnow()
            
            logger.info(f"Disconnected WebSocket from stream {stream_key} "
                       f"(remaining connections: {len(stream.connections)})")
            
            # Close stream if no connections remain
            if not stream.connections:
                await self._close_stream(stream_key)
    
    async def broadcast(
        self,
        source_type: LogSourceType,
        resource_id: str,
        entry: LogEntry
    ):
        """
        Broadcast a log entry to all connected clients.
        
        Args:
            source_type: Type of log source
            resource_id: ID of the resource
            entry: Log entry to broadcast
        """
        stream_key = self._get_stream_key(source_type, resource_id)
        
        if stream_key in self.streams:
            stream = self.streams[stream_key]
            
            # Add to buffer
            stream.buffer.append(entry)
            stream.last_activity = datetime.utcnow()
            
            # Broadcast to all connections
            disconnected = []
            for websocket in stream.connections:
                try:
                    await self._send_log_entry(websocket, entry)
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket: {e}")
                    disconnected.append(websocket)
            
            # Remove disconnected clients
            for websocket in disconnected:
                stream.connections.discard(websocket)
    
    async def _send_log_entry(self, websocket: WebSocket, entry: LogEntry):
        """Send a log entry to a WebSocket connection."""
        await websocket.send_json({
            "type": "log",
            "timestamp": entry.timestamp.isoformat(),
            "source_type": entry.source_type,
            "source_id": entry.source_id,
            "message": entry.message,
            "level": entry.level,
            "metadata": entry.metadata
        })
    
    async def _stream_logs(self, stream_key: str):
        """
        Stream logs from the provider and broadcast to connections.
        
        This runs in a separate task for each active stream.
        """
        stream = self.streams.get(stream_key)
        if not stream:
            return
        
        try:
            logger.info(f"Starting log streaming for {stream_key}")
            
            # Get logs from provider
            async for entry in stream.provider.get_logs(
                stream.resource_id,
                follow=True,
                tail=100,  # Get initial history
                timestamps=True
            ):
                # Check if stream is still active
                if stream_key not in self.streams or not stream.is_active:
                    break
                
                # Broadcast to all connections
                await self.broadcast(
                    stream.source_type,
                    stream.resource_id,
                    entry
                )
            
            logger.info(f"Log streaming ended for {stream_key}")
            
        except Exception as e:
            logger.error(f"Error in log stream {stream_key}: {e}")
            
            # Send error to all connections
            for websocket in list(stream.connections):
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Log stream error: {str(e)}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except:
                    pass
        
        finally:
            # Mark stream as inactive
            if stream_key in self.streams:
                self.streams[stream_key].is_active = False
    
    async def _close_stream(self, stream_key: str):
        """Close and cleanup a log stream."""
        if stream_key not in self.streams:
            return
        
        stream = self.streams[stream_key]
        
        # Cancel streaming task
        if stream.task and not stream.task.done():
            stream.task.cancel()
            try:
                await stream.task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for websocket in list(stream.connections):
            try:
                await websocket.close()
            except:
                pass
        
        # Remove stream and lock
        del self.streams[stream_key]
        if stream_key in self.locks:
            del self.locks[stream_key]
        
        logger.info(f"Closed log stream {stream_key}")
    
    async def _cleanup_idle_streams(self):
        """Periodically cleanup idle streams."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                now = datetime.utcnow()
                idle_streams = []
                
                for stream_key, stream in self.streams.items():
                    # Check if stream is idle
                    if (not stream.connections and 
                        (now - stream.last_activity).total_seconds() > self.stream_timeout):
                        idle_streams.append(stream_key)
                
                # Close idle streams
                for stream_key in idle_streams:
                    logger.info(f"Closing idle stream {stream_key}")
                    await self._close_stream(stream_key)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active streams."""
        return {
            stream_key: {
                "resource_id": stream.resource_id,
                "source_type": stream.source_type,
                "connections": len(stream.connections),
                "buffer_size": len(stream.buffer),
                "is_active": stream.is_active,
                "created_at": stream.created_at.isoformat(),
                "last_activity": stream.last_activity.isoformat()
            }
            for stream_key, stream in self.streams.items()
        }


# Global instance
_stream_manager: Optional[UnifiedLogStreamManager] = None


def get_stream_manager() -> UnifiedLogStreamManager:
    """Get the global stream manager instance."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = UnifiedLogStreamManager()
    return _stream_manager


@asynccontextmanager
async def stream_manager_lifespan():
    """Async context manager for stream manager lifecycle."""
    manager = get_stream_manager()
    await manager.start()
    try:
        yield manager
    finally:
        await manager.stop()