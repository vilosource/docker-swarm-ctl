from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional
import asyncio
import json
import logging
import struct
from app.api.v1.websocket.auth import get_current_user_ws, check_permission
from app.services.docker_client import DockerClientFactory
from app.models.user import User
from docker.errors import NotFound, APIError
import socket

logger = logging.getLogger(__name__)
router = APIRouter()

# Get container hostname to detect self-monitoring
CONTAINER_HOSTNAME = socket.gethostname()

def is_self_monitoring(container_id: str, docker_client) -> bool:
    """Check if we're monitoring our own container to prevent log loops."""
    try:
        container = docker_client.containers.get(container_id)
        container_hostname = container.attrs.get('Config', {}).get('Hostname', '')
        # Also check by container name patterns
        container_name = container.name
        # Common patterns for backend container names
        is_backend = any(pattern in container_name.lower() for pattern in ['backend', 'api', 'fastapi'])
        return container_hostname == CONTAINER_HOSTNAME or is_backend
    except:
        return False


@router.websocket("/containers/{container_id}/exec")
async def container_exec_ws(
    websocket: WebSocket,
    container_id: str,
    cmd: str = Query(None, description="Command to execute (auto-detect if not provided)"),
    workdir: str = Query("/", description="Working directory"),
    token: Optional[str] = Query(None, description="JWT token for authentication")
):
    """WebSocket endpoint for interactive container exec sessions."""
    # Authenticate
    user = await get_current_user_ws(websocket, token)
    if not user:
        return
    
    # Check permissions (operator or higher can exec)
    if not check_permission(user, "operator"):
        await websocket.close(code=1008, reason="Insufficient permissions")
        return
    
    await websocket.accept()
    
    # Check if self-monitoring to avoid log loops
    docker = DockerClientFactory.get_client()
    if not is_self_monitoring(container_id, docker):
        logger.info(f"User {user.username} starting exec session in container {container_id}")
    
    exec_instance = None
    exec_socket = None
    
    try:
        docker = DockerClientFactory.get_client()
        container = docker.containers.get(container_id)
        
        # Check if container is running
        if container.status != 'running':
            await websocket.send_json({
                "type": "error",
                "message": f"Container {container_id} is not running"
            })
            await websocket.close()
            return
        
        # Auto-detect shell if not provided
        if not cmd:
            # Try to detect available shell
            shells = ["/bin/bash", "/bin/sh", "/usr/bin/bash", "/usr/bin/sh", "bash", "sh"]
            for shell in shells:
                try:
                    # Test if shell exists
                    result = container.exec_run(f"which {shell}", stderr=False)
                    if result.exit_code == 0:
                        cmd = shell
                        if not is_self_monitoring(container_id, docker):
                            logger.info(f"Detected shell: {cmd}")
                        break
                except Exception:
                    continue
            
            if not cmd:
                # Default to sh if nothing found
                cmd = "/bin/sh"
                if not is_self_monitoring(container_id, docker):
                    logger.info(f"Using default shell: {cmd}")
        
        # Create exec instance
        exec_instance = docker.api.exec_create(
            container.id,
            cmd,
            stdin=True,
            stdout=True,
            stderr=True,
            tty=True,
            workdir=workdir
        )
        
        exec_id = exec_instance['Id']
        
        # Start exec and get socket
        exec_socket = docker.api.exec_start(
            exec_id,
            socket=True,
            tty=True
        )
        exec_socket._sock.setblocking(False)
        
        # Important: Need to read the attach headers first if not in TTY mode
        # In TTY mode, there are no headers
        
        # Flag to track if exec is started
        exec_started = True
        
        # Send initial success message
        await websocket.send_json({
            "type": "connected",
            "message": f"Connected to container {container.name or container_id}",
            "shell": cmd
        })
        
        # Send initial newline to trigger shell prompt
        await asyncio.sleep(0.1)  # Small delay to ensure exec is ready
        try:
            exec_socket._sock.sendall(b'\n')
            if not is_self_monitoring(container_id, docker):
                logger.info("Sent initial newline")
        except Exception as e:
            if not is_self_monitoring(container_id, docker):
                logger.debug(f"Initial newline send failed: {e}")
        
        # Create tasks for bidirectional communication
        loop = asyncio.get_event_loop()
        
        async def read_from_docker():
            """Read from Docker exec and send to WebSocket"""
            while True:
                try:
                    # Use run_in_executor for blocking recv
                    def read_socket():
                        try:
                            return exec_socket._sock.recv(4096)
                        except BlockingIOError:
                            return None
                    
                    data = await loop.run_in_executor(None, read_socket)
                    
                    if data is None:
                        # No data available, wait a bit
                        await asyncio.sleep(0.01)
                        continue
                    elif not data:
                        # Socket closed
                        if not is_self_monitoring(container_id, docker):
                            logger.info("Docker socket closed")
                        break
                    
                    # Send data to WebSocket
                    await websocket.send_bytes(data)
                    
                except Exception as e:
                    if not is_self_monitoring(container_id, docker):
                        logger.error(f"Error reading from Docker: {e}")
                    break
        
        async def write_to_docker():
            """Read from WebSocket and write to Docker exec"""
            while True:
                try:
                    message = await websocket.receive()
                    
                    if message["type"] == "websocket.disconnect":
                        break
                    
                    if "bytes" in message:
                        # Binary message (terminal data)
                        data = message["bytes"]
                        exec_socket._sock.sendall(data)
                    elif "text" in message:
                        # Text message (could be control commands)
                        text_data = message["text"]
                        try:
                            json_data = json.loads(text_data)
                            if json_data.get("type") == "resize":
                                # Handle terminal resize
                                rows = json_data.get("rows", 24)
                                cols = json_data.get("cols", 80)
                                # Docker exec resize API
                                try:
                                    docker.api.exec_resize(exec_id, height=rows, width=cols)
                                    if not is_self_monitoring(container_id, docker):
                                        logger.info(f"Resized terminal to {rows}x{cols}")
                                except Exception as e:
                                    # Ignore resize errors - exec might not be fully started yet
                                    if not is_self_monitoring(container_id, docker):
                                        logger.debug(f"Resize failed (exec may not be started): {e}")
                        except json.JSONDecodeError:
                            # Not JSON, treat as terminal input
                            exec_socket._sock.sendall(text_data.encode())
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    if not is_self_monitoring(container_id, docker):
                        logger.error(f"Error writing to Docker: {e}")
                    break
        
        # Run both tasks concurrently
        if not is_self_monitoring(container_id, docker):
            logger.info("Starting read/write tasks")
        try:
            await asyncio.gather(
                read_from_docker(),
                write_to_docker()
            )
        except asyncio.CancelledError:
            if not is_self_monitoring(container_id, docker):
                logger.info("Tasks cancelled")
        except Exception as e:
            if not is_self_monitoring(container_id, docker):
                logger.error(f"Error in gather: {e}")
    
    except NotFound:
        await websocket.send_json({
            "type": "error",
            "message": f"Container {container_id} not found"
        })
    except APIError as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Docker API error: {str(e)}"
        })
    except Exception as e:
        docker = DockerClientFactory.get_client()
        if not is_self_monitoring(container_id, docker):
            logger.error(f"Error in exec WebSocket: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Cleanup
        if exec_socket:
            try:
                exec_socket.close()
            except:
                pass
        if not is_self_monitoring(container_id, docker):
            logger.info(f"Exec session ended for container {container_id}")