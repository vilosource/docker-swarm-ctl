"""
SSH Tunnel Docker Connection

This implementation creates an SSH tunnel to the Docker daemon and then
connects using aiodocker through the tunnel.
"""

import os
import tempfile
import asyncio
import subprocess
from typing import Dict, Optional, TYPE_CHECKING
from urllib.parse import urlparse
import threading
import time

if TYPE_CHECKING:
    import aiodocker

from app.core.logging import logger
from app.core.exceptions import DockerConnectionError
from app.models import DockerHost


class SSHTunnelDockerConnection:
    """
    Docker connection via SSH tunnel using aiodocker
    """
    
    def __init__(self, host: DockerHost, credentials: Dict[str, str]):
        self.host = host
        self.credentials = credentials
        self.tunnel_process: Optional[subprocess.Popen] = None
        self.local_port: Optional[int] = None
        self.temp_files = []
        self._parse_ssh_url()
    
    def _parse_ssh_url(self):
        """Parse SSH URL from host configuration"""
        parsed = urlparse(self.host.host_url)
        
        if parsed.scheme != 'ssh':
            raise ValueError(f"Expected ssh:// URL, got {parsed.scheme}://")
        
        self.ssh_user = parsed.username or 'root'
        self.ssh_host = parsed.hostname
        self.ssh_port = parsed.port or 22
        self.docker_socket = '/var/run/docker.sock'  # Standard Docker socket path
    
    def _find_free_port(self) -> int:
        """Find a free local port for the tunnel"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def _create_ssh_tunnel(self) -> int:
        """Create SSH tunnel to Docker daemon"""
        self.local_port = self._find_free_port()
        
        # Create SSH key file if needed
        ssh_key_path = None
        if 'ssh_private_key' in self.credentials and self.credentials['ssh_private_key'].strip():
            key_fd, ssh_key_path = tempfile.mkstemp(prefix='docker_ssh_key_', suffix='.pem')
            self.temp_files.append(ssh_key_path)
            os.write(key_fd, self.credentials['ssh_private_key'].encode())
            os.close(key_fd)
            os.chmod(ssh_key_path, 0o600)
        
        # Build SSH tunnel command
        ssh_cmd = [
            'ssh',
            '-N',  # No remote command execution
            '-L', f'{self.local_port}:{self.docker_socket}',  # Local port forwarding
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=ERROR',
            '-o', 'ConnectTimeout=30',
            '-o', 'ServerAliveInterval=60',
            '-o', 'ServerAliveCountMax=3',
            '-p', str(self.ssh_port),
        ]
        
        if ssh_key_path:
            ssh_cmd.extend(['-i', ssh_key_path])
        
        ssh_cmd.append(f'{self.ssh_user}@{self.ssh_host}')
        
        logger.info(f"Creating SSH tunnel: local port {self.local_port} -> {self.ssh_host}:{self.docker_socket}")
        
        # Start SSH tunnel
        self.tunnel_process = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        
        # Wait a moment for tunnel to establish
        time.sleep(2)
        
        # Check if tunnel is working
        if self.tunnel_process.poll() is not None:
            stdout, stderr = self.tunnel_process.communicate()
            raise DockerConnectionError(f"SSH tunnel failed: {stderr.decode()}")
        
        return self.local_port
    
    async def create_client(self) -> 'aiodocker.Docker':
        """Create aiodocker client through SSH tunnel"""
        try:
            import aiodocker
        except ImportError:
            raise DockerConnectionError("aiodocker not installed. Run: pip install aiodocker")
        
        # Create SSH tunnel
        local_port = self._create_ssh_tunnel()
        
        # Create aiodocker client pointing to tunneled port
        docker_url = f"http://localhost:{local_port}"
        
        logger.info(f"Creating aiodocker client via tunnel: {docker_url}")
        
        client = aiodocker.Docker(url=docker_url)
        
        # Test the connection
        try:
            version_info = await client.version()
            logger.info(f"Connected via SSH tunnel to Docker {version_info.get('Version', 'Unknown')}")
        except Exception as e:
            await client.close()
            self._cleanup()
            raise DockerConnectionError(f"Failed to connect through SSH tunnel: {str(e)}")
        
        # Store cleanup info
        client._ssh_tunnel_process = self.tunnel_process
        client._ssh_temp_files = self.temp_files
        
        return client
    
    def _cleanup(self):
        """Clean up SSH tunnel and temporary files"""
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
                self.tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.tunnel_process.kill()
                self.tunnel_process.wait()
            self.tunnel_process = None
        
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        self.temp_files.clear()
    
    async def close(self, client: 'aiodocker.Docker'):
        """Close client and cleanup"""
        try:
            await client.close()
        except:
            pass
        
        # Cleanup tunnel
        if hasattr(client, '_ssh_tunnel_process') and client._ssh_tunnel_process:
            try:
                client._ssh_tunnel_process.terminate()
                client._ssh_tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                client._ssh_tunnel_process.kill()
                client._ssh_tunnel_process.wait()
        
        # Cleanup temp files
        if hasattr(client, '_ssh_temp_files'):
            for temp_file in client._ssh_temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)