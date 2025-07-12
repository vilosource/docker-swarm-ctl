"""
Fixed SSH Docker Connection

This implementation ensures docker-py properly uses SSH transport
without the "http+docker" error.
"""

import os
import tempfile
from typing import Dict, TYPE_CHECKING
from urllib.parse import urlparse

import paramiko

if TYPE_CHECKING:
    from docker.client import DockerClient

from app.core.logging import logger
from app.core.exceptions import DockerConnectionError
from app.models import DockerHost


class SSHConnectionError(DockerConnectionError):
    """SSH-specific connection error"""
    pass


class SSHDockerFixed:
    """
    Fixed SSH Docker connection that properly configures docker-py
    """
    
    def __init__(self, host: DockerHost, credentials: Dict[str, str]):
        self.host = host
        self.credentials = credentials
        self._parse_ssh_url()
    
    def _parse_ssh_url(self):
        """Parse SSH URL from host configuration"""
        parsed = urlparse(self.host.host_url)
        
        if parsed.scheme != 'ssh':
            raise ValueError(f"Expected ssh:// URL, got {parsed.scheme}://")
        
        self.ssh_user = parsed.username or 'root'
        self.ssh_host = parsed.hostname
        self.ssh_port = parsed.port or 22
    
    def create_client(self) -> 'DockerClient':
        """Create Docker client with proper SSH configuration"""
        # Import docker here to ensure patch is applied
        import docker
        from docker.client import DockerClient
        
        docker_host_url = f"ssh://{self.ssh_user}@{self.ssh_host}:{self.ssh_port}"
        
        # Create temporary files for SSH
        temp_files = []
        
        try:
            # Write SSH private key if provided
            if 'ssh_private_key' in self.credentials:
                key_fd, key_path = tempfile.mkstemp(prefix='docker_ssh_key_', suffix='.pem')
                temp_files.append(key_path)
                os.write(key_fd, self.credentials['ssh_private_key'].encode())
                os.close(key_fd)
                os.chmod(key_path, 0o600)
                
                # Set SSH key in environment
                os.environ['SSH_KEY_PATH'] = key_path
                
                # Also set up SSH command for shell mode
                ssh_command = f'ssh -i {key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
                os.environ['DOCKER_SSH_COMMAND'] = ssh_command
                os.environ['DOCKER_HOST'] = docker_host_url
                
                logger.info(f"Set DOCKER_SSH_COMMAND: {ssh_command}")
            
            logger.info(f"Creating Docker client for {docker_host_url}")
            
            # Method 1: Try with from_env() which should respect DOCKER_HOST
            try:
                client = docker.from_env(timeout=60)
                client.ping()
                logger.info("Successfully connected using from_env()")
                
                # Store temp files for cleanup
                client._ssh_temp_files = temp_files
                return client
                
            except Exception as e1:
                logger.warning(f"from_env() failed: {e1}")
                
                # Method 2: Try direct connection
                try:
                    client = DockerClient(
                        base_url=docker_host_url,
                        version='auto',
                        timeout=60
                    )
                    client.ping()
                    logger.info("Successfully connected using direct URL")
                    
                    # Store temp files for cleanup
                    client._ssh_temp_files = temp_files
                    return client
                    
                except Exception as e2:
                    logger.error(f"Direct connection failed: {e2}")
                    raise
                    
        except Exception as e:
            # Cleanup on error
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            # Clean up environment
            os.environ.pop('SSH_KEY_PATH', None)
            os.environ.pop('DOCKER_SSH_COMMAND', None)
            os.environ.pop('DOCKER_HOST', None)
            
            raise SSHConnectionError(f"SSH connection failed: {str(e)}")
    
    def close(self, client: 'DockerClient'):
        """Close client and cleanup"""
        try:
            client.close()
        except:
            pass
        
        # Cleanup temp files
        if hasattr(client, '_ssh_temp_files'):
            for temp_file in client._ssh_temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
        
        # Clean up environment
        os.environ.pop('SSH_KEY_PATH', None)
        os.environ.pop('DOCKER_SSH_COMMAND', None)
        os.environ.pop('DOCKER_HOST', None)