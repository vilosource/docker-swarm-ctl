"""
Integration tests for WebSocket container handlers
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from fastapi import WebSocket
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.websocket.containers_refactored import (
    ContainerLogsHandler,
    ContainerStatsHandler
)
from app.models import User, UserRole
from app.services.docker_service import ContainerData


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.accepted = False
        self.closed = False
        self.sent_messages: List[Dict[str, Any]] = []
        self.receive_queue: asyncio.Queue = asyncio.Queue()
    
    async def accept(self):
        self.accepted = True
    
    async def send_json(self, data: dict):
        self.sent_messages.append(data)
    
    async def receive_json(self) -> dict:
        return await self.receive_queue.get()
    
    async def close(self):
        self.closed = True
    
    def add_message(self, message: dict):
        """Add a message to be received"""
        self.receive_queue.put_nowait(message)


class TestContainerLogsHandler:
    """Integration tests for container logs WebSocket handler"""
    
    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.role = UserRole.operator
        return user
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_websocket(self):
        return MockWebSocket()
    
    @pytest.fixture
    def mock_container(self):
        """Create a mock container with log stream"""
        container = Mock()
        container.name = "test-container"
        container.id = "abc123"
        
        # Mock log stream
        log_lines = [
            b"Starting application...\n",
            b"Server listening on port 8080\n",
            b"Connection established\n",
            b""  # End of stream
        ]
        
        stream = Mock()
        stream.read = Mock(side_effect=log_lines)
        stream.close = Mock()
        
        container.logs = Mock(return_value=stream)
        return container
    
    @pytest.mark.asyncio
    async def test_container_logs_streaming(
        self,
        mock_websocket,
        mock_user,
        mock_db,
        mock_container
    ):
        """Test streaming container logs"""
        # Create handler
        handler = ContainerLogsHandler(
            websocket=mock_websocket,
            user=mock_user,
            db=mock_db,
            container_id="abc123"
        )
        
        # Mock Docker service
        mock_docker_service = Mock()
        container_data = ContainerData(mock_container)
        mock_docker_service.get_container = AsyncMock(return_value=container_data)
        
        with patch.object(handler, 'docker_service', mock_docker_service):
            # Connect
            await handler.on_connect()
            
            # Start streaming
            with patch('asyncio.to_thread', side_effect=lambda f, *args: f(*args)):
                await handler.start_log_stream({
                    "lines": 10,
                    "follow": False,
                    "timestamps": False
                })
        
        # Verify messages sent
        messages = mock_websocket.sent_messages
        
        # Should have connection message
        assert any(msg["type"] == "connected" for msg in messages)
        
        # Should have log messages
        log_messages = [msg for msg in messages if msg["type"] == "log"]
        assert len(log_messages) == 3
        assert log_messages[0]["data"]["line"] == "Starting application..."
        assert log_messages[1]["data"]["line"] == "Server listening on port 8080"
        assert log_messages[2]["data"]["line"] == "Connection established"
        
        # Should have stream end message
        assert any(
            msg["type"] == "stream_end" and msg["data"]["total_lines"] == 3
            for msg in messages
        )
    
    @pytest.mark.asyncio
    async def test_self_monitoring_filtering(
        self,
        mock_websocket,
        mock_user,
        mock_db
    ):
        """Test that self-monitoring messages are filtered"""
        # Create handler
        handler = ContainerLogsHandler(
            websocket=mock_websocket,
            user=mock_user,
            db=mock_db,
            container_id="abc123"
        )
        
        # Mock container with self-monitoring name
        mock_container = Mock()
        mock_container.name = "docker-swarm-ctl-backend"
        mock_container.id = "abc123"
        
        # Mock log stream with self-monitoring messages
        log_lines = [
            b"Regular application log\n",
            b"WebSocket connected: admin\n",  # Should be filtered
            b"Starting log stream\n",  # Should be filtered
            b"Another regular log\n",
            b""
        ]
        
        stream = Mock()
        stream.read = Mock(side_effect=log_lines)
        stream.close = Mock()
        mock_container.logs = Mock(return_value=stream)
        
        # Mock Docker service
        mock_docker_service = Mock()
        container_data = ContainerData(mock_container)
        mock_docker_service.get_container = AsyncMock(return_value=container_data)
        
        with patch.object(handler, 'docker_service', mock_docker_service):
            await handler.on_connect()
            
            with patch('asyncio.to_thread', side_effect=lambda f, *args: f(*args)):
                await handler.start_log_stream({"lines": 10, "follow": False})
        
        # Verify only non-filtered messages sent
        log_messages = [
            msg for msg in mock_websocket.sent_messages
            if msg["type"] == "log"
        ]
        assert len(log_messages) == 2
        assert log_messages[0]["data"]["line"] == "Regular application log"
        assert log_messages[1]["data"]["line"] == "Another regular log"
    
    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        mock_websocket,
        mock_user,
        mock_db
    ):
        """Test error handling when container not found"""
        handler = ContainerLogsHandler(
            websocket=mock_websocket,
            user=mock_user,
            db=mock_db,
            container_id="nonexistent"
        )
        
        # Mock Docker service that throws error
        mock_docker_service = Mock()
        mock_docker_service.get_container = AsyncMock(
            side_effect=Exception("Container not found")
        )
        
        with patch.object(handler, 'docker_service', mock_docker_service):
            await handler.on_connect()
            await handler.start_log_stream({})
        
        # Should send error message
        error_messages = [
            msg for msg in mock_websocket.sent_messages
            if msg["type"] == "error"
        ]
        assert len(error_messages) == 1
        assert "not found" in error_messages[0]["data"]["message"]


class TestContainerStatsHandler:
    """Integration tests for container stats WebSocket handler"""
    
    @pytest.fixture
    def mock_stats_data(self):
        """Create mock stats data"""
        return {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 1000000},
                "system_cpu_usage": 2000000
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 900000},
                "system_cpu_usage": 1900000
            },
            "memory_stats": {
                "usage": 104857600,  # 100 MB
                "limit": 1073741824  # 1 GB
            },
            "networks": {
                "eth0": {"rx_bytes": 1000, "tx_bytes": 2000}
            },
            "blkio_stats": {
                "io_service_bytes_recursive": [
                    {"op": "Read", "value": 5000},
                    {"op": "Write", "value": 3000}
                ]
            },
            "pids_stats": {"current": 10}
        }
    
    @pytest.fixture
    def mock_container_with_stats(self, mock_stats_data):
        """Create mock container with stats stream"""
        container = Mock()
        container.name = "test-container"
        container.id = "abc123"
        
        # Mock stats stream
        stats_lines = [
            json.dumps(mock_stats_data).encode(),
            b""  # End stream
        ]
        
        stream = Mock()
        stream.read = Mock(side_effect=stats_lines)
        stream.close = Mock()
        
        container.stats = Mock(return_value=stream)
        return container
    
    @pytest.mark.asyncio
    async def test_container_stats_streaming(
        self,
        mock_websocket,
        mock_user,
        mock_db,
        mock_container_with_stats
    ):
        """Test streaming container stats"""
        handler = ContainerStatsHandler(
            websocket=mock_websocket,
            user=mock_user,
            db=mock_db,
            container_id="abc123"
        )
        
        # Mock Docker service
        mock_docker_service = Mock()
        container_data = ContainerData(mock_container_with_stats)
        mock_docker_service.get_container = AsyncMock(return_value=container_data)
        
        with patch.object(handler, 'docker_service', mock_docker_service):
            await handler.on_connect()
            
            with patch('asyncio.to_thread', side_effect=lambda f, *args: f(*args)):
                await handler.start_stats_stream({"interval": 1.0})
        
        # Verify stats message sent
        stats_messages = [
            msg for msg in mock_websocket.sent_messages
            if msg["type"] == "stats"
        ]
        
        assert len(stats_messages) == 1
        stats = stats_messages[0]["data"]["stats"]
        
        # Verify calculated stats
        assert "cpu_percent" in stats
        assert "memory_usage" in stats
        assert "memory_percent" in stats
        assert stats["memory_usage"] == 104857600
        assert stats["network_rx"] == 1000
        assert stats["network_tx"] == 2000
    
    @pytest.mark.asyncio
    async def test_stop_stats_stream(
        self,
        mock_websocket,
        mock_user,
        mock_db
    ):
        """Test stopping stats stream"""
        handler = ContainerStatsHandler(
            websocket=mock_websocket,
            user=mock_user,
            db=mock_db,
            container_id="abc123"
        )
        
        await handler.on_connect()
        
        # Simulate some updates sent
        handler.updates_sent = 5
        
        # Stop stream
        await handler.stop_stats_stream()
        
        # Verify stop message
        stop_messages = [
            msg for msg in mock_websocket.sent_messages
            if msg["type"] == "stream_stopped"
        ]
        assert len(stop_messages) == 1
        assert stop_messages[0]["data"]["updates_sent"] == 5


class TestWebSocketMessageHandling:
    """Test WebSocket message handling"""
    
    @pytest.mark.asyncio
    async def test_ping_pong(self, mock_websocket, mock_user, mock_db):
        """Test ping/pong message handling"""
        handler = ContainerLogsHandler(
            websocket=mock_websocket,
            user=mock_user,
            db=mock_db,
            container_id="abc123"
        )
        
        await handler.handle_message({"type": "ping"})
        
        # Should respond with pong
        pong_messages = [
            msg for msg in mock_websocket.sent_messages
            if msg["type"] == "pong"
        ]
        assert len(pong_messages) == 1
    
    @pytest.mark.asyncio
    async def test_unknown_message_type(self, mock_websocket, mock_user, mock_db):
        """Test handling of unknown message types"""
        handler = ContainerLogsHandler(
            websocket=mock_websocket,
            user=mock_user,
            db=mock_db,
            container_id="abc123"
        )
        
        await handler.handle_message({"type": "unknown_type"})
        
        # Should send error
        error_messages = [
            msg for msg in mock_websocket.sent_messages
            if msg["type"] == "error"
        ]
        assert len(error_messages) == 1
        assert "Unknown message type" in error_messages[0]["data"]["message"]