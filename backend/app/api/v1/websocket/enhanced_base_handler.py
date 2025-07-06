"""
Enhanced Base WebSocket Handler

Extends the base handler with resource management, state handling,
and common patterns for Docker operations.
"""

import asyncio
from typing import Optional, Dict, Any, List, Set, Callable
from contextlib import asynccontextmanager
from enum import Enum
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.websocket.base_handler import BaseWebSocketHandler
from app.models import User
from app.core.logging import logger


class WebSocketState(Enum):
    """WebSocket connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    STREAMING = "streaming"
    CLOSING = "closing"
    CLOSED = "closed"


class ResourceType(Enum):
    """Types of resources that can be managed"""
    DOCKER_STREAM = "docker_stream"
    ASYNC_TASK = "async_task"
    LOCK = "lock"
    TIMER = "timer"


class ManagedResource:
    """Represents a managed resource"""
    
    def __init__(
        self,
        resource_type: ResourceType,
        resource: Any,
        cleanup_callback: Optional[Callable] = None
    ):
        self.type = resource_type
        self.resource = resource
        self.cleanup_callback = cleanup_callback
        self.created_at = datetime.utcnow()
    
    async def cleanup(self):
        """Clean up the resource"""
        try:
            if self.cleanup_callback:
                await self.cleanup_callback(self.resource)
            elif hasattr(self.resource, 'close'):
                self.resource.close()
            elif hasattr(self.resource, 'cancel'):
                self.resource.cancel()
                try:
                    await self.resource
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.error(f"Error cleaning up {self.type.value} resource: {e}")


class EnhancedWebSocketHandler(BaseWebSocketHandler):
    """
    Enhanced base handler with resource management and state handling
    
    Provides:
    - Automatic resource cleanup
    - State machine for connection lifecycle
    - Structured error handling
    - Performance monitoring
    """
    
    def __init__(
        self,
        websocket: WebSocket,
        user: User,
        db: AsyncSession,
        resource_id: str,
        resource_type: str
    ):
        super().__init__()  # BaseWebSocketHandler has no args
        self.websocket = websocket
        self.user = user
        self.db = db
        self.resource_id = resource_id
        self.resource_type = resource_type
        self._state = WebSocketState.CONNECTING
        self._resources: List[ManagedResource] = []
        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "connected_at": datetime.utcnow()
        }
        self._state_lock = asyncio.Lock()
    
    @property
    def state(self) -> WebSocketState:
        """Get current connection state"""
        return self._state
    
    async def set_state(self, new_state: WebSocketState) -> None:
        """
        Set connection state with validation
        
        Args:
            new_state: New state to transition to
        """
        async with self._state_lock:
            # Validate state transition
            if not self._is_valid_transition(self._state, new_state):
                raise ValueError(
                    f"Invalid state transition from {self._state.value} to {new_state.value}"
                )
            
            old_state = self._state
            self._state = new_state
            logger.debug(
                f"WebSocket state transition: {old_state.value} -> {new_state.value} "
                f"for {self.resource_type} {self.resource_id}"
            )
    
    def _is_valid_transition(
        self,
        from_state: WebSocketState,
        to_state: WebSocketState
    ) -> bool:
        """Check if state transition is valid"""
        valid_transitions = {
            WebSocketState.CONNECTING: [
                WebSocketState.CONNECTED,
                WebSocketState.CLOSED
            ],
            WebSocketState.CONNECTED: [
                WebSocketState.AUTHENTICATED,
                WebSocketState.CLOSING,
                WebSocketState.CLOSED
            ],
            WebSocketState.AUTHENTICATED: [
                WebSocketState.STREAMING,
                WebSocketState.CLOSING,
                WebSocketState.CLOSED
            ],
            WebSocketState.STREAMING: [
                WebSocketState.AUTHENTICATED,
                WebSocketState.CLOSING,
                WebSocketState.CLOSED
            ],
            WebSocketState.CLOSING: [WebSocketState.CLOSED],
            WebSocketState.CLOSED: []  # Terminal state
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    @asynccontextmanager
    async def managed_resources(self):
        """
        Context manager for automatic resource cleanup
        
        Yields:
            List of managed resources
        """
        resources = []
        try:
            yield resources
        finally:
            # Cleanup all resources in reverse order
            for resource in reversed(self._resources):
                await resource.cleanup()
            self._resources.clear()
    
    def add_resource(
        self,
        resource_type: ResourceType,
        resource: Any,
        cleanup_callback: Optional[Callable] = None
    ) -> None:
        """
        Add a resource to be managed
        
        Args:
            resource_type: Type of resource
            resource: The resource object
            cleanup_callback: Optional cleanup callback
        """
        managed = ManagedResource(resource_type, resource, cleanup_callback)
        self._resources.append(managed)
        logger.debug(f"Added managed resource: {resource_type.value}")
    
    async def remove_resource(self, resource: Any) -> None:
        """
        Remove and cleanup a specific resource
        
        Args:
            resource: Resource to remove
        """
        for managed in self._resources[:]:
            if managed.resource == resource:
                await managed.cleanup()
                self._resources.remove(managed)
                break
    
    @asynccontextmanager
    async def error_handling(self, operation: str):
        """
        Context manager for consistent error handling
        
        Args:
            operation: Name of the operation
        """
        try:
            yield
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected during {operation}")
            raise
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Error in {operation}: {e}")
            await self.send_error(f"Error in {operation}: {str(e)}")
            raise
    
    async def send_message(
        self,
        message_type: str,
        data: Any,
        **kwargs
    ) -> None:
        """
        Send a message with metrics tracking
        
        Args:
            message_type: Type of message
            data: Message data
            **kwargs: Additional message fields
        """
        await super().send_message(message_type, data, **kwargs)
        self._metrics["messages_sent"] += 1
    
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming message with metrics tracking
        
        Args:
            message: Received message
        """
        self._metrics["messages_received"] += 1
        await super().handle_message(message)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection metrics"""
        return {
            **self._metrics,
            "duration": (datetime.utcnow() - self._metrics["connected_at"]).total_seconds(),
            "state": self._state.value,
            "active_resources": len(self._resources)
        }
    
    async def health_check(self) -> bool:
        """
        Perform health check on the connection
        
        Returns:
            True if healthy, False otherwise
        """
        if self._state not in [
            WebSocketState.AUTHENTICATED,
            WebSocketState.STREAMING
        ]:
            return False
        
        try:
            # Send ping to check connection
            await self.websocket.send_json({"type": "ping"})
            return True
        except Exception:
            return False
    
    async def graceful_shutdown(self, reason: str = "Shutdown requested") -> None:
        """
        Perform graceful shutdown
        
        Args:
            reason: Reason for shutdown
        """
        try:
            await self.set_state(WebSocketState.CLOSING)
            
            # Send shutdown notification
            await self.send_message("shutdown", {"reason": reason})
            
            # Cleanup resources
            for resource in reversed(self._resources):
                await resource.cleanup()
            
            # Close WebSocket
            await self.websocket.close()
            
        finally:
            await self.set_state(WebSocketState.CLOSED)
    
    async def run_with_recovery(
        self,
        operation: Callable,
        max_retries: int = 3,
        backoff: float = 1.0
    ) -> Any:
        """
        Run an operation with automatic retry and recovery
        
        Args:
            operation: Async operation to run
            max_retries: Maximum retry attempts
            backoff: Backoff multiplier between retries
            
        Returns:
            Operation result
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff * (2 ** attempt)
                    logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Operation failed after {max_retries} attempts: {e}")
        
        raise last_error
    
    # Methods to make it compatible with base handler's template pattern
    async def send_message(self, message_type: str, data: Any, **kwargs) -> None:
        """Send a message to the WebSocket client"""
        message = {
            "type": message_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        await self.websocket.send_json(message)
        self._metrics["messages_sent"] += 1
    
    async def send_error(self, message: str) -> None:
        """Send an error message to the client"""
        await self.send_message("error", {"message": message})
    
    async def send_connected(self) -> None:
        """Send connection confirmation"""
        await self.send_message("connected", {
            "user": self.user.username,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type
        })
    
    # These need to be implemented by subclasses to work with base handler
    async def on_connect(self) -> None:
        """Handle connection initialization - override in subclass"""
        pass
    
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket message - override in subclass"""
        self._metrics["messages_received"] += 1
    
    async def on_disconnect(self) -> None:
        """Handle disconnection cleanup - override in subclass"""
        pass
    
    # WebSocket lifecycle methods
    async def connect(self) -> None:
        """Accept WebSocket connection and initialize"""
        await self.websocket.accept()
        await self.on_connect()
    
    async def listen(self) -> None:
        """Listen for incoming messages"""
        try:
            while True:
                message = await self.websocket.receive_json()
                await self.handle_message(message)
        except WebSocketDisconnect:
            pass
    
    async def disconnect(self) -> None:
        """Clean up and close connection"""
        await self.on_disconnect()
        await self.graceful_shutdown("Connection closed")