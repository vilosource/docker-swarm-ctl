"""
Docker Stream Handler

Provides abstraction for handling Docker streams (logs, stats, exec)
with automatic resource management and error handling.
"""

import asyncio
from typing import AsyncIterator, Callable, Optional, Any, TypeVar
from contextlib import asynccontextmanager
import json

from app.core.logging import logger
from app.core.exceptions import DockerStreamError


T = TypeVar('T')


class StreamProcessor:
    """Base class for processing different types of Docker streams"""
    
    async def process(self, data: bytes) -> Optional[Any]:
        """Process raw stream data"""
        raise NotImplementedError


class LogStreamProcessor(StreamProcessor):
    """Process Docker log streams"""
    
    def __init__(self, decode: bool = True, timestamps: bool = False):
        self.decode = decode
        self.timestamps = timestamps
    
    async def process(self, data: bytes) -> Optional[str]:
        """Process log data into string format"""
        if not data:
            return None
        
        try:
            if self.decode:
                # Docker log format includes 8-byte header
                if len(data) > 8:
                    return data[8:].decode('utf-8', errors='replace').rstrip('\n')
                return data.decode('utf-8', errors='replace').rstrip('\n')
            return data.hex()
        except Exception as e:
            logger.error(f"Error processing log data: {e}")
            return None


class StatsStreamProcessor(StreamProcessor):
    """Process Docker stats streams"""
    
    async def process(self, data: bytes) -> Optional[dict]:
        """Process stats data into dictionary format"""
        if not data:
            return None
        
        try:
            line = data.decode('utf-8').strip()
            if line:
                return json.loads(line)
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing stats JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing stats data: {e}")
            return None


class DockerStreamHandler:
    """
    Handles Docker streams with automatic resource management
    
    Provides unified interface for different types of Docker streams
    with proper cleanup and error handling.
    """
    
    def __init__(self, timeout: Optional[float] = None):
        self.timeout = timeout
        self._active_streams: list[asyncio.Task] = []
    
    @asynccontextmanager
    async def managed_stream(
        self,
        stream: Any,
        processor: StreamProcessor,
        on_data: Callable[[Any], asyncio.Future]
    ) -> AsyncIterator[None]:
        """
        Context manager for handling a Docker stream
        
        Args:
            stream: Docker stream object
            processor: StreamProcessor instance
            on_data: Callback for processed data
            
        Yields:
            None
        """
        task = None
        try:
            # Create task for stream processing
            task = asyncio.create_task(
                self._process_stream(stream, processor, on_data)
            )
            self._active_streams.append(task)
            
            yield
            
        finally:
            # Cleanup
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            if task in self._active_streams:
                self._active_streams.remove(task)
            
            # Close the stream
            try:
                if hasattr(stream, 'close'):
                    stream.close()
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
    
    async def _process_stream(
        self,
        stream: Any,
        processor: StreamProcessor,
        on_data: Callable[[Any], asyncio.Future]
    ) -> None:
        """
        Process a Docker stream
        
        Args:
            stream: Docker stream object
            processor: StreamProcessor instance
            on_data: Callback for processed data
        """
        try:
            while True:
                # Read from stream with timeout
                if self.timeout:
                    data = await asyncio.wait_for(
                        asyncio.to_thread(stream.read, 1024),
                        timeout=self.timeout
                    )
                else:
                    data = await asyncio.to_thread(stream.read, 1024)
                
                if not data:
                    break
                
                # Process data
                processed = await processor.process(data)
                if processed is not None:
                    await on_data(processed)
                    
        except asyncio.TimeoutError:
            logger.warning("Stream read timeout")
        except asyncio.CancelledError:
            logger.debug("Stream processing cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
            raise DockerStreamError(f"Stream processing failed: {e}")
    
    async def process_log_stream(
        self,
        container: Any,
        on_log: Callable[[str], asyncio.Future],
        lines: int = 100,
        follow: bool = True,
        timestamps: bool = False
    ) -> None:
        """
        Process container log stream
        
        Args:
            container: Docker container object
            on_log: Callback for each log line
            lines: Number of historical lines
            follow: Whether to follow logs
            timestamps: Include timestamps
        """
        processor = LogStreamProcessor(timestamps=timestamps)
        
        # Get log stream
        stream = container.logs(
            stream=True,
            follow=follow,
            tail=lines,
            timestamps=timestamps
        )
        
        async with self.managed_stream(stream, processor, on_log):
            # Stream is processed in background task
            while follow and any(not task.done() for task in self._active_streams):
                await asyncio.sleep(0.1)
    
    async def process_stats_stream(
        self,
        container: Any,
        on_stats: Callable[[dict], asyncio.Future],
        stream: bool = True
    ) -> None:
        """
        Process container stats stream
        
        Args:
            container: Docker container object
            on_stats: Callback for each stats update
            stream: Whether to stream stats
        """
        processor = StatsStreamProcessor()
        
        # Get stats stream
        stats_stream = container.stats(stream=stream, decode=True)
        
        if stream:
            async with self.managed_stream(stats_stream, processor, on_stats):
                # Stream is processed in background task
                while any(not task.done() for task in self._active_streams):
                    await asyncio.sleep(0.1)
        else:
            # Single stats read
            data = next(stats_stream)
            stats = await processor.process(data.encode())
            if stats:
                await on_stats(stats)
    
    async def stop_all_streams(self) -> None:
        """Stop all active streams"""
        for task in self._active_streams[:]:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._active_streams.clear()
    
    def get_active_stream_count(self) -> int:
        """Get count of active streams"""
        return len([t for t in self._active_streams if not t.done()])