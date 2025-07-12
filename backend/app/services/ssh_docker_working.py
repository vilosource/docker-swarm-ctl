"""
Working SSH Docker Connection

This implementation properly handles docker-py 7.0.0's SSH connection
by ensuring the SSH adapter is correctly configured.
"""

import os
import tempfile
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


class WorkingSSHDockerConnection:
    """
    SSH Docker connection that actually works with docker-py 7.0.0
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
        """Create Docker client with working SSH configuration"""
        # Import docker after patch is applied
        import docker
        from docker.client import DockerClient
        from docker.api import APIClient
        import paramiko
        
        docker_host_url = f"ssh://{self.ssh_user}@{self.ssh_host}:{self.ssh_port}"
        logger.info(f"Creating SSH connection to {docker_host_url}")
        
        temp_files = []
        
        try:
            # 1. First, verify we can connect via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.ssh_host,
                'port': self.ssh_port,
                'username': self.ssh_user,
                'timeout': 10
            }
            
            # Add SSH key if provided
            if 'ssh_private_key' in self.credentials:
                key_fd, key_path = tempfile.mkstemp(prefix='docker_ssh_key_', suffix='.pem')
                temp_files.append(key_path)
                os.write(key_fd, self.credentials['ssh_private_key'].encode())
                os.close(key_fd)
                os.chmod(key_path, 0o600)
                
                # Parse the key
                from io import StringIO
                key_str = self.credentials['ssh_private_key']
                
                # Try different key types
                pkey = None
                for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]:
                    try:
                        pkey = key_class.from_private_key(StringIO(key_str))
                        logger.info(f"Parsed SSH key as {key_class.__name__}")
                        break
                    except:
                        continue
                
                if pkey:
                    connect_kwargs['pkey'] = pkey
                else:
                    # Fall back to key file
                    connect_kwargs['key_filename'] = key_path
            
            logger.info(f"Testing SSH connection to {self.ssh_host}:{self.ssh_port}")
            ssh.connect(**connect_kwargs)
            
            # Test docker is available
            stdin, stdout, stderr = ssh.exec_command('docker version --format "{{.Server.Version}}"')
            docker_version = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            
            if error or not docker_version:
                ssh.close()
                raise SSHConnectionError(f"Docker not accessible via SSH: {error or 'No version returned'}")
            
            logger.info(f"Remote Docker version: {docker_version}")
            ssh.close()
            
            # 2. Now create the Docker client
            # The key insight is that docker-py expects to handle the SSH connection itself
            # We need to ensure our monkey patch is working
            
            # Set up SSH key in a way docker-py can use
            if 'ssh_private_key' in self.credentials and temp_files:
                # Create SSH config file
                config_fd, config_path = tempfile.mkstemp(prefix='ssh_config_')
                temp_files.append(config_path)
                
                with os.fdopen(config_fd, 'w') as f:
                    f.write(f"Host {self.ssh_host}\n")
                    f.write(f"    HostName {self.ssh_host}\n")
                    f.write(f"    User {self.ssh_user}\n")
                    f.write(f"    Port {self.ssh_port}\n")
                    f.write(f"    IdentityFile {key_path}\n")
                    f.write(f"    IdentitiesOnly yes\n")
                    f.write(f"    StrictHostKeyChecking no\n")
                    f.write(f"    UserKnownHostsFile /dev/null\n")
                
                # Set environment variable that paramiko might use
                os.environ['SSH_CONFIG_FILE'] = config_path
                
                # Also create a wrapper script for shell mode
                wrapper_fd, wrapper_path = tempfile.mkstemp(prefix='ssh_wrapper_', suffix='.sh')
                temp_files.append(wrapper_path)
                
                wrapper_content = f"""#!/bin/bash
exec ssh -F {config_path} "$@"
"""
                os.write(wrapper_fd, wrapper_content.encode())
                os.close(wrapper_fd)
                os.chmod(wrapper_path, 0o755)
                
                # Set SSH command for docker
                os.environ['DOCKER_SSH'] = wrapper_path
            
            # Create the client
            # Docker-py will create SSHHTTPAdapter internally
            client = DockerClient(
                base_url=docker_host_url,
                version='auto',
                timeout=60
            )
            
            # Test the connection
            client.ping()
            
            logger.info("Successfully connected to Docker via SSH")
            
            # Store temp files for cleanup
            client._ssh_temp_files = temp_files
            
            return client
            
        except Exception as e:
            # Cleanup on error
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            # Clean up environment
            os.environ.pop('SSH_CONFIG_FILE', None)
            os.environ.pop('DOCKER_SSH', None)
            
            if 'paramiko.ssh_exception.SSHException' in str(type(e)):
                raise SSHConnectionError(f"SSH authentication failed: {str(e)}")
            elif 'DockerException' in str(type(e)):
                raise SSHConnectionError(f"Docker connection failed: {str(e)}")
            else:
                raise SSHConnectionError(f"Unexpected error: {str(e)}")
    
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
        os.environ.pop('SSH_CONFIG_FILE', None)
        os.environ.pop('DOCKER_SSH', None)