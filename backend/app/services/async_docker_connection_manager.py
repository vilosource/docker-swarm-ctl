import asyncio
from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Import aiodocker types only for type checking
if TYPE_CHECKING:
    import aiodocker

from app.core.exceptions import DockerConnectionError, AuthorizationError
from app.models import DockerHost, UserHostPermission, User, UserRole, HostCredential
from app.services.encryption import get_encryption_service
from app.core.logging import logger
from app.services.circuit_breaker import get_circuit_breaker_manager, CircuitBreakerConfig
from app.services.ssh_tunnel_docker import SSHTunnelDockerConnection


class AsyncDockerConnectionManager:
    """Async Docker client connections manager using aiodocker and SSH tunneling"""
    
    def __init__(self):
        self._connections: Dict[str, 'aiodocker.Docker'] = {}
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
    ) -> 'aiodocker.Docker':
        """
        Get async Docker client for specific host with permission check
        
        Args:
            host_id: UUID of the Docker host
            user: Current user making the request
            db: Database session
            
        Returns:
            aiodocker.Docker instance
            
        Raises:
            AuthorizationError: If user doesn't have access to the host
            DockerConnectionError: If connection fails
        """
        # Check user permissions
        await self._check_permissions(host_id, user, db)
        
        # Use circuit breaker for connection operations
        circuit_breaker = get_circuit_breaker_manager().get_or_create(
            f"docker-host-{host_id}",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
                expected_exception=DockerConnectionError,
                success_threshold=2
            )
        )
        
        async def _get_connection():
            # Get or create connection
            if host_id not in self._connections:
                async with self._lock:
                    if host_id not in self._connections:
                        await self._create_connection(host_id, db)
            
            # Check if connection needs health check
            if await self._needs_health_check(host_id):
                await self._perform_health_check(host_id)
            
            return self._connections[host_id]
        
        # Execute through circuit breaker
        return await circuit_breaker.call(_get_connection)
    
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
        """Create new async Docker connection"""
        host = await self._get_host_config(host_id, db)
        credentials = await self._get_credentials(host_id, db)
        
        try:
            # Convert enum to string if needed
            connection_type = host.connection_type.value if hasattr(host.connection_type, 'value') else host.connection_type
            
            if connection_type == "unix":
                import aiodocker
                client = aiodocker.Docker(url=host.host_url)
            
            elif connection_type == "tcp":
                import aiodocker
                # For TCP connections, we can use aiodocker directly
                # Note: TLS support would need to be implemented in aiodocker config
                client = aiodocker.Docker(url=host.host_url)
            
            elif connection_type == "ssh":
                # Use the SSH tunnel approach that we know works!
                ssh_tunnel = SSHTunnelDockerConnection(host, credentials)
                client = await ssh_tunnel.create_client()
                
                # Store the tunnel reference for cleanup
                client._ssh_tunnel_handler = ssh_tunnel
            
            else:
                raise DockerConnectionError(
                    f"Unsupported connection type: {connection_type}"
                )
            
            # Test connection
            version_info = await client.version()
            logger.info(f"Connected to Docker {version_info.get('Version', 'Unknown')} on {host.name}")
            
            # Store connection
            self._connections[host_id] = client
            self._health_checks[host_id] = datetime.utcnow()
            
            # Update host status
            await self._update_host_status(host_id, "healthy", db)
            
            logger.info(f"Successfully connected to async Docker host {host.name} ({host_id})")
            
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
            await client.version()  # Simple health check
            self._health_checks[host_id] = datetime.utcnow()
        except Exception as e:
            logger.warning(f"Health check failed for host {host_id}: {str(e)}")
            # Remove failed connection
            await self._cleanup_connection(host_id)
            raise DockerConnectionError(f"Docker host health check failed: {str(e)}")
    
    async def _update_host_status(
        self,
        host_id: str,
        status: str,
        db: AsyncSession,
        error: Optional[str] = None
    ) -> None:
        """Update host status in database"""
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
    
    async def _cleanup_connection(self, host_id: str) -> None:
        """Clean up a specific connection"""
        if host_id in self._connections:
            client = self._connections[host_id]
            
            try:
                # Handle SSH tunnel cleanup
                if hasattr(client, '_ssh_tunnel_handler'):
                    await client._ssh_tunnel_handler.close(client)
                else:
                    await client.close()
            except Exception as e:
                logger.error(f"Error closing connection to {host_id}: {str(e)}")
            finally:
                self._connections.pop(host_id, None)
                self._health_checks.pop(host_id, None)
    
    async def close_connection(self, host_id: str) -> None:
        """Close connection to specific host"""
        await self._cleanup_connection(host_id)
    
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
_async_connection_manager: Optional[AsyncDockerConnectionManager] = None


def get_async_docker_connection_manager() -> AsyncDockerConnectionManager:
    """Get or create the global async connection manager instance"""
    global _async_connection_manager
    if _async_connection_manager is None:
        _async_connection_manager = AsyncDockerConnectionManager()
    return _async_connection_manager