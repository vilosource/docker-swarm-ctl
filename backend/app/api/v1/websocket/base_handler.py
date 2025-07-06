"""
Base WebSocket Handler

Provides common functionality for WebSocket endpoints using the Template Method pattern.
Reduces code duplication and complexity in WebSocket handlers.
"""

from typing import Optional, Dict, Any, Callable, TypeVar, Generic
from abc import ABC, abstractmethod
from fastapi import WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json
from datetime import datetime

from app.api.v1.websocket.auth import get_current_user_ws, check_permission
from app.api.v1.websocket.base import manager
from app.services.docker_client import DockerClientFactory
from app.services.docker_connection_manager import get_docker_connection_manager
from app.services.self_monitoring_detector import is_self_monitoring
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.logging import logger
from app.core.feature_flags import FeatureFlag, is_feature_enabled


T = TypeVar('T')


class WebSocketContext:
    """Context object containing WebSocket connection information"""
    
    def __init__(
        self,
        websocket: WebSocket,
        user: User,
        docker_client: Any,
        container_id: Optional[str] = None,
        host_id: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        is_self_monitoring: bool = False
    ):
        self.websocket = websocket
        self.user = user
        self.docker_client = docker_client
        self.container_id = container_id
        self.host_id = host_id
        self.db_session = db_session
        self.is_self_monitoring = is_self_monitoring
        self.connection_id = f"{user.username}:{container_id or 'system'}"


