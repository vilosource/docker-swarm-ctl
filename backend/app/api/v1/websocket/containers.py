"""
Simplified Refactored Container WebSocket Handlers

A simpler implementation that reduces code duplication without complex inheritance.
"""

from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import asyncio
import json
from collections import deque

from app.db.session import get_db, AsyncSessionLocal
from app.services.docker_service import DockerServiceFactory
from app.services.docker_connection_manager import get_docker_connection_manager
from app.services.self_monitoring import get_self_monitoring_service
from app.services.container_stats_calculator import ContainerStatsCalculator
from app.api.v1.websocket.auth import check_permission
from app.api.v1.websocket.base import manager
from app.core.logging import logger
from app.core.config import settings
from app.services.user import UserService
from jose import JWTError, jwt
from docker.errors import NotFound, APIError


# Shared authentication function
async def authenticate_websocket_user(token: Optional[str], db: AsyncSession):
    """Authenticate WebSocket connection using JWT token"""
    if not token:
        return None, "Missing authentication token"
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            return None, "Invalid token"
    except JWTError:
        return None, "Invalid token"
    
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    if user is None or not user.is_active:
        return None, "User not found or inactive"
    
    return user, None


# Shared Docker client getter
async def get_docker_for_websocket(host_id: Optional[str], user, db: AsyncSession):
    """Get Docker client for WebSocket connection"""
    if host_id:
        connection_manager = get_docker_connection_manager()
        return await connection_manager.get_client(host_id, user, db)
    else:
        from app.services.docker_client import DockerClientFactory
        return DockerClientFactory.get_client()


# Log buffer management
log_buffers: Dict[str, deque] = {}
BUFFER_SIZE = 1000
active_streams: Dict[str, AsyncGenerator] = {}
stream_locks: Dict[str, asyncio.Lock] = {}


async def stream_container_logs(
    container_id: str,
    docker_client,
    follow: bool = True,
    tail: int = 100,
    timestamps: bool = True
) -> AsyncGenerator[str, None]:
    """Stream logs from a container"""
    if container_id not in stream_locks:
        stream_locks[container_id] = asyncio.Lock()
    
    async with stream_locks[container_id]:
        if container_id not in active_streams or not follow:
            try:
                container = docker_client.containers.get(container_id)
                stream = container.logs(
                    stream=True,
                    follow=follow,
                    timestamps=timestamps,
                    tail=tail
                )
                active_streams[container_id] = stream
                
                if container_id not in log_buffers:
                    log_buffers[container_id] = deque(maxlen=BUFFER_SIZE)
            except NotFound:
                raise ValueError(f"Container {container_id} not found")
            except APIError as e:
                raise ValueError(f"Docker API error: {str(e)}")
    
    stream = active_streams.get(container_id)
    if not stream:
        return
    
    loop = asyncio.get_event_loop()
    
    def read_log_line():
        try:
            for line in stream:
                if line:
                    return line
            return None
        except:
            return None
    
    try:
        while True:
            line = await loop.run_in_executor(None, read_log_line)
            if line is None:
                break
            
            log_line = line.decode('utf-8').strip()
            if log_line:
                # Skip corrupted logs
                if log_line.count('\\') > 100:
                    continue
                
                # Store in buffer
                if container_id in log_buffers:
                    log_buffers[container_id].append(log_line)
                
                yield log_line
            
            await asyncio.sleep(0)
    finally:
        if not follow:
            # Cleanup stream
            if container_id in active_streams:
                try:
                    active_streams[container_id].close()
                except:
                    pass
                del active_streams[container_id]


async def stream_container_stats(container_id: str, docker_client) -> AsyncGenerator[dict, None]:
    """Stream stats from a container"""
    try:
        container = docker_client.containers.get(container_id)
    except NotFound:
        raise ValueError(f"Container {container_id} not found")
    
    loop = asyncio.get_event_loop()
    
    def get_stats_stream():
        return container.stats(stream=True, decode=True)
    
    stats_generator = await loop.run_in_executor(None, get_stats_stream)
    
    def read_next_stat():
        try:
            return next(stats_generator)
        except StopIteration:
            return None
        except Exception:
            return None
    
    stats_calculator = ContainerStatsCalculator()
    
    while True:
        raw_stats = await loop.run_in_executor(None, read_next_stat)
        if raw_stats is None:
            break
        
        # Calculate stats using the service
        stats = stats_calculator.calculate_stats(raw_stats)
        
        yield {
            "cpu_percent": stats.cpu_percent,
            "memory_usage": stats.memory_usage,
            "memory_limit": stats.memory_limit,
            "memory_percent": stats.memory_percent,
            "network_rx": stats.network_rx,
            "network_tx": stats.network_tx,
            "block_read": stats.block_read,
            "block_write": stats.block_write,
            "pids": stats.pids
        }
        
        await asyncio.sleep(1)


# Router setup
router = APIRouter()


@router.websocket("/containers/{container_id}/logs")
async def container_logs_ws(
    websocket: WebSocket,
    container_id: str,
    follow: bool = Query(True),
    tail: int = Query(100),
    timestamps: bool = Query(True),
    token: Optional[str] = Query(None),
    host_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for streaming container logs.
    
    This endpoint now uses the unified log streaming architecture,
    ensuring consistency with service logs and other log sources.
    """
    from app.services.logs import LogSourceType
    from app.api.v1.websocket.unified_logs import handle_log_websocket
    
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


@router.websocket("/containers/{container_id}/stats")
async def container_stats_ws(
    websocket: WebSocket,
    container_id: str,
    token: Optional[str] = Query(None),
    host_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for streaming container stats"""
    # Authenticate user
    user, error = await authenticate_websocket_user(token, db)
    if not user:
        await websocket.accept()
        await websocket.close(code=1008, reason=error)
        return
    
    # Check permissions
    if not check_permission(user, "viewer"):
        await websocket.accept()
        await websocket.close(code=1008, reason="Insufficient permissions")
        return
    
    # Accept connection
    await websocket.accept()
    
    db_session = None
    
    try:
        # Get Docker client
        if host_id:
            # Create new session for multi-host
            db_session = AsyncSessionLocal()
            db = await db_session.__aenter__()
            docker_client = await get_docker_for_websocket(host_id, user, db)
        else:
            docker_client = await get_docker_for_websocket(None, user, db)
        
        # Stream stats
        update_count = 0
        async for stats in stream_container_stats(container_id, docker_client):
            await websocket.send_json({
                "type": "stats",
                "timestamp": datetime.utcnow().isoformat(),
                "container_id": container_id,
                "data": stats,
                "update_number": update_count
            })
            update_count += 1
    
    except WebSocketDisconnect:
        logger.info(f"Stats WebSocket disconnected for container {container_id}")
    except ValueError as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    except Exception as e:
        logger.error(f"Error in stats WebSocket: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Close DB session
        if db_session:
            await db_session.__aexit__(None, None, None)