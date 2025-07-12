"""
Async WebSocket handler for container exec using aiodocker
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional
import asyncio
import json
import logging
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.websocket.auth import get_current_user_ws, check_permission
from app.services.async_docker_connection_manager import get_async_docker_connection_manager
from app.services.self_monitoring_detector import is_self_monitoring_async
from app.db.session import get_db
from app.models.user import User
from app.core.exceptions import ResourceNotFoundError, DockerOperationError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/containers/{container_id}/exec")
async def container_exec_ws(
    websocket: WebSocket,
    container_id: str,
    cmd: str = Query(None, description="Command to execute (auto-detect if not provided)"),
    workdir: str = Query("/", description="Working directory"),
    token: Optional[str] = Query(None, description="JWT token for authentication"),
    host_id: Optional[str] = Query(None, description="Docker host ID (for multi-host deployments)")
):
    """WebSocket endpoint for interactive container exec sessions using aiodocker."""
    # Authenticate
    user = await get_current_user_ws(websocket, token)
    if not user:
        return
    
    # Check permissions (operator or higher can exec)
    if not check_permission(user, "operator"):
        await websocket.close(code=1008, reason="Insufficient permissions")
        return
    
    await websocket.accept()
    
    # Get async Docker client
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        connection_manager = get_async_docker_connection_manager()
        try:
            # For local connections, use the default host
            if not host_id:
                host_id = await connection_manager.get_default_host_id(db, user)
            
            client = await connection_manager.get_client(host_id, user, db)
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to connect to host: {str(e)}"
            })
            await websocket.close()
            return
    
    try:
        # Get container
        try:
            container = await client.containers.get(container_id)
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                await websocket.send_json({
                    "type": "error",
                    "message": f"Container {container_id} not found"
                })
                await websocket.close()
                return
            raise
        
        # Check if container is running
        container_info = await container.show()
        if container_info.get('State', {}).get('Status') != 'running':
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
                    exec_create = await container.exec([shell, "-c", "echo test"], 
                                                      stdout=True, stderr=True)
                    output = await exec_create.start(detach=False)
                    if output and b"test" in output:
                        cmd = shell
                        logger.info(f"Detected shell: {cmd}")
                        break
                except Exception:
                    continue
            
            if not cmd:
                # Default to sh if nothing found
                cmd = "/bin/sh"
                logger.info(f"Using default shell: {cmd}")
        
        # Create exec instance with TTY for interactive session
        exec_instance = await container.exec(
            cmd=[cmd] if isinstance(cmd, str) else cmd,
            stdin=True,
            stdout=True,
            stderr=True,
            tty=True,
            workdir=workdir,
            environment={},  # Add any env vars if needed
            user=None  # Run as default user in container
        )
        
        # Start exec and get WebSocket response
        # When detach=False and tty=True, this returns a WebSocket-like response
        ws_response = await exec_instance.start(detach=False)
        
        # Send initial success message
        await websocket.send_json({
            "type": "connected",
            "message": f"Connected to container {container_id}",
            "shell": cmd
        })
        
        # Create tasks for bidirectional communication
        async def read_from_docker():
            """Read from Docker exec WebSocket and send to client"""
            try:
                async for msg in ws_response:
                    if msg.type == aiohttp.WSMsgType.BINARY:
                        # Send binary data directly to the terminal
                        await websocket.send_bytes(msg.data)
                    elif msg.type == aiohttp.WSMsgType.TEXT:
                        # Handle text messages (unlikely in TTY mode)
                        await websocket.send_bytes(msg.data.encode('utf-8'))
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f'WebSocket error: {ws_response.exception()}')
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSE:
                        break
            except Exception as e:
                logger.error(f"Error reading from Docker: {e}")
            finally:
                # Ensure WebSocket is closed
                if not ws_response.closed:
                    await ws_response.close()
        
        async def write_to_docker():
            """Read from client WebSocket and send to Docker exec"""
            try:
                while True:
                    message = await websocket.receive()
                    
                    if message["type"] == "websocket.disconnect":
                        break
                    
                    if "bytes" in message:
                        # Send input to Docker
                        await ws_response.send_bytes(message["bytes"])
                    elif "text" in message:
                        # Handle JSON messages (e.g., resize)
                        try:
                            data = json.loads(message["text"])
                            if data.get("type") == "resize":
                                # Handle terminal resize
                                rows = data.get("rows", 24)
                                cols = data.get("cols", 80)
                                await exec_instance.resize(h=rows, w=cols)
                                logger.debug(f"Resized terminal to {cols}x{rows}")
                        except json.JSONDecodeError:
                            # If not JSON, treat as text input
                            await ws_response.send_bytes(message["text"].encode('utf-8'))
            except WebSocketDisconnect:
                logger.info("Client disconnected")
            except Exception as e:
                logger.error(f"Error writing to Docker: {e}")
        
        # Run both tasks concurrently
        await asyncio.gather(
            read_from_docker(),
            write_to_docker(),
            return_exceptions=True
        )
        
    except Exception as e:
        logger.error(f"Exec session error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Exec session error: {str(e)}"
            })
        except:
            pass
    finally:
        # Clean up
        try:
            if 'ws_response' in locals() and not ws_response.closed:
                await ws_response.close()
        except:
            pass
        
        try:
            await websocket.close()
        except:
            pass
        
        logger.info(f"Exec session ended for container {container_id}")