"""
Updated service endpoints to use unified log handler.

This shows how to update the service logs WebSocket endpoint to use
the new unified log streaming architecture.
"""

from fastapi import WebSocket, Query
from app.services.logs import LogSourceType
from app.api.v1.websocket.unified_logs import handle_log_websocket

# ... other imports and endpoints remain the same ...

# Replace the existing service_logs_ws endpoint with this:

@router.websocket("/{service_id}/logs")
async def service_logs_ws(
    websocket: WebSocket,
    service_id: str,
    host_id: str = Query(..., description="Docker host ID (must be a swarm manager)"),
    tail: int = Query(100, description="Number of lines to show from the end"),
    follow: bool = Query(True, description="Follow log output"),
    timestamps: bool = Query(False, description="Add timestamps"),
    token: Optional[str] = Query(None)
):
    """
    Stream service logs via WebSocket.
    
    This endpoint now uses the unified log streaming architecture,
    ensuring consistency with container logs and other log sources.
    """
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