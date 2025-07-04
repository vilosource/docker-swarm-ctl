# Scaling WebSocket Applications with Multiple Backend Instances

## Overview

Scaling WebSocket applications presents unique challenges compared to traditional HTTP APIs. This guide explains how to scale the Docker Control Platform's WebSocket features across multiple backend instances in production.

## 1. Challenges with WebSockets and Multiple Instances

### 1.1 Connection State
- **Stateful Nature**: Unlike HTTP requests, WebSocket connections are long-lived and stateful
- **Client Affinity**: Clients establish connections to specific backend instances
- **Connection Migration**: Moving connections between instances is complex and disruptive

### 1.2 Message Routing
- **Cross-Instance Communication**: Messages may need to reach clients connected to different backend instances
- **Broadcast Challenges**: Sending messages to all connected clients requires coordination
- **Event Synchronization**: Docker events must reach all relevant clients regardless of their connection point

### 1.3 Load Balancing
- **Sticky Sessions**: Traditional round-robin doesn't work well with WebSockets
- **Connection Distribution**: Uneven distribution can occur with long-lived connections
- **Failover Complexity**: Handling instance failures requires reconnection strategies

## 2. Common Architectural Patterns for Scaling WebSockets

### 2.1 Pub/Sub Pattern with Message Broker
```
┌─────────┐     ┌─────────┐     ┌─────────┐
│Client 1 │     │Client 2 │     │Client 3 │
└────┬────┘     └────┬────┘     └────┬────┘
     │               │               │
     │WebSocket      │WebSocket      │WebSocket
     │               │               │
┌────▼────┐     ┌────▼────┐     ┌────▼────┐
│Backend 1│     │Backend 2│     │Backend 3│
└────┬────┘     └────┬────┘     └────┬────┘
     │               │               │
     └───────────────┴───────────────┘
                     │
              ┌──────▼──────┐
              │Redis Pub/Sub│
              └─────────────┘
```

### 2.2 Session Store Pattern
- Store WebSocket session metadata in shared storage (Redis)
- Enable cross-instance message routing
- Support connection recovery after failures

### 2.3 Event Bus Architecture
- Centralized event distribution
- Decoupled message producers and consumers
- Supports multiple transport mechanisms

## 3. Specific Implementation for Docker Control Platform

### 3.1 Redis Pub/Sub Integration

**Backend WebSocket Manager with Redis:**
```python
# app/websocket/manager.py
import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
import redis.asyncio as redis
from app.core.config import settings

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.redis_client = None
        self.pubsub = None
        self.listener_task = None
        
    async def startup(self):
        """Initialize Redis connection and start listening"""
        self.redis_client = await redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe("websocket:broadcast")
        self.listener_task = asyncio.create_task(self._listen_redis())
    
    async def shutdown(self):
        """Cleanup connections"""
        if self.listener_task:
            self.listener_task.cancel()
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
    
    async def _listen_redis(self):
        """Listen for Redis pub/sub messages"""
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await self._handle_redis_message(data)
    
    async def _handle_redis_message(self, data: dict):
        """Route messages from Redis to appropriate WebSocket connections"""
        channel = data.get("channel")
        payload = data.get("payload")
        
        if channel in self.active_connections:
            # Send to all connections on this channel
            for websocket in self.active_connections[channel]:
                try:
                    await websocket.send_json(payload)
                except Exception:
                    # Connection might be closed
                    await self.disconnect(websocket, channel)
    
    async def connect(self, websocket: WebSocket, channel: str):
        """Accept WebSocket connection and register it"""
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        
        self.active_connections[channel].add(websocket)
        
        # Store connection info in Redis for monitoring
        connection_key = f"ws:connection:{channel}:{id(websocket)}"
        await self.redis_client.setex(
            connection_key,
            300,  # 5 minute TTL
            json.dumps({
                "instance_id": settings.INSTANCE_ID,
                "channel": channel,
                "connected_at": asyncio.get_event_loop().time()
            })
        )
    
    async def disconnect(self, websocket: WebSocket, channel: str):
        """Remove WebSocket connection"""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]
        
        # Remove from Redis
        connection_key = f"ws:connection:{channel}:{id(websocket)}"
        await self.redis_client.delete(connection_key)
    
    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast message to all instances via Redis"""
        await self.redis_client.publish(
            "websocket:broadcast",
            json.dumps({
                "channel": channel,
                "payload": message
            })
        )
    
    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """Send message directly to a specific connection"""
        await websocket.send_json(message)

# Global manager instance
manager = WebSocketManager()
```

