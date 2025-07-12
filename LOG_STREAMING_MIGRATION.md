# Log Streaming Architecture Migration Guide

This guide explains how to migrate from the current separate log implementations to the new unified log streaming architecture.

## Overview

The new unified log streaming architecture provides:
- **Single implementation** for all log types (container, service, host, etc.)
- **Connection pooling** - multiple WebSocket clients share the same log stream
- **Buffering** - late-joining clients receive recent logs
- **Consistent behavior** across all log sources
- **Easy extensibility** for future log types

## Architecture Components

### 1. Core Abstractions (`/backend/app/services/logs/base.py`)
- `LogEntry` - Standardized log entry format
- `LogSource` - Abstract interface for log providers
- `LogSourceMetadata` - Information about log sources

### 2. Stream Manager (`/backend/app/services/logs/stream_manager.py`)
- Manages active log streams
- Handles connection pooling
- Provides buffering
- Broadcasts to multiple clients

### 3. Log Router (`/backend/app/services/logs/router.py`)
- Registry of available log sources
- Routes requests to appropriate providers

### 4. Log Providers (`/backend/app/services/logs/providers/`)
- `ContainerLogSource` - Docker container logs
- `ServiceLogSource` - Docker Swarm service logs
- Future: `HostLogSource`, `DaemonLogSource`, etc.

### 5. Unified WebSocket Handler (`/backend/app/api/v1/websocket/unified_logs.py`)
- Single handler for all log types
- Consistent authentication and error handling
- Uses stream manager for efficiency

## Migration Steps

### Backend Migration

#### Step 1: Update Service Logs Endpoint

Replace the current implementation in `/backend/app/api/v1/endpoints/services.py`:

```python
# Old implementation
@router.websocket("/{service_id}/logs")
async def service_logs_ws(
    websocket: WebSocket,
    service_id: str,
    # ... parameters ...
):
    # Complex custom implementation
    # ...

# New implementation
from app.services.logs import LogSourceType
from app.api.v1.websocket.unified_logs import handle_log_websocket

@router.websocket("/{service_id}/logs")
async def service_logs_ws(
    websocket: WebSocket,
    service_id: str,
    host_id: str = Query(...),
    tail: int = Query(100),
    follow: bool = Query(True),
    timestamps: bool = Query(False),
    token: Optional[str] = Query(None)
):
    """Stream service logs via WebSocket using unified architecture."""
    await handle_log_websocket(
        websocket=websocket,
        source_type=LogSourceType.SERVICE,
        resource_id=service_id,
        host_id=host_id,
        tail=tail,
        follow=follow,
        timestamps=timestamps,
        token=token
    )
```

#### Step 2: Update Container Logs Endpoint

Update `/backend/app/api/v1/websocket/containers.py`:

```python
# Replace the container_logs_ws function with:
@router.websocket("/containers/{container_id}/logs")
async def container_logs_ws(
    websocket: WebSocket,
    container_id: str,
    follow: bool = Query(True),
    tail: int = Query(100),
    timestamps: bool = Query(True),
    token: Optional[str] = Query(None),
    host_id: Optional[str] = Query(None)
):
    """Stream container logs via WebSocket using unified architecture."""
    await handle_log_websocket(
        websocket=websocket,
        source_type=LogSourceType.CONTAINER,
        resource_id=container_id,
        host_id=host_id,
        tail=tail,
        follow=follow,
        timestamps=timestamps,
        token=token
    )
```

#### Step 3: Initialize Stream Manager

Add to `/backend/app/main.py`:

```python
from app.services.logs.stream_manager import stream_manager_lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Existing startup code...
    
    # Start log stream manager
    async with stream_manager_lifespan():
        yield
    
    # Existing shutdown code...
```

### Frontend Migration

#### Step 1: Create Unified Log Hook

Create `/frontend/src/hooks/useUnifiedLogStream.ts`:

```typescript
import { useWebSocket } from './useWebSocket'
import { useAuthStore } from '../store/authStore'

export type LogSourceType = 'container' | 'service' | 'host' | 'daemon' | 'stack'

interface UseUnifiedLogStreamOptions {
  sourceType: LogSourceType
  resourceId: string
  hostId?: string
  tail?: number
  follow?: boolean
  timestamps?: boolean
  enabled?: boolean
}

export function useUnifiedLogStream({
  sourceType,
  resourceId,
  hostId,
  tail = 100,
  follow = true,
  timestamps = true,
  enabled = true
}: UseUnifiedLogStreamOptions) {
  const { token } = useAuthStore()
  
  // Build WebSocket URL based on source type
  const wsUrl = resourceId && token && enabled
    ? buildLogWebSocketUrl(sourceType, resourceId, {
        host_id: hostId,
        tail,
        follow,
        timestamps,
        token
      })
    : null
  
  return useWebSocket({
    url: wsUrl,
    onMessage: handleLogMessage,
    enabled: !!wsUrl
  })
}

function buildLogWebSocketUrl(
  sourceType: LogSourceType,
  resourceId: string,
  params: Record<string, any>
): string {
  const baseUrl = import.meta.env.VITE_WS_URL
  
  // Map source types to endpoints
  const endpoints: Record<LogSourceType, string> = {
    container: `/containers/${resourceId}/logs`,
    service: `/services/${resourceId}/logs`,
    host: `/hosts/${resourceId}/logs`,
    daemon: `/daemon/${resourceId}/logs`,
    stack: `/stacks/${resourceId}/logs`
  }
  
  const endpoint = endpoints[sourceType]
  const queryString = new URLSearchParams(params).toString()
  
  return `${baseUrl}${endpoint}?${queryString}`
}
```

#### Step 2: Update Container Logs Component

Update `ContainerLogs.tsx` to use the unified hook:

```typescript
import { useUnifiedLogStream } from '../hooks/useUnifiedLogStream'

export const ContainerLogs: React.FC<ContainerLogsProps> = ({ 
  containerId, 
  hostId 
}) => {
  const {
    logs,
    isConnected,
    error,
    reconnect
  } = useUnifiedLogStream({
    sourceType: 'container',
    resourceId: containerId,
    hostId,
    follow: true,
    tail: 100
  })
  
  // Rest of component remains the same
}
```

#### Step 3: Update Service Logs Hook

Update `useServiceLogs.ts` to use the unified hook:

```typescript
import { useUnifiedLogStream } from './useUnifiedLogStream'

export const useServiceLogs = ({
  hostId,
  serviceId,
  tail = 100,
  follow = true,
  timestamps = false,
  autoConnect = true
}: UseServiceLogsOptions) => {
  return useUnifiedLogStream({
    sourceType: 'service',
    resourceId: serviceId,
    hostId,
    tail,
    follow,
    timestamps,
    enabled: autoConnect
  })
}
```

## Benefits of Migration

1. **Code Reduction**: Remove ~50% of duplicated code
2. **Consistency**: Both log types work identically
3. **Performance**: Connection pooling reduces server load
4. **Features**: All log types get buffering, multi-client support
5. **Maintainability**: Single implementation to maintain
6. **Extensibility**: Easy to add new log sources

## Testing Migration

1. **Test Container Logs**:
   - Single client connection
   - Multiple clients to same container
   - Buffering for late-joining clients
   - Disconnection/reconnection

2. **Test Service Logs**:
   - Service logs from Swarm manager
   - Multiple replicas aggregation
   - Error handling for non-manager nodes

3. **Performance Testing**:
   - Load test with many concurrent connections
   - Verify memory usage with buffering
   - Test stream cleanup

## Rollback Plan

If issues arise:
1. Keep old endpoints during transition
2. Use feature flags to switch between old/new
3. Monitor error rates and performance
4. Rollback by switching feature flag

## Future Additions

With this architecture, adding new log sources is simple:

1. Create new provider in `/backend/app/services/logs/providers/`
2. Register with log router
3. Add endpoint mapping in frontend
4. No changes needed to WebSocket handler or stream manager

Example for host system logs:
```python
class HostSystemLogSource(LogSource):
    async def get_logs(self, resource_id: str, **kwargs):
        # Implementation to read journald/syslog
        pass
```

## Conclusion

This migration creates a robust, extensible log streaming architecture that will serve as the foundation for all current and future log streaming needs.