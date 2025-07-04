from typing import Dict, Set, Optional
from fastapi import WebSocket
from collections import defaultdict
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""
    
    MAX_CONNECTIONS_PER_USER = 10
    MAX_CONNECTIONS_PER_CONTAINER = 50
    
    def __init__(self):
        # Active connections by container ID
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        # User info for each connection
        self.connection_users: Dict[WebSocket, str] = {}
        # Connection timestamps
        self.connection_times: Dict[WebSocket, datetime] = {}
        # User connection count
        self.user_connections: Dict[str, int] = defaultdict(int)
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, container_id: str, username: str) -> bool:
        """Accept and register a new WebSocket connection."""
        async with self.lock:
            # Check connection limits
            if self.user_connections[username] >= self.MAX_CONNECTIONS_PER_USER:
                await websocket.close(code=1008, reason="Too many connections for user")
                return False
            
            if len(self.active_connections[container_id]) >= self.MAX_CONNECTIONS_PER_CONTAINER:
                await websocket.close(code=1008, reason="Too many connections for container")
                return False
            
            await websocket.accept()
            self.active_connections[container_id].add(websocket)
            self.connection_users[websocket] = username
            self.connection_times[websocket] = datetime.utcnow()
            self.user_connections[username] += 1
            logger.info(f"WebSocket connected: {username} to container {container_id}")
            return True
    
    async def disconnect(self, websocket: WebSocket, container_id: str):
        """Remove a WebSocket connection."""
        async with self.lock:
            self.active_connections[container_id].discard(websocket)
            if not self.active_connections[container_id]:
                del self.active_connections[container_id]
            
            username = self.connection_users.pop(websocket, "unknown")
            self.connection_times.pop(websocket, None)
            
            # Decrement user connection count
            if username != "unknown" and username in self.user_connections:
                self.user_connections[username] -= 1
                if self.user_connections[username] <= 0:
                    del self.user_connections[username]
            
            logger.info(f"WebSocket disconnected: {username} from container {container_id}")
    
    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """Send message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {str(e)} - Message: {message}")
    
    async def broadcast_to_container(self, container_id: str, message: dict):
        """Broadcast message to all connections watching a container."""
        connections = self.active_connections.get(container_id, set()).copy()
        if connections:
            # Send to all connections in parallel
            tasks = [self.send_to_connection(ws, message) for ws in connections]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_connection_count(self, container_id: str) -> int:
        """Get number of active connections for a container."""
        return len(self.active_connections.get(container_id, set()))
    
    def get_all_connections(self) -> Dict[str, int]:
        """Get connection counts for all containers."""
        return {cid: len(conns) for cid, conns in self.active_connections.items()}


# Global connection manager instance
manager = ConnectionManager()