"""
Self-Monitoring Detection Service

This service detects when the application is trying to monitor its own container
to prevent feedback loops in logging and stats collection.
"""

import socket
from typing import Optional
from docker.models.containers import Container
from docker.client import DockerClient
from app.core.logging import logger


class SelfMonitoringDetector:
    """Service to detect self-monitoring scenarios"""
    
    # Container name patterns that indicate backend/API containers
    BACKEND_PATTERNS = [
        'backend',
        'api',
        'fastapi',
        'swarm-ctl-backend',
        'swarm-ctl_backend',
        'docker-swarm-ctl-backend',
        'docker-swarm-ctl_backend'
    ]
    
    # Service labels that indicate backend containers
    BACKEND_SERVICE_LABELS = ['backend', 'api']
    
    def __init__(self):
        """Initialize with current container hostname"""
        self._hostname = socket.gethostname()
        logger.info(f"SelfMonitoringDetector initialized with hostname: {self._hostname}")
    
    def is_self_monitoring(self, container_id: str, docker_client: DockerClient) -> bool:
        """
        Check if we're monitoring our own container
        
        Args:
            container_id: The container ID to check
            docker_client: Docker client instance
            
        Returns:
            True if monitoring self, False otherwise
        """
        try:
            # Quick check: ID prefix matching
            if self._check_id_match(container_id):
                logger.debug(f"Self-monitoring detected by ID match: {container_id}")
                return True
            
            # Get container details for deeper inspection
            container = self._get_container_safe(container_id, docker_client)
            if not container:
                return False
            
            # Check various indicators
            if self._check_hostname_match(container):
                logger.debug(f"Self-monitoring detected by hostname match: {container_id}")
                return True
            
            if self._check_name_patterns(container):
                logger.debug(f"Self-monitoring detected by name pattern: {container_id}")
                return True
            
            if self._check_service_labels(container):
                logger.debug(f"Self-monitoring detected by service label: {container_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking self-monitoring for {container_id}: {e}")
            # Err on the side of caution - assume not self-monitoring
            return False
    
    def _check_id_match(self, container_id: str) -> bool:
        """Check if container ID matches our hostname (common in Docker)"""
        # Containers often have their short ID as hostname
        return (
            self._hostname.startswith(container_id[:12]) or 
            container_id.startswith(self._hostname[:12])
        )
    
    def _get_container_safe(self, container_id: str, docker_client: DockerClient) -> Optional[Container]:
        """Safely get container object"""
        try:
            return docker_client.containers.get(container_id)
        except Exception:
            return None
    
    def _check_hostname_match(self, container: Container) -> bool:
        """Check if container hostname matches ours"""
        try:
            container_hostname = container.attrs.get('Config', {}).get('Hostname', '')
            return container_hostname == self._hostname
        except Exception:
            return False
    
    def _check_name_patterns(self, container: Container) -> bool:
        """Check if container name matches backend patterns"""
        try:
            container_name = container.name.lower()
            return any(pattern in container_name for pattern in self.BACKEND_PATTERNS)
        except Exception:
            return False
    
    def _check_service_labels(self, container: Container) -> bool:
        """Check if container has backend service labels"""
        try:
            labels = container.labels or {}
            service_name = labels.get('com.docker.compose.service', '').lower()
            return service_name in self.BACKEND_SERVICE_LABELS
        except Exception:
            return False
    
    def should_suppress_logs(self, container_id: str, docker_client: DockerClient) -> bool:
        """
        Determine if logs should be suppressed for a container
        
        This is an alias for is_self_monitoring but makes the intent clearer
        when used in logging contexts.
        """
        return self.is_self_monitoring(container_id, docker_client)


# Global instance
_detector = SelfMonitoringDetector()


def is_self_monitoring(container_id: str, docker_client: DockerClient) -> bool:
    """Check if monitoring own container (global function for backward compatibility)"""
    return _detector.is_self_monitoring(container_id, docker_client)


def should_suppress_logs(container_id: str, docker_client: DockerClient) -> bool:
    """Check if logs should be suppressed for a container"""
    return _detector.should_suppress_logs(container_id, docker_client)


async def is_self_monitoring_async(container_id: str, client) -> bool:
    """Async version for aiodocker clients - currently just returns False"""
    # TODO: Implement proper self-monitoring detection for aiodocker
    # For now, return False to avoid blocking functionality
    return False