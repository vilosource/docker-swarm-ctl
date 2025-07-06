"""
Refactored Container WebSocket Handlers

Simplified implementation using enhanced base handler and stream management.
"""

from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.websocket.enhanced_base_handler import (
    EnhancedWebSocketHandler,
    WebSocketState,
    ResourceType
)
from app.services.docker_stream_handler import DockerStreamHandler
from app.services.self_monitoring import get_self_monitoring_service
from app.services.docker_service import DockerServiceFactory
from app.core.exceptions import DockerOperationError
from app.core.logging import logger
from app.models import User
from app.db.session import get_db
from app.api.v1.websocket.auth import get_current_user_ws


class ContainerLogsHandler(EnhancedWebSocketHandler):
    """Handles container log streaming over WebSocket"""
    
    def __init__(
        self,
        websocket: WebSocket,
        user: User,
        db: AsyncSession,
        container_id: str
    ):
        super().__init__(
            websocket=websocket,
            user=user,
            db=db,
            resource_id=container_id,
            resource_type="container"
        )
        self.container_id = container_id
        self.docker_service = None
        self.stream_handler = DockerStreamHandler()
        self.self_monitoring = get_self_monitoring_service()
        self.lines_sent = 0
    
    async def on_connect(self) -> None:
        """Handle WebSocket connection"""
        await self.set_state(WebSocketState.CONNECTED)
        
        # Initialize Docker service
        self.docker_service = DockerServiceFactory.create(
            user=self.user,
            db=self.db,
            multi_host=True
        )
        
        await self.set_state(WebSocketState.AUTHENTICATED)
        await self.send_connected()
    
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages"""
        msg_type = message.get("type")
        
        if msg_type == "start":
            await self.start_log_stream(message.get("data", {}))
        elif msg_type == "stop":
            await self.stop_log_stream()
        elif msg_type == "ping":
            await self.send_message("pong", {})
        else:
            await self.send_error(f"Unknown message type: {msg_type}")
    
    async def start_log_stream(self, options: Dict[str, Any]) -> None:
        """Start streaming container logs"""
        async with self.error_handling("start_log_stream"):
            # Get options
            lines = options.get("lines", 100)
            follow = options.get("follow", True)
            timestamps = options.get("timestamps", False)
            host_id = options.get("host_id")
            
            # Get container
            try:
                container_data = await self.docker_service.get_container(
                    self.container_id,
                    host_id
                )
                container = container_data.container
                container_name = container.name
            except DockerOperationError as e:
                await self.send_error(f"Container not found: {str(e)}")
                return
            
            # Check if self-monitoring
            is_self_monitoring = self.self_monitoring.is_self_monitoring(container_name)
            if is_self_monitoring:
                logger.info(f"Self-monitoring container detected: {container_name}")
            
            await self.set_state(WebSocketState.STREAMING)
            self.lines_sent = 0
            
            # Define log callback
            async def on_log(log_line: str):
                # Filter self-monitoring messages
                if is_self_monitoring and self.self_monitoring.should_filter_message(
                    log_line,
                    container_name
                ):
                    return
                
                self.lines_sent += 1
                await self.send_message("log", {
                    "line": log_line,
                    "timestamp": timestamps,
                    "line_number": self.lines_sent
                })
            
            # Start streaming logs
            await self.stream_handler.process_log_stream(
                container=container,
                on_log=on_log,
                lines=lines,
                follow=follow,
                timestamps=timestamps
            )
            
            # Stream ended
            await self.send_message("stream_end", {
                "total_lines": self.lines_sent,
                "reason": "Stream ended"
            })
            await self.set_state(WebSocketState.AUTHENTICATED)
    
    async def stop_log_stream(self) -> None:
        """Stop streaming logs"""
        await self.stream_handler.stop_all_streams()
        await self.send_message("stream_stopped", {"lines_sent": self.lines_sent})
        await self.set_state(WebSocketState.AUTHENTICATED)
    
    async def on_disconnect(self) -> None:
        """Handle WebSocket disconnection"""
        await self.stream_handler.stop_all_streams()
        logger.info(
            f"Log stream ended for container {self.container_id}, "
            f"sent {self.lines_sent} lines"
        )


class ContainerStatsHandler(EnhancedWebSocketHandler):
    """Handles container stats streaming over WebSocket"""
    
    def __init__(
        self,
        websocket: WebSocket,
        user: User,
        db: AsyncSession,
        container_id: str
    ):
        super().__init__(
            websocket=websocket,
            user=user,
            db=db,
            resource_id=container_id,
            resource_type="container"
        )
        self.container_id = container_id
        self.docker_service = None
        self.stream_handler = DockerStreamHandler()
        self.stats_calculator = None
        self.updates_sent = 0
    
    async def on_connect(self) -> None:
        """Handle WebSocket connection"""
        await self.set_state(WebSocketState.CONNECTED)
        
        # Initialize services
        self.docker_service = DockerServiceFactory.create(
            user=self.user,
            db=self.db,
            multi_host=True
        )
        
        # Lazy import to avoid circular dependency
        from app.services.container_stats_calculator import get_stats_calculator
        self.stats_calculator = get_stats_calculator()
        
        await self.set_state(WebSocketState.AUTHENTICATED)
        await self.send_connected()
    
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages"""
        msg_type = message.get("type")
        
        if msg_type == "start":
            await self.start_stats_stream(message.get("data", {}))
        elif msg_type == "stop":
            await self.stop_stats_stream()
        elif msg_type == "ping":
            await self.send_message("pong", {})
        else:
            await self.send_error(f"Unknown message type: {msg_type}")
    
    async def start_stats_stream(self, options: Dict[str, Any]) -> None:
        """Start streaming container stats"""
        async with self.error_handling("start_stats_stream"):
            # Get options
            interval = options.get("interval", 1.0)
            host_id = options.get("host_id")
            
            # Get container
            try:
                container_data = await self.docker_service.get_container(
                    self.container_id,
                    host_id
                )
                container = container_data.container
            except DockerOperationError as e:
                await self.send_error(f"Container not found: {str(e)}")
                return
            
            await self.set_state(WebSocketState.STREAMING)
            self.updates_sent = 0
            
            # Define stats callback
            async def on_stats(raw_stats: dict):
                # Calculate stats
                stats = self.stats_calculator.calculate(raw_stats)
                
                self.updates_sent += 1
                await self.send_message("stats", {
                    "stats": stats.dict(),
                    "update_number": self.updates_sent,
                    "timestamp": raw_stats.get("read", "")
                })
            
            # Start streaming stats
            await self.stream_handler.process_stats_stream(
                container=container,
                on_stats=on_stats,
                stream=True
            )
            
            # Stream ended
            await self.send_message("stream_end", {
                "total_updates": self.updates_sent,
                "reason": "Stream ended"
            })
            await self.set_state(WebSocketState.AUTHENTICATED)
    
    async def stop_stats_stream(self) -> None:
        """Stop streaming stats"""
        await self.stream_handler.stop_all_streams()
        await self.send_message("stream_stopped", {"updates_sent": self.updates_sent})
        await self.set_state(WebSocketState.AUTHENTICATED)
    
    async def on_disconnect(self) -> None:
        """Handle WebSocket disconnection"""
        await self.stream_handler.stop_all_streams()
        logger.info(
            f"Stats stream ended for container {self.container_id}, "
            f"sent {self.updates_sent} updates"
        )


# WebSocket endpoint functions
async def container_logs_ws(
    websocket: WebSocket,
    container_id: str,
    current_user: User = Depends(get_current_user_ws),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for container logs"""
    handler = ContainerLogsHandler(websocket, current_user, db, container_id)
    
    try:
        await handler.connect()
        await handler.listen()
    except WebSocketDisconnect:
        pass
    finally:
        await handler.disconnect()


async def container_stats_ws(
    websocket: WebSocket,
    container_id: str,
    current_user: User = Depends(get_current_user_ws),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for container stats"""
    handler = ContainerStatsHandler(websocket, current_user, db, container_id)
    
    try:
        await handler.connect()
        await handler.listen()
    except WebSocketDisconnect:
        pass
    finally:
        await handler.disconnect()