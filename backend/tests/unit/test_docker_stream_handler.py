"""
Unit tests for Docker Stream Handler
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.docker_stream_handler import (
    DockerStreamHandler,
    LogStreamProcessor,
    StatsStreamProcessor,
    StreamProcessor
)
from app.core.exceptions import DockerStreamError


class TestLogStreamProcessor:
    """Test cases for LogStreamProcessor"""
    
    @pytest.fixture
    def processor(self):
        return LogStreamProcessor(decode=True, timestamps=False)
    
    @pytest.mark.asyncio
    async def test_process_valid_log_data(self, processor):
        """Test processing valid log data"""
        # Docker log format: 8-byte header + content
        header = b'\x01\x00\x00\x00\x00\x00\x00\x0d'
        content = b'Hello, World!'
        data = header + content
        
        result = await processor.process(data)
        assert result == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_process_log_without_header(self, processor):
        """Test processing log data without Docker header"""
        data = b'Simple log line'
        result = await processor.process(data)
        assert result == "Simple log line"
    
    @pytest.mark.asyncio
    async def test_process_empty_data(self, processor):
        """Test processing empty data"""
        result = await processor.process(b'')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_with_newline(self, processor):
        """Test that newlines are stripped"""
        data = b'Log line with newline\n'
        result = await processor.process(data)
        assert result == "Log line with newline"
    
    @pytest.mark.asyncio
    async def test_process_binary_mode(self):
        """Test processing in binary mode (hex output)"""
        processor = LogStreamProcessor(decode=False)
        data = b'Binary data'
        result = await processor.process(data)
        assert result == data.hex()
    
    @pytest.mark.asyncio
    async def test_process_invalid_utf8(self, processor):
        """Test processing data with invalid UTF-8"""
        data = b'\x01\x00\x00\x00\x00\x00\x00\x04\xff\xfe\xfd\xfc'
        result = await processor.process(data)
        assert result is not None  # Should handle gracefully with replacement


class TestStatsStreamProcessor:
    """Test cases for StatsStreamProcessor"""
    
    @pytest.fixture
    def processor(self):
        return StatsStreamProcessor()
    
    @pytest.mark.asyncio
    async def test_process_valid_json(self, processor):
        """Test processing valid JSON stats"""
        stats_data = {
            "cpu_stats": {"cpu_usage": {"total_usage": 1000}},
            "memory_stats": {"usage": 1048576, "limit": 2097152}
        }
        data = json.dumps(stats_data).encode('utf-8')
        
        result = await processor.process(data)
        assert result == stats_data
    
    @pytest.mark.asyncio
    async def test_process_invalid_json(self, processor):
        """Test processing invalid JSON"""
        data = b'{"invalid": json}'
        result = await processor.process(data)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_empty_data(self, processor):
        """Test processing empty data"""
        result = await processor.process(b'')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_whitespace_only(self, processor):
        """Test processing whitespace-only data"""
        data = b'   \n   '
        result = await processor.process(data)
        assert result is None


class TestDockerStreamHandler:
    """Test cases for DockerStreamHandler"""
    
    @pytest.fixture
    def handler(self):
        return DockerStreamHandler(timeout=5.0)
    
    @pytest.fixture
    def mock_container(self):
        """Create a mock Docker container"""
        container = Mock()
        container.logs = Mock()
        container.stats = Mock()
        return container
    
    @pytest.fixture
    def mock_stream(self):
        """Create a mock stream object"""
        stream = Mock()
        stream.close = Mock()
        return stream
    
    @pytest.mark.asyncio
    async def test_managed_stream_cleanup(self, handler, mock_stream):
        """Test that managed_stream properly cleans up resources"""
        processor = Mock(spec=StreamProcessor)
        on_data = AsyncMock()
        
        # Test normal execution
        async with handler.managed_stream(mock_stream, processor, on_data):
            assert len(handler._active_streams) == 1
        
        # Stream should be closed
        mock_stream.close.assert_called_once()
        assert len(handler._active_streams) == 0
    
    @pytest.mark.asyncio
    async def test_managed_stream_exception_cleanup(self, handler, mock_stream):
        """Test cleanup when exception occurs in managed_stream"""
        processor = Mock(spec=StreamProcessor)
        on_data = AsyncMock()
        
        with pytest.raises(RuntimeError):
            async with handler.managed_stream(mock_stream, processor, on_data):
                raise RuntimeError("Test error")
        
        # Stream should still be closed
        mock_stream.close.assert_called_once()
        assert len(handler._active_streams) == 0
    
    @pytest.mark.asyncio
    async def test_process_log_stream(self, handler, mock_container):
        """Test processing log stream"""
        # Setup mock log stream
        log_lines = [b'Line 1\n', b'Line 2\n', b'']
        mock_stream = MagicMock()
        mock_stream.read = Mock(side_effect=log_lines)
        mock_stream.close = Mock()
        mock_container.logs.return_value = mock_stream
        
        # Track received logs
        received_logs = []
        async def on_log(line):
            received_logs.append(line)
        
        # Process logs
        with patch('asyncio.to_thread', side_effect=lambda f, *args: f(*args)):
            await handler.process_log_stream(
                container=mock_container,
                on_log=on_log,
                lines=10,
                follow=False,
                timestamps=False
            )
        
        # Verify
        assert len(received_logs) == 2
        assert received_logs[0] == "Line 1"
        assert received_logs[1] == "Line 2"
    
    @pytest.mark.asyncio
    async def test_process_stats_stream(self, handler, mock_container):
        """Test processing stats stream"""
        # Setup mock stats
        stats_data = {"cpu_stats": {"cpu_usage": {"total_usage": 1000}}}
        mock_container.stats.return_value = [json.dumps(stats_data)]
        
        # Track received stats
        received_stats = []
        async def on_stats(stats):
            received_stats.append(stats)
        
        # Process stats (non-streaming)
        await handler.process_stats_stream(
            container=mock_container,
            on_stats=on_stats,
            stream=False
        )
        
        # Verify
        assert len(received_stats) == 1
        assert received_stats[0] == stats_data
    
    @pytest.mark.asyncio
    async def test_stop_all_streams(self, handler):
        """Test stopping all active streams"""
        # Create mock tasks
        task1 = AsyncMock()
        task1.done.return_value = False
        task1.cancel = Mock()
        
        task2 = AsyncMock()
        task2.done.return_value = False
        task2.cancel = Mock()
        
        handler._active_streams = [task1, task2]
        
        # Stop all streams
        await handler.stop_all_streams()
        
        # Verify all tasks cancelled
        task1.cancel.assert_called_once()
        task2.cancel.assert_called_once()
        assert len(handler._active_streams) == 0
    
    @pytest.mark.asyncio
    async def test_stream_timeout(self, handler):
        """Test stream processing with timeout"""
        processor = Mock(spec=StreamProcessor)
        on_data = AsyncMock()
        
        # Mock stream that blocks
        mock_stream = Mock()
        mock_stream.read = Mock(side_effect=asyncio.TimeoutError)
        mock_stream.close = Mock()
        
        # Should handle timeout gracefully
        with patch('asyncio.to_thread', side_effect=asyncio.TimeoutError):
            async with handler.managed_stream(mock_stream, processor, on_data):
                pass  # Timeout should be caught internally
    
    def test_get_active_stream_count(self, handler):
        """Test counting active streams"""
        # Create mix of done and active tasks
        done_task = Mock()
        done_task.done.return_value = True
        
        active_task = Mock()
        active_task.done.return_value = False
        
        handler._active_streams = [done_task, active_task, active_task]
        
        count = handler.get_active_stream_count()
        assert count == 2