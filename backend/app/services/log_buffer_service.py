"""
Log Buffer Service

Centralized service for managing container log buffers with configurable
retention policies and memory management.
"""

from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
import time

from app.core.logging import logger
from app.core.config import settings


@dataclass
class LogEntry:
    """Represents a single log entry with metadata"""
    timestamp: datetime
    message: str
    source: str = "stdout"  # stdout or stderr
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "source": self.source
        }


@dataclass
class BufferStats:
    """Statistics for a log buffer"""
    size: int
    oldest_entry: Optional[datetime]
    newest_entry: Optional[datetime]
    total_entries_added: int
    total_entries_dropped: int


class LogBuffer:
    """Individual log buffer for a container"""
    
    def __init__(self, max_size: int = 1000):
        self.entries: deque[LogEntry] = deque(maxlen=max_size)
        self.max_size = max_size
        self.total_added = 0
        self.total_dropped = 0
        self.last_access = time.time()
    
    def add(self, message: str, timestamp: Optional[datetime] = None, source: str = "stdout"):
        """Add a log entry to the buffer"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Track if we're dropping entries
        if len(self.entries) >= self.max_size:
            self.total_dropped += 1
        
        entry = LogEntry(timestamp=timestamp, message=message, source=source)
        self.entries.append(entry)
        self.total_added += 1
        self.last_access = time.time()
    
    def get_recent(self, count: int, since: Optional[datetime] = None) -> List[LogEntry]:
        """Get recent log entries"""
        self.last_access = time.time()
        
        if since:
            # Filter entries after the given timestamp
            filtered = [e for e in self.entries if e.timestamp > since]
            return filtered[-count:] if count < len(filtered) else filtered
        
        return list(self.entries)[-count:]
    
    def get_stats(self) -> BufferStats:
        """Get buffer statistics"""
        oldest = self.entries[0].timestamp if self.entries else None
        newest = self.entries[-1].timestamp if self.entries else None
        
        return BufferStats(
            size=len(self.entries),
            oldest_entry=oldest,
            newest_entry=newest,
            total_entries_added=self.total_added,
            total_entries_dropped=self.total_dropped
        )
    
    def clear(self):
        """Clear the buffer"""
        self.entries.clear()
        self.total_dropped += len(self.entries)


class LogBufferService:
    """
    Centralized service for managing log buffers across containers
    
    Features:
    - Configurable buffer sizes
    - Automatic cleanup of old buffers
    - Memory usage monitoring
    - Buffer statistics
    """
    
    def __init__(
        self,
        default_buffer_size: int = 1000,
        max_total_buffers: int = 100,
        buffer_ttl_minutes: int = 60,
        cleanup_interval_minutes: int = 5
    ):
        self.buffers: Dict[str, LogBuffer] = {}
        self.default_buffer_size = default_buffer_size
        self.max_total_buffers = max_total_buffers
        self.buffer_ttl = timedelta(minutes=buffer_ttl_minutes)
        self.cleanup_interval = timedelta(minutes=cleanup_interval_minutes)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Load settings from config if available
        self.default_buffer_size = getattr(
            settings, 'LOG_BUFFER_SIZE', default_buffer_size
        )
        self.max_total_buffers = getattr(
            settings, 'MAX_LOG_BUFFERS', max_total_buffers
        )
    
    async def start(self):
        """Start the background cleanup task"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("LogBufferService started")
    
    async def stop(self):
        """Stop the background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("LogBufferService stopped")
    
    async def add_log(
        self,
        container_id: str,
        message: str,
        timestamp: Optional[datetime] = None,
        source: str = "stdout"
    ):
        """Add a log entry for a container"""
        async with self._lock:
            # Create buffer if it doesn't exist
            if container_id not in self.buffers:
                # Check if we're at capacity
                if len(self.buffers) >= self.max_total_buffers:
                    # Remove least recently used buffer
                    await self._evict_lru_buffer()
                
                self.buffers[container_id] = LogBuffer(self.default_buffer_size)
            
            # Add the log entry
            self.buffers[container_id].add(message, timestamp, source)
    
    async def add_logs_batch(
        self,
        container_id: str,
        messages: List[Tuple[str, Optional[datetime], str]]
    ):
        """Add multiple log entries at once"""
        async with self._lock:
            if container_id not in self.buffers:
                if len(self.buffers) >= self.max_total_buffers:
                    await self._evict_lru_buffer()
                self.buffers[container_id] = LogBuffer(self.default_buffer_size)
            
            buffer = self.buffers[container_id]
            for message, timestamp, source in messages:
                buffer.add(message, timestamp, source)
    
    async def get_logs(
        self,
        container_id: str,
        count: int = 100,
        since: Optional[datetime] = None
    ) -> List[LogEntry]:
        """Get recent logs for a container"""
        async with self._lock:
            if container_id not in self.buffers:
                return []
            
            return self.buffers[container_id].get_recent(count, since)
    
    async def get_logs_as_text(
        self,
        container_id: str,
        count: int = 100,
        since: Optional[datetime] = None,
        include_timestamps: bool = True
    ) -> List[str]:
        """Get logs as formatted text lines"""
        entries = await self.get_logs(container_id, count, since)
        
        result = []
        for entry in entries:
            if include_timestamps:
                line = f"{entry.timestamp.isoformat()} {entry.message}"
            else:
                line = entry.message
            result.append(line)
        
        return result
    
    async def clear_buffer(self, container_id: str):
        """Clear logs for a specific container"""
        async with self._lock:
            if container_id in self.buffers:
                self.buffers[container_id].clear()
    
    async def remove_buffer(self, container_id: str):
        """Remove buffer for a container entirely"""
        async with self._lock:
            self.buffers.pop(container_id, None)
    
    async def get_buffer_stats(self, container_id: str) -> Optional[BufferStats]:
        """Get statistics for a container's buffer"""
        async with self._lock:
            if container_id in self.buffers:
                return self.buffers[container_id].get_stats()
            return None
    
    async def get_all_stats(self) -> Dict[str, BufferStats]:
        """Get statistics for all buffers"""
        async with self._lock:
            return {
                container_id: buffer.get_stats()
                for container_id, buffer in self.buffers.items()
            }
    
    async def get_memory_usage(self) -> Dict[str, Any]:
        """Get estimated memory usage information"""
        async with self._lock:
            total_entries = sum(len(b.entries) for b in self.buffers.values())
            # Rough estimate: 200 bytes per log entry
            estimated_memory = total_entries * 200
            
            return {
                "buffer_count": len(self.buffers),
                "total_entries": total_entries,
                "estimated_memory_bytes": estimated_memory,
                "estimated_memory_mb": round(estimated_memory / 1024 / 1024, 2)
            }
    
    async def _evict_lru_buffer(self):
        """Evict least recently used buffer"""
        if not self.buffers:
            return
        
        # Find LRU buffer
        lru_container = min(
            self.buffers.keys(),
            key=lambda k: self.buffers[k].last_access
        )
        
        logger.info(f"Evicting LRU log buffer for container {lru_container}")
        del self.buffers[lru_container]
    
    async def _cleanup_loop(self):
        """Background task to clean up old buffers"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval.total_seconds())
                await self._cleanup_old_buffers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in log buffer cleanup: {e}")
    
    async def _cleanup_old_buffers(self):
        """Remove buffers that haven't been accessed recently"""
        async with self._lock:
            current_time = time.time()
            ttl_seconds = self.buffer_ttl.total_seconds()
            
            to_remove = []
            for container_id, buffer in self.buffers.items():
                if current_time - buffer.last_access > ttl_seconds:
                    to_remove.append(container_id)
            
            for container_id in to_remove:
                logger.info(f"Removing expired log buffer for container {container_id}")
                del self.buffers[container_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} expired log buffers")


# Global instance
_log_buffer_service = LogBufferService()


async def get_log_buffer_service() -> LogBufferService:
    """Get the global log buffer service instance"""
    # Ensure service is started
    if not _log_buffer_service._cleanup_task:
        await _log_buffer_service.start()
    return _log_buffer_service


# Convenience functions
async def add_container_log(
    container_id: str,
    message: str,
    timestamp: Optional[datetime] = None,
    source: str = "stdout"
):
    """Add a log entry for a container"""
    service = await get_log_buffer_service()
    await service.add_log(container_id, message, timestamp, source)


async def get_container_logs(
    container_id: str,
    count: int = 100,
    since: Optional[datetime] = None
) -> List[str]:
    """Get recent logs for a container"""
    service = await get_log_buffer_service()
    return await service.get_logs_as_text(container_id, count, since)