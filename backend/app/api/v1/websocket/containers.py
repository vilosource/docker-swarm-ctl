from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional, AsyncGenerator
from datetime import datetime
import asyncio
import json
import logging
from app.api.v1.websocket.auth import get_current_user_ws, check_permission
from app.api.v1.websocket.base import manager
from app.services.docker_client import DockerClientFactory
from app.models.user import User
from docker.errors import NotFound, APIError
from collections import deque

logger = logging.getLogger(__name__)
router = APIRouter()

# Ring buffer for recent logs per container
log_buffers: dict[str, deque] = {}
BUFFER_SIZE = 1000

# Active log streams per container
active_streams: dict[str, AsyncGenerator] = {}
stream_locks: dict[str, asyncio.Lock] = {}


class LogStreamManager:
    """Manages Docker log streams to avoid duplicates."""
    
    @staticmethod
    async def get_or_create_stream(container_id: str, follow: bool = True, tail: int = 100):
        """Get existing stream or create new one for a container."""
        if container_id not in stream_locks:
            stream_locks[container_id] = asyncio.Lock()
        
        async with stream_locks[container_id]:
            if container_id not in active_streams or not follow:
                # Create new stream
                docker = DockerClientFactory.get_client()
                try:
                    container = docker.containers.get(container_id)
                    logger.info(f"Creating log stream for container {container_id} (follow={follow}, tail={tail})")
                    # Start streaming logs
                    active_streams[container_id] = container.logs(
                        stream=True,
                        follow=follow,
                        timestamps=True,
                        tail=tail
                    )
                    # Initialize buffer if needed
                    if container_id not in log_buffers:
                        log_buffers[container_id] = deque(maxlen=BUFFER_SIZE)
                except NotFound:
                    logger.error(f"Container {container_id} not found")
                    raise ValueError(f"Container {container_id} not found")
                except APIError as e:
                    logger.error(f"Docker API error for container {container_id}: {str(e)}")
                    raise ValueError(f"Docker API error: {str(e)}")
            
            return active_streams.get(container_id)
    
    @staticmethod
    async def stop_stream(container_id: str):
        """Stop and cleanup a log stream."""
        if container_id in stream_locks:
            async with stream_locks[container_id]:
                if container_id in active_streams:
                    try:
                        # Close the generator
                        active_streams[container_id].close()
                    except:
                        pass
                    del active_streams[container_id]
                # Also clean up the lock if no longer needed
                if container_id not in active_streams:
                    del stream_locks[container_id]
                    # Clean up buffer too
                    if container_id in log_buffers:
                        del log_buffers[container_id]


async def log_reader(container_id: str, follow: bool, tail: int) -> AsyncGenerator[str, None]:
    """Read logs from Docker and yield them."""
    try:
        stream = await LogStreamManager.get_or_create_stream(container_id, follow, tail)
        if stream:
            # Add timeout for reading logs
            last_log_time = asyncio.get_event_loop().time()
            timeout = 300  # 5 minutes timeout for no logs
            
            try:
                # Run the synchronous Docker log stream in a thread
                loop = asyncio.get_event_loop()
                
                def read_logs():
                    for line in stream:
                        if line:
                            return line
                    return None
                
                while True:
                    line = await loop.run_in_executor(None, read_logs)
                    if line is None:
                        break
                        
                    # Decode and clean the log line
                    log_line = line.decode('utf-8').strip()
                    if log_line:
                        # Store in buffer
                        if container_id in log_buffers:
                            log_buffers[container_id].append(log_line)
                        yield log_line
                        last_log_time = asyncio.get_event_loop().time()
                    
                    # Check for timeout
                    if follow and (asyncio.get_event_loop().time() - last_log_time) > timeout:
                        logger.info(f"Log stream timeout for container {container_id}")
                        break
                    
                    # Allow other tasks to run
                    await asyncio.sleep(0)
            except GeneratorExit:
                logger.info(f"Log stream generator closed for container {container_id}")
                raise
            except Exception as e:
                logger.error(f"Error in log stream: {e}")
    except Exception as e:
        logger.error(f"Error reading logs for container {container_id}: {e}")
        yield f"Error: {str(e)}"
    finally:
        if not follow:
            await LogStreamManager.stop_stream(container_id)


