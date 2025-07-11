"""
SSH Docker Connection Handler

Provides SSH-based connections to remote Docker daemons following
the existing patterns and SOLID principles of the codebase.
"""

import re
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse
import docker
from docker.client import DockerClient
import paramiko
import io

from app.core.exceptions import DockerConnectionError
from app.core.logging import logger
from app.models import DockerHost


class SSHConnectionError(DockerConnectionError):
    """SSH-specific connection error"""
    pass


class SSHAuthenticationError(SSHConnectionError):
    """SSH authentication failure"""
    pass


class SSHDockerConnection:
    """
    Handles SSH connections to Docker daemons.
    
    This class follows the existing patterns in the codebase:
    - Single Responsibility: Only handles SSH Docker connections
    - Dependency Injection: Receives configuration via constructor
    - Clear error handling with specific exceptions
    """
    
    def __init__(self, host_config: DockerHost, credentials: Dict[str, str]):
        """
        Initialize SSH connection handler.
        
        Args:
            host_config: DockerHost configuration
            credentials: Decrypted credentials dictionary
        """
        self.host = host_config
        self.credentials = credentials
        self.ssh_user = None
        self.ssh_host = None
        self.ssh_port = 22
        self._parse_ssh_url()
    
    def _parse_ssh_url(self) -> None:
        """
        Parse SSH URL to extract connection parameters.
        
        Expected format: ssh://[user@]host[:port]
        """
        try:
            # Parse the URL
            parsed = urlparse(self.host.host_url)
            
            if parsed.scheme != 'ssh':
                raise ValueError(f"Invalid SSH URL scheme: {parsed.scheme}")
            
            # Extract user if present
            if '@' in parsed.netloc:
                user_host = parsed.netloc.split('@')
                self.ssh_user = user_host[0]
                host_port = user_host[1]
            else:
                self.ssh_user = self.credentials.get('ssh_user', 'root')
                host_port = parsed.netloc
            
            # Extract host and port
            if ':' in host_port:
                self.ssh_host, port_str = host_port.split(':', 1)
                try:
                    self.ssh_port = int(port_str)
                except ValueError:
                    raise ValueError(f"Invalid SSH port: {port_str}")
            else:
                self.ssh_host = host_port
            
            if not self.ssh_host:
                raise ValueError("SSH host not specified in URL")
                
        except Exception as e:
            raise SSHConnectionError(f"Failed to parse SSH URL: {str(e)}")
    
    def _get_ssh_client(self) -> paramiko.SSHClient:
        """
        Create and configure SSH client.
        
        Returns:
            Configured paramiko SSH client
            
        Raises:
            SSHAuthenticationError: If authentication fails
            SSHConnectionError: If connection fails
        """
        ssh_client = paramiko.SSHClient()
        
        # Load system SSH config
        ssh_config = paramiko.SSHConfig()
        ssh_config_file = None
        use_ssh_config = self.credentials.get('use_ssh_config', 'true').lower() == 'true'
        
        if use_ssh_config:
            import os
            ssh_config_path = os.path.expanduser('~/.ssh/config')
            if os.path.exists(ssh_config_path):
                try:
                    with open(ssh_config_path, 'r') as f:
                        ssh_config.parse(f)
                    ssh_config_file = ssh_config.lookup(self.ssh_host)
                    logger.info(f"Loaded SSH config for host: {self.ssh_host}")
                except Exception as e:
                    logger.warning(f"Failed to load SSH config: {e}")
        
        # Handle host key verification
        if 'ssh_known_hosts' in self.credentials:
            # Load known hosts from credential
            known_hosts_content = self.credentials['ssh_known_hosts']
            ssh_client.get_host_keys().load(io.StringIO(known_hosts_content))
        else:
            # Try to load system known_hosts
            import os
            known_hosts_paths = [
                os.path.expanduser('~/.ssh/known_hosts'),
                '/etc/ssh/ssh_known_hosts'
            ]
            for path in known_hosts_paths:
                if os.path.exists(path):
                    try:
                        ssh_client.load_host_keys(path)
                        logger.info(f"Loaded known_hosts from: {path}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load known_hosts from {path}: {e}")
            
            # If still no host keys, auto-add (less secure)
            if not ssh_client.get_host_keys():
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                logger.warning("No known_hosts found, auto-adding host keys")
        
        try:
            # Determine connection parameters
            connect_kwargs = {
                'timeout': 30,
                'banner_timeout': 30
            }
            
            # Use SSH config if available
            if ssh_config_file:
                # Override with SSH config values
                connect_kwargs['hostname'] = ssh_config_file.get('hostname', self.ssh_host)
                connect_kwargs['port'] = int(ssh_config_file.get('port', self.ssh_port))
                connect_kwargs['username'] = ssh_config_file.get('user', self.ssh_user)
                
                # Handle ProxyCommand or ProxyJump
                if 'proxycommand' in ssh_config_file:
                    connect_kwargs['sock'] = paramiko.ProxyCommand(ssh_config_file['proxycommand'])
            else:
                # Use direct values
                connect_kwargs['hostname'] = self.ssh_host
                connect_kwargs['port'] = self.ssh_port
                connect_kwargs['username'] = self.ssh_user
            
            # Try key-based authentication first
            if 'ssh_private_key' in self.credentials:
                private_key_content = self.credentials['ssh_private_key']
                
                # Parse the private key
                try:
                    # Try different key formats
                    key = None
                    key_file = io.StringIO(private_key_content)
                    
                    # Get passphrase if provided
                    passphrase = self.credentials.get('ssh_private_key_passphrase')
                    
                    # Try RSA key
                    try:
                        key = paramiko.RSAKey.from_private_key(key_file, password=passphrase)
                    except:
                        key_file.seek(0)
                        # Try DSA key
                        try:
                            key = paramiko.DSSKey.from_private_key(key_file, password=passphrase)
                        except:
                            key_file.seek(0)
                            # Try ECDSA key
                            try:
                                key = paramiko.ECDSAKey.from_private_key(key_file, password=passphrase)
                            except:
                                key_file.seek(0)
                                # Try Ed25519 key
                                key = paramiko.Ed25519Key.from_private_key(key_file, password=passphrase)
                    
                    connect_kwargs['pkey'] = key
                    
                except Exception as e:
                    raise SSHAuthenticationError(f"Failed to parse SSH private key: {str(e)}")
            
            # Fall back to password authentication
            elif 'ssh_password' in self.credentials:
                connect_kwargs['password'] = self.credentials['ssh_password']
            else:
                # Try SSH agent and identity files from SSH config
                auth_methods = []
                
                # Check for SSH agent
                agent = paramiko.Agent()
                agent_keys = agent.get_keys()
                if agent_keys:
                    auth_methods.append("ssh-agent")
                    logger.info(f"Found {len(agent_keys)} keys in SSH agent")
                
                # Check for identity files in SSH config
                identity_files = []
                if ssh_config_file and 'identityfile' in ssh_config_file:
                    # SSH config can have multiple identity files
                    identity_file_entries = ssh_config_file['identityfile']
                    if isinstance(identity_file_entries, str):
                        identity_files = [identity_file_entries]
                    else:
                        identity_files = identity_file_entries
                    
                    # Expand paths
                    import os
                    identity_files = [os.path.expanduser(f) for f in identity_files]
                    identity_files = [f for f in identity_files if os.path.exists(f)]
                    
                    if identity_files:
                        auth_methods.append(f"identity files: {', '.join(identity_files)}")
                        logger.info(f"Found identity files: {identity_files}")
                
                # If no explicit auth method, try with paramiko's default behavior
                # which includes SSH agent and default identity files
                if not auth_methods:
                    # Also check default identity files
                    import os
                    default_keys = ['~/.ssh/id_rsa', '~/.ssh/id_dsa', '~/.ssh/id_ecdsa', '~/.ssh/id_ed25519']
                    for key_path in default_keys:
                        expanded_path = os.path.expanduser(key_path)
                        if os.path.exists(expanded_path):
                            identity_files.append(expanded_path)
                            auth_methods.append(f"default key: {key_path}")
                
                if not auth_methods:
                    raise SSHAuthenticationError(
                        "No SSH authentication method available. "
                        "Please provide either: private key, password, or configure SSH keys in ~/.ssh/"
                    )
                
                logger.info(f"Attempting SSH authentication with: {', '.join(auth_methods)}")
                
                # If we have identity files, explicitly load them
                if identity_files:
                    connect_kwargs['key_filename'] = identity_files
            
            # Connect
            ssh_client.connect(**connect_kwargs)
            
            return ssh_client
            
        except paramiko.AuthenticationException as e:
            raise SSHAuthenticationError(f"SSH authentication failed: {str(e)}")
        except paramiko.SSHException as e:
            raise SSHConnectionError(f"SSH connection failed: {str(e)}")
        except Exception as e:
            raise SSHConnectionError(f"Unexpected SSH error: {str(e)}")
    
    def create_client(self) -> DockerClient:
        """
        Create Docker client with SSH transport.
        
        Returns:
            Configured DockerClient instance
            
        Raises:
            SSHConnectionError: If connection fails
        """
        try:
            # Get SSH client
            ssh_client = self._get_ssh_client()
            
            # docker-py expects the SSH client to be passed via use_ssh_client parameter
            # The base_url should be in the format: ssh://user@host:port
            docker_host_url = f"ssh://{self.ssh_user}@{self.ssh_host}:{self.ssh_port}"
            
            # Create Docker client with SSH transport
            client = docker.DockerClient(
                base_url=docker_host_url,
                use_ssh_client=True,
                ssh_client=ssh_client
            )
            
            # Test the connection
            client.ping()
            
            logger.info(f"Successfully connected to Docker via SSH at {self.ssh_host}")
            
            return client
            
        except docker.errors.DockerException as e:
            # Close SSH connection if Docker connection fails
            if 'ssh_client' in locals():
                ssh_client.close()
            raise SSHConnectionError(f"Docker connection via SSH failed: {str(e)}")
        except Exception as e:
            # Ensure SSH connection is closed on any error
            if 'ssh_client' in locals():
                ssh_client.close()
            raise
    
    @staticmethod
    def validate_ssh_url(url: str) -> bool:
        """
        Validate SSH URL format.
        
        Args:
            url: SSH URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme == 'ssh' and
                bool(parsed.netloc) and
                # Ensure host is specified (with or without user)
                bool(re.match(r'^([^@]+@)?[^:]+(\:\d+)?$', parsed.netloc))
            )
        except:
            return False
    
    @staticmethod
    def get_required_credentials() -> list[str]:
        """
        Get list of credential types for SSH.
        
        Returns:
            List of credential type names
            
        Note: SSH authentication can work with:
        1. No credentials if using SSH config and agent/identity files
        2. Explicit private key
        3. Password
        """
        return [
            'ssh_private_key',  # Private key content (optional if using SSH config)
            'ssh_private_key_passphrase',  # For encrypted private keys
            'ssh_password',  # Password authentication
            'ssh_user',  # SSH username (optional, can be in URL or SSH config)
            'ssh_known_hosts',  # Known hosts content (optional, uses system's by default)
            'use_ssh_config'  # Whether to use ~/.ssh/config (default: true)
        ]
    
    @staticmethod
    def get_ssh_config_info() -> dict:
        """
        Get information about SSH configuration options.
        
        Returns:
            Dictionary with SSH config information
        """
        return {
            'authentication_methods': [
                'SSH Agent (automatic)',
                'SSH Config identity files (automatic)',
                'Default SSH keys (~/.ssh/id_*)',
                'Explicit private key credential',
                'Password credential'
            ],
            'config_support': [
                'Host aliases from ~/.ssh/config',
                'Identity files from SSH config',
                'ProxyCommand/ProxyJump support',
                'User and port from SSH config',
                'Known hosts from ~/.ssh/known_hosts'
            ],
            'minimal_setup': (
                'For minimal setup, just create a host with SSH URL '
                'and ensure your SSH keys are configured in ~/.ssh/'
            )
        }