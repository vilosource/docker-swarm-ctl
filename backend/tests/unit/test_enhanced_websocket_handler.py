"""
Unit tests for Enhanced WebSocket Handler
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.websocket.enhanced_base_handler import (
    EnhancedWebSocketHandler,
    WebSocketState,
    ResourceType,
    ManagedResource
)
from app.models import User


class TestWebSocketState:
    """Test WebSocket state management"""
    
    @pytest.fixture
    def handler(self):
        """Create a mock handler for testing"""
        websocket = Mock(spec=WebSocket)
        user = Mock(spec=User)
        db = Mock(spec=AsyncSession)
        return EnhancedWebSocketHandler(
            websocket=websocket,
            user=user,
            db=db,
            resource_id="test-123",
            resource_type="test"
        )
    
    @pytest.mark.asyncio
    async def test_initial_state(self, handler):
        """Test initial state is CONNECTING"""
        assert handler.state == WebSocketState.CONNECTING
    
    @pytest.mark.asyncio
    async def test_valid_state_transitions(self, handler):
        """Test valid state transitions"""
        # CONNECTING -> CONNECTED
        await handler.set_state(WebSocketState.CONNECTED)
        assert handler.state == WebSocketState.CONNECTED
        
        # CONNECTED -> AUTHENTICATED
        await handler.set_state(WebSocketState.AUTHENTICATED)
        assert handler.state == WebSocketState.AUTHENTICATED
        
        # AUTHENTICATED -> STREAMING
        await handler.set_state(WebSocketState.STREAMING)
        assert handler.state == WebSocketState.STREAMING
        
        # STREAMING -> CLOSING
        await handler.set_state(WebSocketState.CLOSING)
        assert handler.state == WebSocketState.CLOSING
        
        # CLOSING -> CLOSED
        await handler.set_state(WebSocketState.CLOSED)
        assert handler.state == WebSocketState.CLOSED
    
    @pytest.mark.asyncio
    async def test_invalid_state_transitions(self, handler):
        """Test invalid state transitions raise error"""
        # Can't go from CONNECTING to STREAMING
        with pytest.raises(ValueError, match="Invalid state transition"):
            await handler.set_state(WebSocketState.STREAMING)
        
        # Set to valid state
        await handler.set_state(WebSocketState.CONNECTED)
        
        # Can't go backwards
        with pytest.raises(ValueError, match="Invalid state transition"):
            await handler.set_state(WebSocketState.CONNECTING)
    
    @pytest.mark.asyncio
    async def test_terminal_state(self, handler):
        """Test CLOSED is terminal state"""
        # Go to CLOSED
        await handler.set_state(WebSocketState.CONNECTED)
        await handler.set_state(WebSocketState.CLOSING)
        await handler.set_state(WebSocketState.CLOSED)
        
        # Can't transition from CLOSED
        with pytest.raises(ValueError, match="Invalid state transition"):
            await handler.set_state(WebSocketState.CONNECTING)


class TestResourceManagement:
    """Test resource management functionality"""
    
    @pytest.fixture
    def handler(self):
        websocket = Mock(spec=WebSocket)
        user = Mock(spec=User)
        db = Mock(spec=AsyncSession)
        return EnhancedWebSocketHandler(
            websocket=websocket,
            user=user,
            db=db,
            resource_id="test-123",
            resource_type="test"
        )
    
    @pytest.mark.asyncio
    async def test_add_and_cleanup_resource(self, handler):
        """Test adding and cleaning up resources"""
        # Create mock resource
        resource = Mock()
        resource.close = Mock()
        
        # Add resource
        handler.add_resource(
            ResourceType.DOCKER_STREAM,
            resource
        )
        
        assert len(handler._resources) == 1
        
        # Cleanup via context manager
        async with handler.managed_resources() as resources:
            pass
        
        # Resource should be cleaned up
        resource.close.assert_called_once()
        assert len(handler._resources) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_with_callback(self, handler):
        """Test cleanup with custom callback"""
        resource = Mock()
        cleanup_called = False
        
        async def cleanup_callback(res):
            nonlocal cleanup_called
            cleanup_called = True
            assert res == resource
        
        # Add resource with callback
        handler.add_resource(
            ResourceType.ASYNC_TASK,
            resource,
            cleanup_callback
        )
        
        # Cleanup
        async with handler.managed_resources():
            pass
        
        assert cleanup_called
    
    @pytest.mark.asyncio
    async def test_cleanup_async_task(self, handler):
        """Test cleanup of async task resources"""
        # Create mock task
        task = AsyncMock()
        task.cancel = Mock()
        task.done = Mock(return_value=False)
        
        # Add task resource
        handler.add_resource(ResourceType.ASYNC_TASK, task)
        
        # Cleanup
        async with handler.managed_resources():
            pass
        
        # Task should be cancelled
        task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_specific_resource(self, handler):
        """Test removing specific resource"""
        resource1 = Mock()
        resource1.close = Mock()
        resource2 = Mock()
        resource2.close = Mock()
        
        # Add resources
        handler.add_resource(ResourceType.DOCKER_STREAM, resource1)
        handler.add_resource(ResourceType.DOCKER_STREAM, resource2)
        
        assert len(handler._resources) == 2
        
        # Remove specific resource
        await handler.remove_resource(resource1)
        
        # Only resource1 should be cleaned up
        resource1.close.assert_called_once()
        resource2.close.assert_not_called()
        assert len(handler._resources) == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_order(self, handler):
        """Test resources are cleaned up in reverse order"""
        cleanup_order = []
        
        async def make_cleanup(name):
            async def cleanup(res):
                cleanup_order.append(name)
            return cleanup
        
        # Add resources
        handler.add_resource(
            ResourceType.DOCKER_STREAM,
            Mock(),
            await make_cleanup("first")
        )
        handler.add_resource(
            ResourceType.DOCKER_STREAM,
            Mock(),
            await make_cleanup("second")
        )
        handler.add_resource(
            ResourceType.DOCKER_STREAM,
            Mock(),
            await make_cleanup("third")
        )
        
        # Cleanup
        async with handler.managed_resources():
            pass
        
        # Should cleanup in reverse order
        assert cleanup_order == ["third", "second", "first"]


class TestMetricsAndHealth:
    """Test metrics tracking and health checks"""
    
    @pytest.fixture
    def handler(self):
        websocket = AsyncMock(spec=WebSocket)
        user = Mock(spec=User)
        db = Mock(spec=AsyncSession)
        return EnhancedWebSocketHandler(
            websocket=websocket,
            user=user,
            db=db,
            resource_id="test-123",
            resource_type="test"
        )
    
    def test_initial_metrics(self, handler):
        """Test initial metrics state"""
        metrics = handler.get_metrics()
        assert metrics["messages_sent"] == 0
        assert metrics["messages_received"] == 0
        assert metrics["errors"] == 0
        assert metrics["state"] == "connecting"
        assert metrics["active_resources"] == 0
        assert "duration" in metrics
    
    @pytest.mark.asyncio
    async def test_message_metrics(self, handler):
        """Test message counting"""
        # Mock parent class method
        with patch.object(handler.__class__.__bases__[0], 'send_message', new_callable=AsyncMock):
            await handler.send_message("test", {"data": "value"})
        
        with patch.object(handler.__class__.__bases__[0], 'handle_message', new_callable=AsyncMock):
            await handler.handle_message({"type": "test"})
        
        metrics = handler.get_metrics()
        assert metrics["messages_sent"] == 1
        assert metrics["messages_received"] == 1
    
    @pytest.mark.asyncio
    async def test_error_metrics(self, handler):
        """Test error counting"""
        async with handler.error_handling("test_operation"):
            pass  # No error
        
        try:
            async with handler.error_handling("test_operation"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        metrics = handler.get_metrics()
        assert metrics["errors"] == 1
    
    @pytest.mark.asyncio
    async def test_health_check_authenticated(self, handler):
        """Test health check in authenticated state"""
        await handler.set_state(WebSocketState.CONNECTED)
        await handler.set_state(WebSocketState.AUTHENTICATED)
        
        handler.websocket.send_json = AsyncMock()
        
        result = await handler.health_check()
        assert result is True
        handler.websocket.send_json.assert_called_with({"type": "ping"})
    
    @pytest.mark.asyncio
    async def test_health_check_not_ready(self, handler):
        """Test health check when not ready"""
        # Still in CONNECTING state
        result = await handler.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, handler):
        """Test health check with connection error"""
        await handler.set_state(WebSocketState.CONNECTED)
        await handler.set_state(WebSocketState.AUTHENTICATED)
        
        handler.websocket.send_json = AsyncMock(side_effect=Exception("Connection lost"))
        
        result = await handler.health_check()
        assert result is False


class TestGracefulShutdown:
    """Test graceful shutdown functionality"""
    
    @pytest.fixture
    def handler(self):
        websocket = AsyncMock(spec=WebSocket)
        user = Mock(spec=User)
        db = Mock(spec=AsyncSession)
        return EnhancedWebSocketHandler(
            websocket=websocket,
            user=user,
            db=db,
            resource_id="test-123",
            resource_type="test"
        )
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, handler):
        """Test graceful shutdown process"""
        # Set to streaming state
        await handler.set_state(WebSocketState.CONNECTED)
        await handler.set_state(WebSocketState.AUTHENTICATED)
        await handler.set_state(WebSocketState.STREAMING)
        
        # Add some resources
        resource = Mock()
        resource.close = Mock()
        handler.add_resource(ResourceType.DOCKER_STREAM, resource)
        
        # Mock send_message
        with patch.object(handler, 'send_message', new_callable=AsyncMock) as mock_send:
            await handler.graceful_shutdown("Test shutdown")
        
        # Verify shutdown sequence
        assert handler.state == WebSocketState.CLOSED
        mock_send.assert_called_with("shutdown", {"reason": "Test shutdown"})
        resource.close.assert_called_once()
        handler.websocket.close.assert_called_once()


class TestRetryMechanism:
    """Test retry and recovery functionality"""
    
    @pytest.fixture
    def handler(self):
        websocket = Mock(spec=WebSocket)
        user = Mock(spec=User)
        db = Mock(spec=AsyncSession)
        return EnhancedWebSocketHandler(
            websocket=websocket,
            user=user,
            db=db,
            resource_id="test-123",
            resource_type="test"
        )
    
    @pytest.mark.asyncio
    async def test_successful_operation(self, handler):
        """Test operation that succeeds on first try"""
        async def operation():
            return "success"
        
        result = await handler.run_with_recovery(operation)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_operation_with_retry(self, handler):
        """Test operation that fails then succeeds"""
        attempt_count = 0
        
        async def operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await handler.run_with_recovery(
                operation,
                max_retries=3,
                backoff=0.1
            )
        
        assert result == "success"
        assert attempt_count == 3
    
    @pytest.mark.asyncio
    async def test_operation_max_retries(self, handler):
        """Test operation that always fails"""
        attempt_count = 0
        
        async def operation():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Permanent error")
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Permanent error"):
                await handler.run_with_recovery(
                    operation,
                    max_retries=3,
                    backoff=0.1
                )
        
        assert attempt_count == 3