"""
Simple SSH Docker Connection for docker-py 7.0.0

This implementation works around docker-py's SSH issues by using shell_out mode
and proper SSH configuration.
"""

import os
import tempfile
import subprocess
from typing import Dict, TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from docker.client import DockerClient

from app.core.logging import logger
from app.core.exceptions import DockerConnectionError
from app.models import DockerHost


class SSHConnectionError(DockerConnectionError):
    """SSH-specific connection error"""
    pass


class SimpleSSHDockerConnection:
    """
    Simple SSH Docker connection that works with docker-py 7.0.0
    Uses shell_out mode to avoid adapter registration issues.
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
        """Create Docker client using shell-out SSH mode"""
        # Import docker here to ensure any patches are applied
        import docker
        from docker.client import DockerClient
        
        temp_files = []
        
        try:
            # Test SSH connection first
            logger.info(f"Testing SSH connection to {self.ssh_host}:{self.ssh_port}")
            
            ssh_command = self._build_ssh_command(temp_files)
            
            # Test SSH connectivity
            test_cmd = [*ssh_command.split(), f"{self.ssh_user}@{self.ssh_host}", "echo", "test"]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise SSHConnectionError(f"SSH test failed: {result.stderr}")
            
            logger.info("SSH connection test successful")
            
            # Test Docker availability
            docker_test_cmd = [*ssh_command.split(), f"{self.ssh_user}@{self.ssh_host}", "docker", "version", "--format", "{{.Server.Version}}"]
            result = subprocess.run(docker_test_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise SSHConnectionError(f"Docker not accessible via SSH: {result.stderr}")
            
            docker_version = result.stdout.strip()
            logger.info(f"Remote Docker version: {docker_version}")
            
            # Set up environment for docker-py's use_ssh_client=True mode
            docker_host_url = f"ssh://{self.ssh_user}@{self.ssh_host}:{self.ssh_port}"
            
            # Create SSH config file that the system SSH client will use
            ssh_config_fd, ssh_config_path = tempfile.mkstemp(prefix='ssh_config_', suffix='.conf')
            temp_files.append(ssh_config_path)
            
            # Find the SSH key path
            key_path = None
            if 'ssh_private_key' in self.credentials and self.credentials['ssh_private_key'].strip():
                for tf in temp_files:
                    if tf.endswith('.pem'):
                        key_path = tf
                        break
            
            with os.fdopen(ssh_config_fd, 'w') as f:
                f.write(f"Host {self.ssh_host}\n")
                f.write(f"    HostName {self.ssh_host}\n")
                f.write(f"    User {self.ssh_user}\n")
                f.write(f"    Port {self.ssh_port}\n")
                f.write(f"    StrictHostKeyChecking no\n")
                f.write(f"    UserKnownHostsFile /dev/null\n")
                f.write(f"    LogLevel ERROR\n")
                f.write(f"    ConnectTimeout 30\n")
                f.write(f"    BatchMode yes\n")  # Non-interactive mode
                if key_path:
                    f.write(f"    IdentityFile {key_path}\n")
                    f.write(f"    IdentitiesOnly yes\n")
                    f.write(f"    PasswordAuthentication no\n")
                    f.write(f"    PubkeyAuthentication yes\n")
            
            logger.info(f"Created SSH config: {ssh_config_path}")
            
            # For use_ssh_client=True, docker-py will shell out to SSH
            # We need to make sure the SSH command uses our config file
            ssh_command_with_config = f"ssh -F {ssh_config_path}"
            os.environ['DOCKER_SSH_COMMAND'] = ssh_command_with_config
            
            logger.info(f"Set DOCKER_SSH_COMMAND: {ssh_command_with_config}")
            logger.info(f"Creating Docker client with use_ssh_client=True: {docker_host_url}")
            
            # Create client using docker-py's use_ssh_client parameter
            # This tells docker-py to shell out to the system SSH client
            client = DockerClient(
                base_url=docker_host_url,
                version='auto',
                timeout=120,
                use_ssh_client=True
            )
            
            # Test the connection
            try:
                client.ping()
                logger.info("Docker client ping successful")
            except Exception as e:
                logger.error(f"Docker ping failed: {e}")
                raise
            
            # Store temp files for cleanup
            client._ssh_temp_files = temp_files
            client._ssh_env_vars = ['DOCKER_SSH_COMMAND']
            
            return client
            
        except Exception as e:
            # Cleanup on error
            self._cleanup(temp_files)
            raise SSHConnectionError(f"Failed to create SSH Docker connection: {str(e)}")
    
    def _build_ssh_command(self, temp_files: list) -> str:
        """Build SSH command with proper authentication"""
        ssh_opts = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-o", "ConnectTimeout=30",
            "-p", str(self.ssh_port)
        ]
        
        # Add SSH key if provided
        if 'ssh_private_key' in self.credentials and self.credentials['ssh_private_key'].strip():
            key_fd, key_path = tempfile.mkstemp(prefix='docker_ssh_key_', suffix='.pem')
            temp_files.append(key_path)
            os.write(key_fd, self.credentials['ssh_private_key'].encode())
            os.close(key_fd)
            os.chmod(key_path, 0o600)
            
            ssh_opts.extend(["-i", key_path])
            # Force key-based auth only if we have a key
            ssh_opts.extend(["-o", "PasswordAuthentication=no"])
        else:
            # If no key provided, allow other auth methods
            logger.warning("No SSH private key provided, allowing other authentication methods")
            ssh_opts.extend(["-o", "PasswordAuthentication=yes"])
            ssh_opts.extend(["-o", "PubkeyAuthentication=no"])
        
        # Build command
        return f"ssh {' '.join(ssh_opts)}"
    
    def _cleanup(self, temp_files: list):
        """Clean up temporary files and environment"""
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        # Clean up environment
        os.environ.pop('DOCKER_SSH_COMMAND', None)
    
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
        
        # Clean up environment variables
        if hasattr(client, '_ssh_env_vars'):
            for env_var in client._ssh_env_vars:
                os.environ.pop(env_var, None)