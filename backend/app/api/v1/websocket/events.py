"""
Docker Events WebSocket endpoint

Streams real-time Docker events to connected clients with filtering support.
"""

from typing import Optional, Dict, Any, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from datetime import datetime
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.logging import logger
from app.models.user import User
from app.api.v1.websocket.auth import get_current_user_ws
from app.api.v1.websocket.base import ConnectionManager
from app.services.docker_service import DockerServiceFactory


router = APIRouter()

# Connection manager for event subscribers
event_manager = ConnectionManager()

# Thread pool for blocking Docker operations
executor = ThreadPoolExecutor(max_workers=2)


class EventFilter:
    """Filter Docker events based on criteria"""
    
    def __init__(self, filters: Optional[Dict[str, Any]] = None):
        self.filters = filters or {}
        self.types = self.filters.get("type", [])
        self.actions = self.filters.get("action", [])
        self.labels = self.filters.get("label", {})
        self.containers = self.filters.get("container", [])
        self.images = self.filters.get("image", [])
        
    def matches(self, event: Dict[str, Any]) -> bool:
        """Check if event matches filter criteria"""
        # Type filter
        if self.types and event.get("Type") not in self.types:
            return False
            
        # Action filter
        if self.actions and event.get("Action") not in self.actions:
            return False
            
        # Container filter
        if self.containers:
            actor_id = event.get("Actor", {}).get("ID", "")
            actor_name = event.get("Actor", {}).get("Attributes", {}).get("name", "")
            if actor_id not in self.containers and actor_name not in self.containers:
                return False
                
        # Image filter
        if self.images:
            image = event.get("Actor", {}).get("Attributes", {}).get("image", "")
            if image not in self.images:
                return False
                
        # Label filter
        if self.labels:
            event_labels = event.get("Actor", {}).get("Attributes", {})
            for key, value in self.labels.items():
                if event_labels.get(key) != value:
                    return False
                    
        return True