### 3.2 Container Logs Streaming with Scaling

**Scalable Container Logs Endpoint:**
```python
# app/api/websocket/containers.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket.manager import manager
from app.services.docker_service import DockerService
from app.core.auth import get_current_user_ws
import asyncio
import json

router = APIRouter()

@router.websocket("/ws/containers/{container_id}/logs")
async def container_logs(
    websocket: WebSocket,
    container_id: str,
    user = Depends(get_current_user_ws)
):
    channel = f"container:logs:{container_id}"
    await manager.connect(websocket, channel)
    
    try:
        # Check if another instance is already streaming these logs
        stream_lock_key = f"stream:lock:{channel}"
        lock_acquired = await manager.redis_client.set(
            stream_lock_key,
            settings.INSTANCE_ID,
            nx=True,  # Only set if not exists
            ex=60     # 60 second TTL
        )
        
        if lock_acquired:
            # This instance will stream the logs
            await _stream_container_logs(container_id, channel)
        else:
            # Another instance is streaming, just relay messages
            while True:
                await asyncio.sleep(30)
                # Heartbeat to keep connection alive
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    finally:
        # Release lock if we held it
        if lock_acquired:
            await manager.redis_client.delete(stream_lock_key)

async def _stream_container_logs(container_id: str, channel: str):
    """Stream logs and broadcast to all instances"""
    docker_service = DockerService()
    container = docker_service.get_container(container_id)
    
    # Renew lock periodically
    async def renew_lock():
        while True:
            await asyncio.sleep(30)
            await manager.redis_client.expire(f"stream:lock:{channel}", 60)
    
    renew_task = asyncio.create_task(renew_lock())
    
    try:
        async for log in container.logs(stream=True, follow=True):
            message = {
                "type": "log",
                "data": log.decode('utf-8').strip()
            }
            # Broadcast to all instances
            await manager.broadcast_to_channel(channel, message)
    finally:
        renew_task.cancel()
```

### 3.3 Docker Events Distribution

**Centralized Docker Events Handler:**
```python
# app/services/docker_events.py
import asyncio
import json
from app.websocket.manager import manager
from app.services.docker_service import DockerService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DockerEventHandler:
    def __init__(self):
        self.docker_service = DockerService()
        self.running = False
        self.task = None
    
    async def start(self):
        """Start monitoring Docker events"""
        # Use Redis to ensure only one instance monitors events
        lock_key = "docker:events:monitor"
        
        while True:
            lock_acquired = await manager.redis_client.set(
                lock_key,
                settings.INSTANCE_ID,
                nx=True,
                ex=30  # 30 second lock
            )
            
            if lock_acquired:
                logger.info(f"Instance {settings.INSTANCE_ID} monitoring Docker events")
                self.running = True
                self.task = asyncio.create_task(self._monitor_events(lock_key))
                await self.task
            else:
                # Another instance is monitoring, wait
                await asyncio.sleep(25)
    
    async def _monitor_events(self, lock_key: str):
        """Monitor and broadcast Docker events"""
        # Renew lock periodically
        async def renew_lock():
            while self.running:
                await asyncio.sleep(20)
                await manager.redis_client.expire(lock_key, 30)
        
        renew_task = asyncio.create_task(renew_lock())
        
        try:
            async for event in self.docker_service.events():
                # Broadcast event to all instances
                await manager.broadcast_to_channel(
                    "docker:events",
                    {
                        "type": "docker_event",
                        "event": event
                    }
                )
                
                # Also broadcast to container-specific channels
                if event.get("Type") == "container" and event.get("id"):
                    await manager.broadcast_to_channel(
                        f"container:events:{event['id']}",
                        event
                    )
        except Exception as e:
            logger.error(f"Error monitoring Docker events: {e}")
        finally:
            self.running = False
            renew_task.cancel()
            await manager.redis_client.delete(lock_key)

# Global event handler
event_handler = DockerEventHandler()
```

