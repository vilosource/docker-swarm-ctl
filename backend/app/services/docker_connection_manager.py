import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import docker
from docker.client import DockerClient
from docker.errors import DockerException, APIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import DockerConnectionError, AuthorizationError
from app.models import DockerHost, UserHostPermission, User, UserRole, HostCredential
from app.services.encryption import get_encryption_service
from app.core.logging import logger


class DockerConnectionManager:
    """Manages Docker client connections for multiple hosts"""
    
    def __init__(self):
        self._connections: Dict[str, DockerClient] = {}
        self._connection_pools: Dict[str, asyncio.Queue] = {}
        self._health_checks: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self._max_connections_per_host = 10
        self._health_check_interval = timedelta(minutes=5)
        self._encryption = get_encryption_service()
    
    async def get_client(
        self,
        host_id: str,
        user: User,
        db: AsyncSession
    ) -> DockerClient:
        """
        Get Docker client for specific host with permission check
        
        Args:
            host_id: UUID of the Docker host
            user: Current user making the request
            db: Database session
            
        Returns:
            DockerClient instance
            
        Raises:
            AuthorizationError: If user doesn't have access to the host
            DockerConnectionError: If connection fails
        """
        # Check user permissions
        await self._check_permissions(host_id, user, db)
        
        # Get or create connection
        if host_id not in self._connections:
            async with self._lock:
                if host_id not in self._connections:
                    await self._create_connection(host_id, db)
        
        # Check if connection needs health check
        if await self._needs_health_check(host_id):
            await self._perform_health_check(host_id)
        
        return self._connections[host_id]
    
    async def _check_permissions(
        self,
        host_id: str,
        user: User,
        db: AsyncSession
    ) -> None:
        """Check if user has permission to access the host"""
        # Admin users have access to all hosts
        if user.role == UserRole.admin:
            return
        
        # Check specific host permission
        result = await db.execute(
            select(UserHostPermission).where(
                UserHostPermission.user_id == user.id,
                UserHostPermission.host_id == host_id
            )
        )
        permission = result.scalar_one_or_none()
        
        if not permission:
            raise AuthorizationError(
                f"You don't have permission to access this Docker host"
            )
    
    async def _get_host_config(
        self,
        host_id: str,
        db: AsyncSession
    ) -> DockerHost:
        """Get host configuration from database"""
        result = await db.execute(
            select(DockerHost).where(
                DockerHost.id == host_id,
                DockerHost.is_active == True
            )
        )
        host = result.scalar_one_or_none()
        
        if not host:
            raise DockerConnectionError(f"Docker host {host_id} not found or inactive")
        
        return host
    
    async def _get_credentials(
        self,
        host_id: str,
        db: AsyncSession
    ) -> Dict[str, str]:
        """Get and decrypt host credentials"""
        result = await db.execute(
            select(HostCredential).where(
                HostCredential.host_id == host_id
            )
        )
        credentials = result.scalars().all()
        
        decrypted_creds = {}
        for cred in credentials:
            decrypted_creds[cred.credential_type] = self._encryption.decrypt(
                cred.encrypted_value
            )
        
        return decrypted_creds
    
    async def _create_connection(
        self,
        host_id: str,
        db: AsyncSession
    ) -> None:
        """Create new Docker connection"""
        host = await self._get_host_config(host_id, db)
        credentials = await self._get_credentials(host_id, db)
        
        try:
            if host.connection_type == "unix":
                client = docker.DockerClient(base_url=host.host_url)
            
            elif host.connection_type == "tcp":
                # Build TLS configuration if credentials exist
                tls_config = None
                if "tls_cert" in credentials and "tls_key" in credentials:
                    tls_config = docker.tls.TLSConfig(
                        client_cert=(
                            credentials.get("tls_cert"),
                            credentials.get("tls_key")
                        ),
                        ca_cert=credentials.get("tls_ca"),
                        verify=True if credentials.get("tls_ca") else False
                    )
                
                client = docker.DockerClient(
                    base_url=host.host_url,
                    tls=tls_config
                )
            
            elif host.connection_type == "ssh":
                # SSH connection support (requires paramiko)
                # For now, we'll use the standard Docker client
                # In production, use docker-py's SSH support
                client = docker.DockerClient(base_url=host.host_url)
            
            else:
                raise DockerConnectionError(
                    f"Unsupported connection type: {host.connection_type}"
                )
            
            # Test connection
            client.ping()
            
            # Store connection
            self._connections[host_id] = client
            self._health_checks[host_id] = datetime.utcnow()
            
            # Update host status
            await self._update_host_status(host_id, "healthy", db)
            
            logger.info(f"Successfully connected to Docker host {host.name} ({host_id})")
            
        except Exception as e:
            logger.error(f"Failed to connect to Docker host {host.name}: {str(e)}")
            await self._update_host_status(host_id, "unhealthy", db, error=str(e))
            raise DockerConnectionError(f"Failed to connect to Docker host: {str(e)}")
    
    async def _needs_health_check(self, host_id: str) -> bool:
        """Check if connection needs health check"""
        if host_id not in self._health_checks:
            return True
        
        last_check = self._health_checks[host_id]
        return datetime.utcnow() - last_check > self._health_check_interval
    
    async def _perform_health_check(self, host_id: str) -> None:
        """Perform health check on connection"""
        try:
            client = self._connections[host_id]
            client.ping()
            self._health_checks[host_id] = datetime.utcnow()
        except Exception as e:
            logger.warning(f"Health check failed for host {host_id}: {str(e)}")
            # Remove failed connection
            self._connections.pop(host_id, None)
            raise DockerConnectionError(f"Docker host health check failed: {str(e)}")
    
    async def _update_host_status(
        self,
        host_id: str,
        status: str,
        db: AsyncSession,
        error: Optional[str] = None
    ) -> None:
        """Update host status in database"""
        # This is a simplified version - in production, use proper async updates
        result = await db.execute(
            select(DockerHost).where(DockerHost.id == host_id)
        )
        host = result.scalar_one_or_none()
        
        if host:
            host.status = status
            host.last_health_check = datetime.utcnow()
            if error:
                # Store error in connection stats
                pass
            await db.commit()
    
    async def close_connection(self, host_id: str) -> None:
        """Close connection to specific host"""
        if host_id in self._connections:
            try:
                self._connections[host_id].close()
            except Exception as e:
                logger.error(f"Error closing connection to {host_id}: {str(e)}")
            finally:
                self._connections.pop(host_id, None)
                self._health_checks.pop(host_id, None)
    
    async def close_all(self) -> None:
        """Close all connections"""
        host_ids = list(self._connections.keys())
        for host_id in host_ids:
            await self.close_connection(host_id)
    
    async def get_default_host_id(
        self,
        db: AsyncSession,
        user: User
    ) -> Optional[str]:
        """Get the default host ID for a user"""
        # First, try to get the host marked as default
        result = await db.execute(
            select(DockerHost).where(
                DockerHost.is_default == True,
                DockerHost.is_active == True
            )
        )
        default_host = result.scalar_one_or_none()
        
        if default_host:
            # Check if user has access
            try:
                await self._check_permissions(str(default_host.id), user, db)
                return str(default_host.id)
            except AuthorizationError:
                pass
        
        # If no default or no access, get first accessible host
        if user.role == UserRole.admin:
            # Admin can access any active host
            result = await db.execute(
                select(DockerHost).where(
                    DockerHost.is_active == True
                ).limit(1)
            )
            host = result.scalar_one_or_none()
            return str(host.id) if host else None
        else:
            # Get first host user has permission to access
            result = await db.execute(
                select(UserHostPermission).where(
                    UserHostPermission.user_id == user.id
                ).limit(1)
            )
            permission = result.scalar_one_or_none()
            return str(permission.host_id) if permission else None


# Global instance
_connection_manager: Optional[DockerConnectionManager] = None


def get_docker_connection_manager() -> DockerConnectionManager:
    """Get or create the global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = DockerConnectionManager()
    return _connection_manager