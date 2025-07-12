"""
Updated container WebSocket endpoints to use unified log handler.

This shows how to update the container logs WebSocket endpoint to use
the new unified log streaming architecture.
"""

from fastapi import WebSocket, Query
from app.services.logs import LogSourceType
from app.api.v1.websocket.unified_logs import handle_log_websocket

# ... other imports and endpoints remain the same ...

# Replace the existing container_logs_ws endpoint with this:

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
    """
    Stream container logs via WebSocket.
    
    This endpoint now uses the unified log streaming architecture,
    providing consistent behavior across all log sources.
    """
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