class EventBroadcaster:
    """Manages event streaming from Docker to multiple WebSocket clients"""
    
    def __init__(self):
        self.subscribers: Dict[str, Set[WebSocket]] = {}  # host_id -> websockets
        self.tasks: Dict[str, asyncio.Task] = {}  # host_id -> stream task
        self.filters: Dict[WebSocket, EventFilter] = {}  # websocket -> filter
        
    async def subscribe(self, websocket: WebSocket, host_id: str, event_filter: EventFilter):
        """Subscribe a WebSocket to events from a specific host"""
        if host_id not in self.subscribers:
            self.subscribers[host_id] = set()
            
        self.subscribers[host_id].add(websocket)
        self.filters[websocket] = event_filter
        
        # Start event streaming for this host if not already running
        if host_id not in self.tasks or self.tasks[host_id].done():
            self.tasks[host_id] = asyncio.create_task(self._stream_events(host_id))
            
    async def unsubscribe(self, websocket: WebSocket):
        """Unsubscribe a WebSocket from all events"""
        # Remove from all host subscriptions
        for host_id, sockets in self.subscribers.items():
            sockets.discard(websocket)
            
        # Remove filter
        self.filters.pop(websocket, None)
        
        # Stop streaming for hosts with no subscribers
        empty_hosts = [host_id for host_id, sockets in self.subscribers.items() if not sockets]
        for host_id in empty_hosts:
            del self.subscribers[host_id]
            if host_id in self.tasks:
                self.tasks[host_id].cancel()
                del self.tasks[host_id]
                
    async def _stream_events(self, host_id: str):
        """Stream events from a Docker host to subscribers"""
        logger.info(f"Starting event stream for host {host_id}")
        
        try:
            # Get Docker service for this host
            docker_service = DockerServiceFactory.create(None, None, multi_host=True)
            
            # Get Docker client for specific host
            if host_id == "all":
                # Stream from all hosts
                hosts = await docker_service.list_hosts()
                for host in hosts:
                    asyncio.create_task(self._stream_host_events(host.id, docker_service))
            else:
                await self._stream_host_events(host_id, docker_service)
                
        except Exception as e:
            logger.error(f"Error in event stream for host {host_id}: {str(e)}")
            await self._broadcast_error(host_id, str(e))
            
    async def _stream_host_events(self, host_id: str, docker_service):
        """Stream events from a specific host"""
        try:
            # Get the Docker client for this host
            client = await asyncio.get_event_loop().run_in_executor(
                executor,
                docker_service._get_client,
                host_id
            )
            
            # Start streaming events
            events = await asyncio.get_event_loop().run_in_executor(
                executor,
                client.events,
                True,  # decode
                None,  # since
                None,  # until
                None   # filters
            )
            
            # Process each event
            async for event in self._async_event_generator(events):
                # Add host information to event
                event["host_id"] = host_id
                
                # Broadcast to subscribers
                await self._broadcast_event(host_id, event)
                
        except Exception as e:
            logger.error(f"Error streaming events from host {host_id}: {str(e)}")
            
    async def _async_event_generator(self, events):
        """Convert blocking event generator to async"""
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                event = await loop.run_in_executor(executor, next, events)
                if isinstance(event, bytes):
                    event = json.loads(event.decode('utf-8'))
                elif isinstance(event, str):
                    event = json.loads(event)
                yield event
            except StopIteration:
                break
            except Exception as e:
                logger.error(f"Error processing event: {str(e)}")
                continue
                
    async def _broadcast_event(self, host_id: str, event: Dict[str, Any]):
        """Broadcast event to all subscribers"""
        if host_id not in self.subscribers:
            return
            
        # Format event with timestamp
        formatted_event = {
            "type": "event",
            "timestamp": datetime.utcnow().isoformat(),
            "host_id": host_id,
            "event": event
        }
        
        # Send to each subscriber that matches the filter
        disconnected = []
        for websocket in self.subscribers[host_id]:
            try:
                # Check if event matches subscriber's filter
                event_filter = self.filters.get(websocket)
                if event_filter and not event_filter.matches(event):
                    continue
                    
                await websocket.send_json(formatted_event)
            except Exception as e:
                logger.error(f"Error sending event to client: {str(e)}")
                disconnected.append(websocket)
                
        # Clean up disconnected clients
        for ws in disconnected:
            await self.unsubscribe(ws)
            
    async def _broadcast_error(self, host_id: str, error: str):
        """Broadcast error to all subscribers"""
        if host_id not in self.subscribers:
            return
            
        error_msg = {
            "type": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "host_id": host_id,
            "error": error
        }
        
        disconnected = []
        for websocket in self.subscribers[host_id]:
            try:
                await websocket.send_json(error_msg)
            except:
                disconnected.append(websocket)
                
        for ws in disconnected:
            await self.unsubscribe(ws)


# Global event broadcaster
event_broadcaster = EventBroadcaster()


@router.websocket("/events")
async def docker_events(
    websocket: WebSocket,
    host_id: Optional[str] = Query("all", description="Docker host ID or 'all' for all hosts"),
    filters: Optional[str] = Query(None, description="JSON encoded event filters"),
    token: Optional[str] = Query(None)
):
    """
    Stream Docker events via WebSocket
    
    Filters format:
    {
        "type": ["container", "image", "network", "volume"],
        "action": ["create", "start", "stop", "destroy"],
        "label": {"key": "value"},
        "container": ["container_id_or_name"],
        "image": ["image_name"]
    }
    """
    await event_manager.connect(websocket)
    
    # Authenticate user
    current_user = await get_current_user_ws(websocket, token)
    if not current_user:
        return
    
    try:
        # Parse filters
        event_filter = EventFilter()
        if filters:
            try:
                filter_dict = json.loads(filters)
                event_filter = EventFilter(filter_dict)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid filter JSON"
                })
                return
                
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "host_id": host_id,
            "filters": filters
        })
        
        # Subscribe to events
        await event_broadcaster.subscribe(websocket, host_id, event_filter)
        
        # Keep connection alive
        try:
            while True:
                # Wait for client messages (ping/pong)
                data = await websocket.receive_json()
                
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
        except WebSocketDisconnect:
            pass
            
    finally:
        # Clean up
        await event_broadcaster.unsubscribe(websocket)
        event_manager.disconnect(websocket)
        logger.info(f"Client disconnected from events stream")