class BaseWebSocketHandler(ABC, Generic[T]):
    """
    Base class for WebSocket handlers implementing Template Method pattern
    
    Subclasses should implement:
    - get_required_permission() - Return required permission level
    - handle_connection() - Main connection handling logic
    - on_error() - Error handling (optional)
    - on_disconnect() - Cleanup logic (optional)
    """
    
    def __init__(self):
        self.logger = logger
    
    @abstractmethod
    def get_required_permission(self) -> str:
        """Get required permission level for this handler"""
        pass
    
    @abstractmethod
    async def handle_connection(self, context: WebSocketContext) -> None:
        """Handle the WebSocket connection - main logic goes here"""
        pass
    
    async def on_connect(self, context: WebSocketContext) -> bool:
        """Called when connection is established. Return False to reject."""
        return True
    
    async def on_error(self, context: WebSocketContext, error: Exception) -> None:
        """Handle errors during connection"""
        self.logger.error(f"WebSocket error for {context.connection_id}: {error}")
        try:
            await context.websocket.send_json({
                "type": "error",
                "message": str(error),
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass
    
    async def on_disconnect(self, context: WebSocketContext) -> None:
        """Called when connection is closing"""
        if not context.is_self_monitoring:
            self.logger.info(f"WebSocket disconnected for {context.connection_id}")
    
    async def authenticate(
        self,
        websocket: WebSocket,
        token: Optional[str]
    ) -> Optional[User]:
        """Authenticate the WebSocket connection"""
        user = await get_current_user_ws(websocket, token)
        if not user:
            return None
        
        # Check required permission
        required_permission = self.get_required_permission()
        if not check_permission(user, required_permission):
            await websocket.close(code=1008, reason="Insufficient permissions")
            return None
        
        return user
    
    async def get_docker_client(
        self,
        host_id: Optional[str],
        user: User
    ) -> tuple[Any, Optional[AsyncSession]]:
        """Get Docker client for the specified host"""
        db_session = None
        
        if host_id:
            # Multi-host deployment
            db_session = AsyncSessionLocal()
            db = await db_session.__aenter__()
            connection_manager = get_docker_connection_manager()
            
            try:
                docker_client = await connection_manager.get_client(host_id, user, db)
            except Exception as e:
                if db_session:
                    await db_session.__aexit__(None, None, None)
                raise Exception(f"Failed to connect to host: {str(e)}")
        else:
            # Local Docker
            docker_client = DockerClientFactory.get_client()
        
        return docker_client, db_session
    
    async def __call__(
        self,
        websocket: WebSocket,
        container_id: Optional[str] = None,
        token: Optional[str] = None,
        host_id: Optional[str] = None,
        **kwargs
    ):
        """
        Main entry point for WebSocket handler
        
        This method implements the Template Method pattern:
        1. Authenticate user
        2. Get Docker client
        3. Check self-monitoring  - A hack to not recursively send logs that create more logs!!
        4. Accept connection
        5. Call handle_connection (implemented by subclass)
        6. Handle errors and cleanup
        """
        # Skip if feature flag is disabled
        if not is_feature_enabled(FeatureFlag.USE_NEW_WEBSOCKET_HANDLER):
            # Fall back to original implementation
            return await self._legacy_handler(websocket, container_id, token, host_id, **kwargs)
        
        db_session = None
        context = None
        
        try:
            # Authenticate
            user = await self.authenticate(websocket, token)
            if not user:
                return
            
            # Get Docker client
            docker_client, db_session = await self.get_docker_client(host_id, user)
            
            # Check self-monitoring if container_id provided
            self_monitoring = False
            """This fixes the problem where if we access the container that is running this 
               code, then we end up getting logs for this container, which creates more logs
               to be sent , and creates a recursive loop. We simply avoid sending logs to the 
               frontend in this corner case"""

            if container_id and docker_client:
                self_monitoring = is_self_monitoring(container_id, docker_client)
            
            # Create context
            context = WebSocketContext(
                websocket=websocket,
                user=user,
                docker_client=docker_client,
                container_id=container_id,
                host_id=host_id,
                db_session=db_session,
                is_self_monitoring=self_monitoring
            )
            
            # Accept connection
            await websocket.accept()
            
            # Call on_connect hook
            if not await self.on_connect(context):
                await websocket.close(code=1000, reason="Connection rejected")
                return
            
            # Handle self-monitoring case
            if self_monitoring and container_id:
                await self._handle_self_monitoring(context)
                return
            
            # Main connection handling
            await self.handle_connection(context)
            
        except WebSocketDisconnect:
            if context:
                await self.on_disconnect(context)
        except Exception as e:
            if context:
                await self.on_error(context, e)
            else:
                self.logger.error(f"WebSocket error before context creation: {e}")
        finally:
            # Cleanup
            if db_session:
                await db_session.__aexit__(None, None, None)
    
    async def _handle_self_monitoring(self, context: WebSocketContext) -> None:
        """Handle self-monitoring scenario"""
        await context.websocket.send_json({
            "type": "info",
            "message": "Operation disabled for backend container to prevent feedback loops",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive but don't send any data
        try:
            while True:
                await asyncio.sleep(30)
                await context.websocket.send_json({"type": "ping"})
        except WebSocketDisconnect:
            pass
    
    async def _legacy_handler(
        self,
        websocket: WebSocket,
        container_id: Optional[str],
        token: Optional[str],
        host_id: Optional[str],
        **kwargs
    ):
        """Fallback to legacy implementation - to be overridden by subclasses"""
        raise NotImplementedError("Legacy handler not implemented")


class ConnectionManager:
    """Enhanced connection manager for WebSocket connections"""
    
    def __init__(self):
        self._connections: Dict[str, Dict[str, WebSocket]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
    
    async def register(
        self,
        resource_id: str,
        connection_id: str,
        websocket: WebSocket
    ) -> bool:
        """Register a new connection"""
        if resource_id not in self._locks:
            self._locks[resource_id] = asyncio.Lock()
        
        async with self._locks[resource_id]:
            if resource_id not in self._connections:
                self._connections[resource_id] = {}
            
            self._connections[resource_id][connection_id] = websocket
            return True
    
    async def unregister(
        self,
        resource_id: str,
        connection_id: str
    ) -> None:
        """Unregister a connection"""
        if resource_id in self._connections:
            self._connections[resource_id].pop(connection_id, None)
            if not self._connections[resource_id]:
                del self._connections[resource_id]
    
    async def broadcast(
        self,
        resource_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Broadcast message to all connections for a resource"""
        if resource_id in self._connections:
            disconnected = []
            
            for conn_id, websocket in self._connections[resource_id].items():
                try:
                    await websocket.send_json(message)
                except:
                    disconnected.append(conn_id)
            
            # Clean up disconnected connections
            for conn_id in disconnected:
                await self.unregister(resource_id, conn_id)
    
    def get_connection_count(self, resource_id: str) -> int:
        """Get number of active connections for a resource"""
        return len(self._connections.get(resource_id, {}))