### 3.4 Load Balancer Configuration

**Nginx Configuration for WebSocket Load Balancing:**
```nginx
# nginx.conf
upstream backend_websocket {
    # IP hash ensures client stays with same backend
    ip_hash;
    
    server backend1:8000 max_fails=3 fail_timeout=30s;
    server backend2:8000 max_fails=3 fail_timeout=30s;
    server backend3:8000 max_fails=3 fail_timeout=30s;
}

map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    
    # WebSocket endpoints
    location ~ ^/ws/ {
        proxy_pass http://backend_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket timeouts
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        
        # Disable buffering for real-time data
        proxy_buffering off;
    }
    
    # Regular API endpoints
    location /api/ {
        proxy_pass http://backend_websocket;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3.5 Client-Side Reconnection Logic

**React WebSocket Hook with Auto-Reconnect:**
```typescript
// hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from './useAuth';

interface WebSocketOptions {
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket(url: string, options: WebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [reconnectCount, setReconnectCount] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const { token } = useAuth();
  
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10
  } = options;
  
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    // Add auth token to WebSocket URL
    const wsUrl = new URL(url, window.location.origin);
    wsUrl.protocol = wsUrl.protocol.replace('http', 'ws');
    if (token) {
      wsUrl.searchParams.set('token', token);
    }
    
    const ws = new WebSocket(wsUrl.toString());
    
    ws.onopen = () => {
      setIsConnected(true);
      setReconnectCount(0);
      onOpen?.();
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle heartbeat
        if (data.type === 'heartbeat') {
          ws.send(JSON.stringify({ type: 'pong' }));
          return;
        }
        
        onMessage?.(data);
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };
    
    ws.onclose = () => {
      setIsConnected(false);
      onClose?.();
      
      // Attempt reconnection
      if (reconnectCount < maxReconnectAttempts) {
        reconnectTimeoutRef.current = setTimeout(() => {
          setReconnectCount(prev => prev + 1);
          connect();
        }, reconnectInterval * Math.min(reconnectCount + 1, 5));
      }
    };
    
    ws.onerror = (error) => {
      onError?.(error);
    };
    
    wsRef.current = ws;
  }, [url, token, onMessage, onOpen, onClose, onError, reconnectCount]);
  
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);
  
  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected');
    }
  }, []);
  
  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);
  
  return {
    isConnected,
    sendMessage,
    reconnectCount,
    disconnect,
    reconnect: connect
  };
}
```

## 4. Production Deployment Patterns

### 4.1 Kubernetes Deployment with Sticky Sessions

```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docker-control-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: docker-control-backend
  template:
    metadata:
      labels:
        app: docker-control-backend
    spec:
      containers:
      - name: backend
        image: docker-control-backend:latest
        env:
        - name: INSTANCE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        ports:
        - containerPort: 8000
          name: websocket
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  selector:
    app: docker-control-backend
  ports:
  - port: 8000
    targetPort: 8000
  sessionAffinity: ClientIP  # Sticky sessions
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 3600  # 1 hour
```

### 4.2 Health Checks for WebSocket Instances

```python
# app/api/health.py
from fastapi import APIRouter
from app.websocket.manager import manager
import asyncio

router = APIRouter()

