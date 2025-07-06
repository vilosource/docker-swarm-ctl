"""
Self-Monitoring Service

Centralized service for detecting and filtering self-monitoring containers
and their messages to prevent feedback loops.
"""

import re
from typing import Optional, Set
from functools import lru_cache

from app.core.logging import logger


class SelfMonitoringService:
    """
    Handles detection and filtering of self-monitoring containers
    
    This service prevents feedback loops by identifying containers that
    are part of the Docker Control Platform infrastructure.
    """
    
    # Patterns that identify self-monitoring containers
    SELF_MONITORING_PATTERNS = [
        "docker-swarm-ctl",
        "docker-control-platform",
        "dcp-"  # Common prefix for platform containers
    ]
    
    # Message patterns to filter from self-monitoring containers
    FILTER_PATTERNS = [
        r"WebSocket (connected|disconnected)",
        r"(Starting|Stopping) log stream",
        r"Self-monitoring container detected",
        r"Exec session (started|ended)",
        r"Stats collection (started|stopped)"
    ]
    
    def __init__(self):
        self._filter_regex = re.compile("|".join(self.FILTER_PATTERNS))
        self._monitored_containers: Set[str] = set()
    
    @lru_cache(maxsize=128)
    def is_self_monitoring(self, container_name: str) -> bool:
        """
        Check if a container is part of the self-monitoring infrastructure
        
        Args:
            container_name: Name of the container to check
            
        Returns:
            True if container is self-monitoring, False otherwise
        """
        if not container_name:
            return False
        
        # Check against known patterns
        container_lower = container_name.lower()
        is_monitoring = any(
            pattern in container_lower 
            for pattern in self.SELF_MONITORING_PATTERNS
        )
        
        if is_monitoring:
            self._monitored_containers.add(container_name)
            logger.debug(f"Self-monitoring container detected: {container_name}")
        
        return is_monitoring
    
    def should_filter_message(
        self, 
        message: str, 
        container_name: Optional[str] = None
    ) -> bool:
        """
        Determine if a message should be filtered out
        
        Args:
            message: The log message to check
            container_name: Optional container name for context
            
        Returns:
            True if message should be filtered, False otherwise
        """
        if not message:
            return False
        
        # Only filter messages from self-monitoring containers
        if container_name and not self.is_self_monitoring(container_name):
            return False
        
        # Check if message matches filter patterns
        return bool(self._filter_regex.search(message))
    
    def add_monitoring_pattern(self, pattern: str) -> None:
        """
        Add a new pattern for identifying self-monitoring containers
        
        Args:
            pattern: Pattern to add
        """
        if pattern not in self.SELF_MONITORING_PATTERNS:
            self.SELF_MONITORING_PATTERNS.append(pattern)
            # Clear cache to re-evaluate with new pattern
            self.is_self_monitoring.cache_clear()
    
    def add_filter_pattern(self, pattern: str) -> None:
        """
        Add a new message pattern to filter
        
        Args:
            pattern: Regex pattern to filter
        """
        if pattern not in self.FILTER_PATTERNS:
            self.FILTER_PATTERNS.append(pattern)
            self._filter_regex = re.compile("|".join(self.FILTER_PATTERNS))
    
    def get_monitored_containers(self) -> Set[str]:
        """
        Get set of containers identified as self-monitoring
        
        Returns:
            Set of container names
        """
        return self._monitored_containers.copy()
    
    def clear_cache(self) -> None:
        """Clear the container detection cache"""
        self.is_self_monitoring.cache_clear()
        self._monitored_containers.clear()


# Singleton instance
_self_monitoring_service = None


def get_self_monitoring_service() -> SelfMonitoringService:
    """Get or create the self-monitoring service singleton"""
    global _self_monitoring_service
    if _self_monitoring_service is None:
        _self_monitoring_service = SelfMonitoringService()
    return _self_monitoring_service