@router.websocket("/containers/{container_id}/logs")
async def container_logs_ws(
    websocket: WebSocket,
    container_id: str,
    follow: bool = Query(True, description="Follow log output"),
    tail: int = Query(100, description="Number of lines to show from the end"),
    timestamps: bool = Query(True, description="Show timestamps"),
    since: Optional[str] = Query(None, description="Show logs since timestamp"),
    token: Optional[str] = Query(None, description="JWT token for authentication")
):
    """WebSocket endpoint for streaming container logs."""
    # Authenticate
    user = await get_current_user_ws(websocket, token)
    if not user:
        return
    
    # Check permissions (viewer or higher can view logs)
    if not check_permission(user, "viewer"):
        await websocket.close(code=1008, reason="Insufficient permissions")
        return
    
    # Register connection
    if not await manager.connect(websocket, container_id, user.username):
        return
    
    try:
        # Send buffered logs first if available
        if container_id in log_buffers and tail > 0:
            buffered_logs = list(log_buffers[container_id])[-tail:]
            for log_line in buffered_logs:
                await websocket.send_json({
                    "type": "log",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": log_line,
                    "container_id": container_id
                })
        
        # Check if we're already streaming this container
        connection_count = manager.get_connection_count(container_id)
        
        if connection_count == 1:  # First connection, start streaming
            logger.info(f"Starting log stream for container {container_id}")
            # Start log reading task
            log_count = 0
            async for log_line in log_reader(container_id, follow, tail if not log_buffers.get(container_id) else 0):
                # Broadcast to all connections
                await manager.broadcast_to_container(container_id, {
                    "type": "log",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": log_line,
                    "container_id": container_id
                })
                log_count += 1
                
                if not follow:
                    break
            logger.info(f"Log stream ended for container {container_id}, sent {log_count} lines")
        else:
            # Just wait for broadcasts from the existing stream
            # Use a more efficient wait mechanism
            try:
                while True:
                    # Wait for a longer period to reduce CPU usage
                    await asyncio.sleep(30)
                    # Send a ping less frequently
                    try:
                        await websocket.send_json({"type": "ping"})
                    except:
                        break
            except asyncio.CancelledError:
                # Handle graceful shutdown
                pass
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for container {container_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass
    finally:
        # Cleanup
        await manager.disconnect(websocket, container_id)
        
        # If this was the last connection, stop the stream
        if manager.get_connection_count(container_id) == 0:
            await LogStreamManager.stop_stream(container_id)


@router.websocket("/containers/{container_id}/stats")
async def container_stats_ws(
    websocket: WebSocket,
    container_id: str,
    token: Optional[str] = Query(None, description="JWT token for authentication")
):
    """WebSocket endpoint for streaming container stats."""
    # Authenticate
    user = await get_current_user_ws(websocket, token)
    if not user:
        return
    
    # Check permissions
    if not check_permission(user, "viewer"):
        await websocket.close(code=1008, reason="Insufficient permissions")
        return
    
    await websocket.accept()
    
    try:
        docker = DockerClientFactory.get_client()
        container = docker.containers.get(container_id)
        
        # Use thread executor for synchronous Docker API
        loop = asyncio.get_event_loop()
        
        def get_stats_stream():
            return container.stats(stream=True, decode=True)
        
        # Get the stats generator in a thread
        stats_generator = await loop.run_in_executor(None, get_stats_stream)
        
        def read_next_stat():
            try:
                return next(stats_generator)
            except StopIteration:
                return None
            except Exception as e:
                logger.error(f"Error reading stats: {e}")
                return None
        
        # Stream stats
        while True:
            stats = await loop.run_in_executor(None, read_next_stat)
            if stats is None:
                break
            # Calculate CPU usage percentage
            cpu_percent = 0.0
            try:
                if 'cpu_stats' in stats and 'precpu_stats' in stats:
                    cpu_stats = stats['cpu_stats']
                    precpu_stats = stats['precpu_stats']
                    
                    # Check if we have the required fields
                    if ('cpu_usage' in cpu_stats and 'cpu_usage' in precpu_stats and
                        'total_usage' in cpu_stats['cpu_usage'] and 'total_usage' in precpu_stats['cpu_usage']):
                        
                        cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
                        
                        # Handle different Docker versions - some use system_cpu_usage, others use system_cpu_usage
                        system_cpu_usage = cpu_stats.get('system_cpu_usage', 0)
                        pre_system_cpu_usage = precpu_stats.get('system_cpu_usage', 0)
                        
                        # If system_cpu_usage is not available, try online_cpus * 100
                        if system_cpu_usage == 0 or pre_system_cpu_usage == 0:
                            online_cpus = cpu_stats.get('online_cpus', len(cpu_stats['cpu_usage'].get('percpu_usage', [1])))
                            cpu_percent = (cpu_delta / 1000000000.0) * 100.0  # Convert nanoseconds to percentage
                        else:
                            system_delta = system_cpu_usage - pre_system_cpu_usage
                            if system_delta > 0 and cpu_delta > 0:
                                cpu_count = len(cpu_stats['cpu_usage'].get('percpu_usage', [1]))
                                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
            except Exception as e:
                logger.warning(f"Error calculating CPU stats: {e}")
                cpu_percent = 0.0
            
            # Calculate memory usage
            mem_usage = stats.get('memory_stats', {}).get('usage', 0)
            mem_limit = stats.get('memory_stats', {}).get('limit', 1)
            mem_percent = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0
            
            await websocket.send_json({
                "type": "stats",
                "timestamp": datetime.utcnow().isoformat(),
                "container_id": container_id,
                "data": {
                    "cpu_percent": round(cpu_percent, 2),
                    "memory": {
                        "usage": mem_usage,
                        "limit": mem_limit,
                        "percent": round(mem_percent, 2)
                    },
                    "networks": stats.get('networks', {}),
                    "block_io": stats.get('blkio_stats', {})
                }
            })
            
            await asyncio.sleep(1)  # Rate limit to 1 update per second
    
    except WebSocketDisconnect:
        logger.info(f"Stats WebSocket disconnected for container {container_id}")
    except NotFound:
        await websocket.send_json({
            "type": "error",
            "message": f"Container {container_id} not found"
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