@router.get("/health/websocket")
async def websocket_health():
    """Check WebSocket service health"""
    checks = {
        "redis_connected": False,
        "active_connections": 0,
        "active_channels": 0,
        "pubsub_active": False
    }
    
    try:
        # Check Redis connection
        await manager.redis_client.ping()
        checks["redis_connected"] = True
        
        # Count active connections
        for channel, connections in manager.active_connections.items():
            checks["active_channels"] += 1
            checks["active_connections"] += len(connections)
        
        # Check pub/sub
        if manager.pubsub and manager.listener_task:
            checks["pubsub_active"] = not manager.listener_task.done()
        
        status = "healthy" if all([
            checks["redis_connected"],
            checks["pubsub_active"]
        ]) else "degraded"
        
        return {
            "status": status,
            "checks": checks
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "checks": checks
        }
```

## 5. Best Practices and Recommendations

### 5.1 Connection Management
1. **Use Connection Pools**: Maintain Redis connection pools for efficiency
2. **Implement Heartbeats**: Detect stale connections early
3. **Set Reasonable Timeouts**: Balance between connection stability and resource usage
4. **Monitor Connection Metrics**: Track connections per instance

### 5.2 Message Delivery
1. **Implement Message Acknowledgments**: For critical messages
2. **Use Message IDs**: Prevent duplicate processing
3. **Consider Message Persistence**: Store critical messages in Redis/PostgreSQL
4. **Implement Rate Limiting**: Prevent message floods

### 5.3 Scaling Strategies
1. **Start with Vertical Scaling**: Optimize single instance performance first
2. **Use Horizontal Pod Autoscaling**: Scale based on connection count
3. **Implement Graceful Shutdown**: Allow clients to reconnect smoothly
4. **Monitor Redis Pub/Sub Performance**: It can become a bottleneck

### 5.4 Security Considerations
1. **Authenticate WebSocket Connections**: Validate JWT tokens
2. **Implement Connection Limits**: Per user/IP
3. **Use TLS for WebSocket**: WSS in production
4. **Validate All Messages**: Prevent injection attacks

### 5.5 Monitoring and Observability
```python
# app/monitoring/websocket_metrics.py
from prometheus_client import Counter, Gauge, Histogram
import time

# Metrics
ws_connections_total = Counter(
    'websocket_connections_total',
    'Total WebSocket connections',
    ['channel', 'instance']
)

ws_active_connections = Gauge(
    'websocket_active_connections',
    'Active WebSocket connections',
    ['channel', 'instance']
)

ws_messages_sent = Counter(
    'websocket_messages_sent_total',
    'Total messages sent via WebSocket',
    ['channel', 'instance']
)

ws_message_latency = Histogram(
    'websocket_message_latency_seconds',
    'WebSocket message delivery latency',
    ['channel']
)

# Usage in WebSocketManager
async def track_connection(channel: str):
    ws_connections_total.labels(
        channel=channel,
        instance=settings.INSTANCE_ID
    ).inc()
    
    ws_active_connections.labels(
        channel=channel,
        instance=settings.INSTANCE_ID
    ).inc()

async def track_message(channel: str, start_time: float):
    ws_messages_sent.labels(
        channel=channel,
        instance=settings.INSTANCE_ID
    ).inc()
    
    ws_message_latency.labels(
        channel=channel
    ).observe(time.time() - start_time)
```

## Conclusion

Scaling WebSocket applications requires careful architecture design and implementation. The combination of Redis Pub/Sub, connection affinity, and proper monitoring provides a robust foundation for the Docker Control Platform to scale horizontally while maintaining real-time features.

Key takeaways:
- Use Redis Pub/Sub for cross-instance communication
- Implement proper connection management and reconnection logic
- Monitor and load balance effectively
- Design for failure with graceful degradation
- Keep security as a primary concern

This architecture can handle thousands of concurrent WebSocket connections across multiple backend instances while maintaining low latency and high reliability.