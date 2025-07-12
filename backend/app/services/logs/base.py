"""
Base classes and interfaces for the unified log streaming architecture.

This module defines the core abstractions that all log sources must implement,
ensuring consistency across different log types (container, service, host, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Optional, Dict, Any, List
from enum import Enum


class LogLevel(str, Enum):
    """Standard log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class LogSourceType(str, Enum):
    """Types of log sources"""
    CONTAINER = "container"
    SERVICE = "service"
    HOST_SYSTEM = "host_system"
    DOCKER_DAEMON = "docker_daemon"
    STACK = "stack"
    NODE = "node"
    TASK = "task"
    FILE = "file"
    AUDIT = "audit"


@dataclass
class LogEntry:
    """
    Standardized log entry that can represent logs from any source.
    
    This provides a consistent structure for all log types, making it easier
    to handle logs uniformly in the UI and backend.
    """
    timestamp: datetime
    source_type: LogSourceType
    source_id: str
    message: str
    level: Optional[LogLevel] = LogLevel.UNKNOWN
    host_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    structured_data: Optional[Dict[str, Any]] = None
    raw_line: Optional[str] = None  # Original log line before parsing


@dataclass
class LogSourceMetadata:
    """
    Metadata about a log source.
    
    This provides information about the capabilities and characteristics
    of a particular log source.
    """
    source_type: LogSourceType
    source_id: str
    name: str
    description: Optional[str] = None
    supports_follow: bool = True
    supports_tail: bool = True
    supports_timestamps: bool = True
    supports_filtering: bool = False
    supports_search: bool = False
    available_filters: List[str] = field(default_factory=list)
    host_id: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)


class LogSource(ABC):
    """
    Abstract base class for all log sources.
    
    This defines the interface that all log sources must implement,
    whether they're reading from Docker containers, system logs,
    files, or any other source.
    """
    
    @abstractmethod
    async def get_metadata(self, resource_id: str) -> LogSourceMetadata:
        """
        Get metadata about this log source.
        
        Args:
            resource_id: The ID of the resource (container, service, etc.)
            
        Returns:
            LogSourceMetadata describing the source
            
        Raises:
            ResourceNotFoundError: If the resource doesn't exist
        """
        pass
    
    @abstractmethod
    async def get_logs(
        self,
        resource_id: str,
        follow: bool = True,
        tail: Optional[int] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        timestamps: bool = True,
        **kwargs
    ) -> AsyncIterator[LogEntry]:
        """
        Get log stream for a resource.
        
        This is an async generator that yields LogEntry objects.
        It should handle the specifics of connecting to the log source
        and parsing the logs into the standard format.
        
        Args:
            resource_id: The ID of the resource to get logs from
            follow: Whether to follow/tail the logs
            tail: Number of lines to get from the end
            since: Get logs since this timestamp
            until: Get logs until this timestamp
            timestamps: Whether to include timestamps
            **kwargs: Additional source-specific options
            
        Yields:
            LogEntry objects
            
        Raises:
            ResourceNotFoundError: If the resource doesn't exist
            PermissionError: If access is denied
            ConnectionError: If connection to log source fails
        """
        pass
    
    @abstractmethod
    async def search_logs(
        self,
        resource_id: str,
        query: str,
        limit: Optional[int] = None,
        **kwargs
    ) -> List[LogEntry]:
        """
        Search logs for a specific query.
        
        This is optional and may not be supported by all sources.
        
        Args:
            resource_id: The ID of the resource
            query: Search query
            limit: Maximum number of results
            **kwargs: Additional search options
            
        Returns:
            List of matching LogEntry objects
            
        Raises:
            NotImplementedError: If search is not supported
            ResourceNotFoundError: If the resource doesn't exist
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support log search")
    
    @abstractmethod
    async def validate_access(self, resource_id: str, user: Any) -> bool:
        """
        Validate that the user has access to this log source.
        
        Args:
            resource_id: The ID of the resource
            user: The user object
            
        Returns:
            True if access is allowed, False otherwise
        """
        pass
    
    def parse_log_line(self, line: str, source_id: str) -> LogEntry:
        """
        Parse a raw log line into a LogEntry.
        
        This is a helper method that subclasses can override to provide
        custom parsing logic for their specific log format.
        
        Args:
            line: Raw log line
            source_id: ID of the source
            
        Returns:
            Parsed LogEntry
        """
        # Default implementation - can be overridden by subclasses
        return LogEntry(
            timestamp=datetime.utcnow(),
            source_type=self.get_source_type(),
            source_id=source_id,
            message=line.strip(),
            raw_line=line
        )
    
    @abstractmethod
    def get_source_type(self) -> LogSourceType:
        """Get the type of this log source."""
        pass