"""
SSH Host Setup Wizard Implementation

Handles the specific logic for setting up Docker hosts via SSH.
"""

import os
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend
import paramiko
from io import StringIO

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    WizardInstance, DockerHost, UserHostPermission,
    HostStatus, HostType, ConnectionType
)
from app.models.docker_host import HostCredential, HostTag
from app.services.encryption import get_encryption_service
from app.services.ssh_docker_connection import SSHDockerConnection
from app.core.exceptions import ValidationError, DockerConnectionError
from app.core.logging import logger


class SSHHostWizard:
    """Implementation of SSH host setup wizard logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.encryption = get_encryption_service()
    
    async def validate_step_data(self, wizard: WizardInstance, step_data: Dict[str, Any]) -> None:
        """Validate data for current step"""
        step_configs = {
            0: self._validate_connection_details,
            1: self._validate_authentication,
            2: lambda w, d: None,  # SSH test step has no input
            3: lambda w, d: None,  # Docker test step has no input
            4: self._validate_confirmation
        }
        
        validator = step_configs.get(wizard.current_step)
        if validator:
            validator(wizard, step_data)
    
    def _validate_connection_details(self, wizard: WizardInstance, data: Dict[str, Any]) -> None:
        """Validate connection details step"""
        required = ["host_url", "connection_name", "host_type"]
        for field in required:
            if field not in data or not data[field]:
                raise ValidationError(f"Field '{field}' is required")
        
        # Validate SSH URL format
        if not data["host_url"].startswith("ssh://"):
            raise ValidationError("Host URL must start with ssh://")
        
        # Validate port
        port = data.get("ssh_port", 22)
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValidationError("SSH port must be between 1 and 65535")
    
    def _validate_authentication(self, wizard: WizardInstance, data: Dict[str, Any]) -> None:
        """Validate authentication step"""
        if "auth_method" not in data:
            raise ValidationError("Authentication method is required")
        
        auth_method = data["auth_method"]
        
        if auth_method == "existing_key":
            if not data.get("private_key"):
                raise ValidationError("Private key is required")
        elif auth_method == "new_key":
            # Key will be generated, no validation needed
            pass
        elif auth_method == "password":
            if not data.get("password"):
                raise ValidationError("Password is required")
        else:
            raise ValidationError(f"Invalid authentication method: {auth_method}")
    
    def _validate_confirmation(self, wizard: WizardInstance, data: Dict[str, Any]) -> None:
        """Validate confirmation step"""
        # Optional validation for tags, etc.
        pass
    
    async def run_step_test(self, wizard: WizardInstance, test_type: str) -> Dict[str, Any]:
        """Run test for current step"""
        if wizard.current_step == 2 and test_type == "ssh":
            return await self._test_ssh_connection(wizard)
        elif wizard.current_step == 3 and test_type == "docker":
            return await self._test_docker_connection(wizard)
        else:
            raise ValidationError(f"Invalid test type '{test_type}' for step {wizard.current_step}")
    
    async def _test_ssh_connection(self, wizard: WizardInstance) -> Dict[str, Any]:
        """Test SSH connectivity"""
        try:
            # Get connection details from state
            host_url = wizard.state.get("host_url")
            ssh_port = wizard.state.get("ssh_port", 22)
            auth_method = wizard.state.get("auth_method")
            
            # Parse SSH URL
            import re
            match = re.match(r'ssh://(?:([^@]+)@)?([^:]+)(?::(\d+))?', host_url)
            if not match:
                raise ValidationError("Invalid SSH URL format")
            
            ssh_user = match.group(1) or "root"
            ssh_host = match.group(2)
            
            # Create SSH client
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Prepare connection parameters
            connect_kwargs = {
                "hostname": ssh_host,
                "port": ssh_port,
                "username": ssh_user,
                "timeout": 30
            }
            
            # Add authentication
            if auth_method == "existing_key" or auth_method == "new_key":
                private_key = wizard.state.get("private_key")
                if private_key:
                    key_file = StringIO(private_key)
                    passphrase = wizard.state.get("key_passphrase")
                    
                    # Try to load the key
                    try:
                        pkey = paramiko.Ed25519Key.from_private_key(key_file, password=passphrase)
                    except:
                        key_file.seek(0)
                        try:
                            pkey = paramiko.RSAKey.from_private_key(key_file, password=passphrase)
                        except:
                            key_file.seek(0)
                            try:
                                pkey = paramiko.ECDSAKey.from_private_key(key_file, password=passphrase)
                            except:
                                key_file.seek(0)
                                pkey = paramiko.DSSKey.from_private_key(key_file, password=passphrase)
                    
                    connect_kwargs["pkey"] = pkey
            elif auth_method == "password":
                connect_kwargs["password"] = wizard.state.get("password")
            
            # Connect
            ssh_client.connect(**connect_kwargs)
            
            # Get system information
            stdin, stdout, stderr = ssh_client.exec_command("uname -a")
            uname = stdout.read().decode().strip()
            
            stdin, stdout, stderr = ssh_client.exec_command("cat /etc/os-release 2>/dev/null || echo 'Unknown OS'")
            os_info = stdout.read().decode().strip()
            
            ssh_client.close()
            
            return {
                "success": True,
                "message": "SSH connection successful",
                "system_info": {
                    "uname": uname,
                    "os_info": os_info,
                    "ssh_user": ssh_user,
                    "ssh_host": ssh_host
                }
            }
            
        except paramiko.AuthenticationException as e:
            return {
                "success": False,
                "message": "SSH authentication failed",
                "error": str(e)
            }
        except paramiko.SSHException as e:
            return {
                "success": False,
                "message": "SSH connection failed",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"SSH test error: {e}")
            return {
                "success": False,
                "message": "Unexpected error during SSH test",
                "error": str(e)
            }
    
    async def _test_docker_connection(self, wizard: WizardInstance) -> Dict[str, Any]:
        """Test Docker API access via SSH"""
        try:
            # Create temporary host object for testing
            host = DockerHost(
                id=wizard.resource_id,
                name=wizard.state.get("connection_name"),
                host_url=wizard.state.get("host_url"),
                connection_type=ConnectionType.ssh
            )
            
            # Build credentials dict
            credentials = {}
            auth_method = wizard.state.get("auth_method")
            
            if auth_method in ["existing_key", "new_key"]:
                if wizard.state.get("private_key"):
                    credentials["ssh_private_key"] = wizard.state["private_key"]
                if wizard.state.get("key_passphrase"):
                    credentials["ssh_private_key_passphrase"] = wizard.state["key_passphrase"]
            elif auth_method == "password":
                if wizard.state.get("password"):
                    credentials["ssh_password"] = wizard.state["password"]
            
            # Test Docker connection
            ssh_handler = SSHDockerConnection(host, credentials)
            client = ssh_handler.create_client()
            
            # Get Docker info
            docker_info = client.info()
            docker_version = client.version()
            
            # Close connection
            client.close()
            
            return {
                "success": True,
                "message": "Docker API accessible via SSH",
                "docker_info": {
                    "version": docker_version.get("Version"),
                    "api_version": docker_version.get("ApiVersion"),
                    "os": docker_info.get("OperatingSystem"),
                    "architecture": docker_info.get("Architecture"),
                    "containers": docker_info.get("Containers"),
                    "images": docker_info.get("Images"),
                    "is_swarm": docker_info.get("Swarm", {}).get("LocalNodeState") == "active"
                }
            }
            
        except DockerConnectionError as e:
            return {
                "success": False,
                "message": "Docker connection failed",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Docker test error: {e}")
            return {
                "success": False,
                "message": "Unexpected error during Docker test",
                "error": str(e)
            }
    
    def generate_ssh_key_pair(self, comment: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate a new ED25519 SSH key pair
        
        Returns:
            Tuple of (private_key_str, public_key_str)
        """
        # Generate key
        private_key = ed25519.Ed25519PrivateKey.generate()
        
        # Get private key in PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Get public key in OpenSSH format
        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        )
        
        # Add comment if provided
        if comment:
            public_ssh_str = public_ssh.decode() + f" {comment}"
        else:
            public_ssh_str = public_ssh.decode()
        
        return private_pem.decode(), public_ssh_str
    
    async def complete_wizard(self, wizard: WizardInstance) -> Dict[str, Any]:
        """Complete the wizard and create the host"""
        try:
            # Extract data from wizard state
            state = wizard.state
            
            # Determine host type
            host_type = state.get("host_type", "standalone")
            if host_type == "swarm_manager":
                host_type = HostType.swarm_manager
            elif host_type == "swarm_worker":
                host_type = HostType.swarm_worker
            else:
                host_type = HostType.standalone
            
            # Create host
            host = DockerHost(
                name=state["connection_name"],
                display_name=state.get("display_name"),
                description=state.get("description"),
                host_type=host_type,
                connection_type=ConnectionType.ssh,
                host_url=state["host_url"],
                is_active=True,
                is_default=state.get("is_default", False),
                status=HostStatus.setup_pending  # Mark as setup_pending since wizard is completing
            )
            
            self.db.add(host)
            await self.db.flush()  # Get the host ID
            
            # Store credentials
            auth_method = state.get("auth_method")
            
            if auth_method in ["existing_key", "new_key"]:
                if state.get("private_key"):
                    cred = HostCredential(
                        host_id=host.id,
                        credential_type="ssh_private_key",
                        encrypted_value=self.encryption.encrypt(state["private_key"])
                    )
                    self.db.add(cred)
                
                if state.get("key_passphrase"):
                    cred = HostCredential(
                        host_id=host.id,
                        credential_type="ssh_private_key_passphrase",
                        encrypted_value=self.encryption.encrypt(state["key_passphrase"])
                    )
                    self.db.add(cred)
            
            elif auth_method == "password":
                if state.get("password"):
                    cred = HostCredential(
                        host_id=host.id,
                        credential_type="ssh_password",
                        encrypted_value=self.encryption.encrypt(state["password"])
                    )
                    self.db.add(cred)
            
            # Add user permission
            permission = UserHostPermission(
                user_id=wizard.user_id,
                host_id=host.id,
                permission_level="admin"
            )
            self.db.add(permission)
            
            # Add tags if provided
            tags = state.get("tags", [])
            for tag_name in tags:
                if tag_name:
                    tag = HostTag(
                        host_id=host.id,
                        tag_name=tag_name
                    )
                    self.db.add(tag)
            
            
            await self.db.commit()
            
            logger.info(f"Created SSH host {host.name} ({host.id}) via wizard")
            
            return {
                "resource_id": str(host.id),
                "resource_type": "docker_host",
                "host_name": host.name
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to complete SSH host wizard: {e}")
            raise


# Factory function
def get_ssh_host_wizard(db: AsyncSession) -> SSHHostWizard:
    """Get SSH host wizard instance"""
    return SSHHostWizard(db)