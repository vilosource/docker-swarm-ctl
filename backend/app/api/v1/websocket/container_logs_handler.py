"""
Container Logs WebSocket Handler

Refactored implementation using BaseWebSocketHandler to reduce complexity.
"""

from typing import AsyncGenerator, Optional
from datetime import datetime
import asyncio
from collections import deque

from app.api.v1.websocket.base_handler import BaseWebSocketHandler, WebSocketContext
from app.api.v1.websocket.base import manager
from docker.errors import NotFound, APIError
from app.core.logging import logger


class LogBuffer:
    """Manages log buffering for containers"""
    
    def __init__(self, max_size: int = 1000):
        self.buffers: dict[str, deque] = {}
        self.max_size = max_size
    
    def add_log(self, container_id: str, log_line: str):
        """Add a log line to the buffer"""
        if container_id not in self.buffers:
            self.buffers[container_id] = deque(maxlen=self.max_size)
        self.buffers[container_id].append(log_line)
    
    def get_recent_logs(self, container_id: str, count: int) -> list[str]:
        """Get recent logs from buffer"""
        if container_id not in self.buffers:
            return []
        return list(self.buffers[container_id])[-count:]
    
    def clear_buffer(self, container_id: str):
        """Clear buffer for a container"""
        self.buffers.pop(container_id, None)


class ContainerLogsHandler(BaseWebSocketHandler[str]):
    """
    WebSocket handler for streaming container logs
    
    Reduces complexity by:
    - Using base class for common functionality
    - Extracting log buffering to separate class
    - Simplifying stream management
    """
    
    def __init__(self):
        super().__init__()
        self.log_buffer = LogBuffer()
        self.active_streams: dict[str, AsyncGenerator] = {}
        self.stream_locks: dict[str, asyncio.Lock] = {}
    
    def get_required_permission(self) -> str:
        """Viewers and above can view logs"""
        return "viewer"
    
    async def handle_connection(self, context: WebSocketContext) -> None:
        """Handle log streaming for a container"""
        container_id = context.container_id
        if not container_id:
            raise ValueError("Container ID is required")
        
        # Register connection
        if not await manager.connect(
            context.websocket,
            container_id,
            context.user.username,
            context.is_self_monitoring
        ):
            return
        
        try:
            # Send buffered logs first
            await self._send_buffered_logs(context)
            
            # Check if we need to start a new stream
            connection_count = manager.get_connection_count(container_id)
            
            if connection_count == 1:
                # First connection - start streaming
                await self._start_log_stream(context)
            else:
                # Additional connection - just wait for broadcasts
                await self._wait_for_broadcasts(context)
                
        finally:
            # Cleanup
            await manager.disconnect(
                context.websocket,
                container_id,
                context.is_self_monitoring
            )
            
            # Stop stream if last connection
            if manager.get_connection_count(container_id) == 0:
                await self._stop_stream(container_id)
    
    async def _send_buffered_logs(self, context: WebSocketContext) -> None:
        """Send buffered logs to the client"""
        container_id = context.container_id
        # Get tail parameter from somewhere (could be passed in context)
        tail = 100  # Default value
        
        buffered_logs = self.log_buffer.get_recent_logs(container_id, tail)
        for log_line in buffered_logs:
            await context.websocket.send_json({
                "type": "log",
                "timestamp": datetime.utcnow().isoformat(),
                "data": log_line,
                "container_id": container_id
            })
    
    async def _start_log_stream(self, context: WebSocketContext) -> None:
        """Start streaming logs from Docker"""
        container_id = context.container_id
        
        if not context.is_self_monitoring:
            logger.info(f"Starting log stream for container {container_id}")
        
        try:
            # Get container
            container = context.docker_client.containers.get(container_id)
            
            # Start streaming logs
            log_stream = container.logs(
                stream=True,
                follow=True,
                timestamps=True,
                tail=100  # Could be parameterized
            )
            
            # Store stream reference
            self.active_streams[container_id] = log_stream
            
            # Read and broadcast logs
            log_count = 0
            async for log_line in self._read_logs(log_stream):
                # Decode log line
                if isinstance(log_line, bytes):
                    log_line = log_line.decode('utf-8', errors='replace')
                
                # Buffer the log
                self.log_buffer.add_log(container_id, log_line.strip())
                
                # Broadcast to all connections
                await manager.broadcast_to_container(container_id, {
                    "type": "log",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": log_line.strip(),
                    "container_id": container_id
                })
                log_count += 1
            
            if not context.is_self_monitoring:
                logger.info(f"Log stream ended for container {container_id}, sent {log_count} lines")
                
        except NotFound:
            raise ValueError(f"Container {container_id} not found")
        except APIError as e:
            raise ValueError(f"Docker API error: {str(e)}")
    
    async def _read_logs(self, log_stream: AsyncGenerator) -> AsyncGenerator[str, None]:
        """Async generator to read logs from Docker stream"""
        try:
            for log_line in log_stream:
                yield log_line
                # Allow other tasks to run
                await asyncio.sleep(0)
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
        finally:
            # Ensure stream is closed
            if hasattr(log_stream, 'close'):
                log_stream.close()
    
    async def _wait_for_broadcasts(self, context: WebSocketContext) -> None:
        """Wait for log broadcasts from the primary stream"""
        try:
            while True:
                # Send periodic pings to keep connection alive
                await asyncio.sleep(30)
                try:
                    await context.websocket.send_json({"type": "ping"})
                except:
                    break
        except asyncio.CancelledError:
            pass
    
    async def _stop_stream(self, container_id: str) -> None:
        """Stop the log stream for a container"""
        if container_id in self.active_streams:
            stream = self.active_streams.pop(container_id)
            if hasattr(stream, 'close'):
                try:
                    stream.close()
                except:
                    pass
        
        # Clear buffer after some time to save memory
        await asyncio.sleep(300)  # 5 minutes
        self.log_buffer.clear_buffer(container_id)
    
    async def _legacy_handler(
        self,
        websocket,
        container_id,
        token,
        host_id,
        **kwargs
    ):
        """Fallback to original implementation"""
        # Import and call the original handler
        from app.api.v1.websocket.containers import container_logs_ws
        
        # Extract query parameters
        follow = kwargs.get('follow', True)
        tail = kwargs.get('tail', 100)
        timestamps = kwargs.get('timestamps', True)
        since = kwargs.get('since')
        
        return await container_logs_ws(
            websocket=websocket,
            container_id=container_id,
            follow=follow,
            tail=tail,
            timestamps=timestamps,
            since=since,
            token=token,
            host_id=host_id
        )