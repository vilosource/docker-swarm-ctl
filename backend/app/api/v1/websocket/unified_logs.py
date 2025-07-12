"""
Unified WebSocket handler for all log types.

This module provides a single, consistent WebSocket handler that can
stream logs from any source type (container, service, host, etc.).
"""

from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import asyncio

from app.db.session import get_db, AsyncSessionLocal
from app.services.logs import LogSourceType
from app.services.logs.router import get_log_router
from app.services.logs.stream_manager import get_stream_manager
from app.api.v1.websocket.containers import authenticate_websocket_user
from app.api.v1.websocket.auth import check_permission
from app.core.logging import logger
from app.models import User


class UnifiedLogWebSocketHandler:
    """
    Unified handler for all log streaming WebSocket connections.
    
    This handler:
    - Authenticates users
    - Validates permissions
    - Gets the appropriate log provider
    - Manages the WebSocket connection lifecycle
    - Uses the stream manager for efficient multi-client support
    """
    
    def __init__(self):
        """Initialize the handler."""
        self.router = get_log_router()
        self.stream_manager = get_stream_manager()
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        source_type: LogSourceType,
        resource_id: str,
        host_id: Optional[str] = None,
        tail: int = 100,
        follow: bool = True,
        timestamps: bool = True,
        token: Optional[str] = None
    ):
        """
        Handle a WebSocket connection for log streaming.
        
        Args:
            websocket: The WebSocket connection
            source_type: Type of log source
            resource_id: ID of the resource
            host_id: Optional host ID for multi-host resources
            tail: Number of lines to show from the end
            follow: Whether to follow log output
            timestamps: Whether to include timestamps
            token: Authentication token
        """
        db_session = None
        
        try:
            # Create a new session for the WebSocket connection
            db_session = AsyncSessionLocal()
            db = await db_session.__aenter__()
            
            # Authenticate user
            user, error = await authenticate_websocket_user(token, db)
            if not user:
                await websocket.accept()
                await websocket.close(code=1008, reason=error or "Authentication failed")
                return
            
            # Check permissions
            if not check_permission(user, "viewer"):
                await websocket.accept()
                await websocket.close(code=1008, reason="Insufficient permissions")
                return
            
            # Accept connection
            await websocket.accept()
            logger.info(f"WebSocket connected for {source_type}:{resource_id}")
            
            # Send initial connected message
            await websocket.send_json({
                "type": "connected",
                "message": f"Connected to {source_type} logs for {resource_id}",
                "source_type": source_type,
                "resource_id": resource_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Get log provider
            try:
                # For now, create a new provider instance for each connection
                # to avoid issues with singleton providers in multi-host mode
                if source_type == LogSourceType.CONTAINER:
                    from app.services.logs.providers.container_logs import ContainerLogSource
                    from app.services.docker_connection_manager import get_docker_connection_manager
                    provider = ContainerLogSource(connection_manager=get_docker_connection_manager())
                elif source_type == LogSourceType.SERVICE:
                    from app.services.logs.providers.service_logs import ServiceLogSource
                    from app.services.docker_connection_manager import get_docker_connection_manager
                    provider = ServiceLogSource(connection_manager=get_docker_connection_manager())
                else:
                    provider = self.router.get_provider(source_type)
            except ValueError as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                await websocket.close(code=1011)
                return
            
            # Validate access
            if not await provider.validate_access(resource_id, user):
                await websocket.send_json({
                    "type": "error",
                    "message": "Access denied to this resource",
                    "timestamp": datetime.utcnow().isoformat()
                })
                await websocket.close(code=1008)
                return
            
            # Get the stream key
            stream_key = self.stream_manager._get_stream_key(source_type, resource_id)
            
            # Check if this is the first connection for this stream
            is_first_connection = stream_key not in self.stream_manager.streams
            
            # Connect to stream manager
            connected = await self.stream_manager.connect(
                websocket=websocket,
                source_type=source_type,
                resource_id=resource_id,
                provider=provider,
                tail=tail
            )
            
            if not connected:
                await websocket.close(code=1011, reason="Failed to connect to log stream")
                return
            
            if is_first_connection:
                # This is the first connection, start streaming
                logger.info(f"Starting log stream for {source_type}:{resource_id}")
                
                # Create a task to stream logs
                async def stream_logs():
                    try:
                        async for log_entry in provider.get_logs(
                            resource_id=resource_id,
                            follow=follow,
                            tail=tail,
                            timestamps=timestamps,
                            host_id=host_id,
                            user=user,
                            db=db
                        ):
                            # Broadcast to all connections via stream manager
                            await self.stream_manager.broadcast(
                                source_type=source_type,
                                resource_id=resource_id,
                                entry=log_entry
                            )
                        
                        # Send completion message if not following
                        if not follow:
                            for ws in self.stream_manager.streams[stream_key].connections:
                                try:
                                    await ws.send_json({
                                        "type": "complete",
                                        "message": "Log stream completed",
                                        "source_type": source_type,
                                        "resource_id": resource_id,
                                        "timestamp": datetime.utcnow().isoformat()
                                    })
                                except:
                                    pass
                    
                    except Exception as e:
                        logger.error(f"Error streaming logs for {source_type}:{resource_id}: {e}", exc_info=True)
                        # Send error to all connections
                        if stream_key in self.stream_manager.streams:
                            for ws in self.stream_manager.streams[stream_key].connections:
                                try:
                                    await ws.send_json({
                                        "type": "error",
                                        "message": f"Error streaming logs: {str(e)}",
                                        "error_type": type(e).__name__,
                                        "timestamp": datetime.utcnow().isoformat()
                                    })
                                except:
                                    pass
                
                # Start the streaming task
                stream = self.stream_manager.streams[stream_key]
                stream.task = asyncio.create_task(stream_logs())
            else:
                # Additional connection - just wait for broadcasts
                logger.info(f"Connected as additional client to {source_type}:{resource_id}")
            
            # Keep connection alive
            while websocket.client_state.value == 1:  # CONNECTED
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except:
                    break
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for {source_type}:{resource_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {source_type}:{resource_id}: {e}", exc_info=True)
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except:
                pass
        finally:
            # Disconnect from stream manager
            await self.stream_manager.disconnect(websocket, source_type, resource_id)
            
            # Cleanup session
            if db_session:
                await db_session.__aexit__(None, None, None)
            
            logger.info(f"WebSocket handler cleanup complete for {source_type}:{resource_id}")


# Global handler instance
_handler: Optional[UnifiedLogWebSocketHandler] = None


def get_unified_log_handler() -> UnifiedLogWebSocketHandler:
    """Get the global unified log handler instance."""
    global _handler
    if _handler is None:
        _handler = UnifiedLogWebSocketHandler()
    return _handler


# Convenience function for routes
async def handle_log_websocket(
    websocket: WebSocket,
    source_type: LogSourceType,
    resource_id: str,
    host_id: Optional[str] = None,
    tail: int = Query(100, description="Number of lines to show from the end"),
    follow: bool = Query(True, description="Follow log output"),
    timestamps: bool = Query(True, description="Add timestamps"),
    token: Optional[str] = Query(None, description="Authentication token")
):
    """
    Convenience function for handling log WebSocket connections.
    
    This can be used directly in FastAPI routes.
    """
    handler = get_unified_log_handler()
    await handler.handle_connection(
        websocket=websocket,
        source_type=source_type,
        resource_id=resource_id,
        host_id=host_id,
        tail=tail,
        follow=follow,
        timestamps=timestamps,
        token=token
    )