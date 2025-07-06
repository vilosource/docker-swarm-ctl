"""
Unit tests for Self-Monitoring Service
"""

import pytest
from app.services.self_monitoring import SelfMonitoringService, get_self_monitoring_service


class TestSelfMonitoringService:
    """Test cases for SelfMonitoringService"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service instance"""
        return SelfMonitoringService()
    
    def test_singleton_pattern(self):
        """Test that get_self_monitoring_service returns singleton"""
        service1 = get_self_monitoring_service()
        service2 = get_self_monitoring_service()
        assert service1 is service2
    
    def test_is_self_monitoring_with_known_patterns(self, service):
        """Test detection of self-monitoring containers"""
        # Positive cases
        assert service.is_self_monitoring("docker-swarm-ctl-backend")
        assert service.is_self_monitoring("docker-control-platform-frontend")
        assert service.is_self_monitoring("dcp-nginx")
        assert service.is_self_monitoring("DOCKER-SWARM-CTL-REDIS")  # Case insensitive
        
        # Negative cases
        assert not service.is_self_monitoring("nginx")
        assert not service.is_self_monitoring("postgres")
        assert not service.is_self_monitoring("my-app")
        assert not service.is_self_monitoring("")
        assert not service.is_self_monitoring(None)
    
    def test_is_self_monitoring_caching(self, service):
        """Test that results are cached"""
        # First call
        result1 = service.is_self_monitoring("docker-swarm-ctl-test")
        
        # Modify patterns (shouldn't affect cached result)
        service.SELF_MONITORING_PATTERNS.append("never-match")
        
        # Second call should return cached result
        result2 = service.is_self_monitoring("docker-swarm-ctl-test")
        assert result1 == result2
        
        # Clear cache and test again
        service.clear_cache()
        result3 = service.is_self_monitoring("never-match-test")
        assert result3 is True  # Now matches the added pattern
    
    def test_should_filter_message(self, service):
        """Test message filtering logic"""
        # Test with self-monitoring container
        assert service.should_filter_message(
            "WebSocket connected: admin",
            "docker-swarm-ctl-backend"
        )
        assert service.should_filter_message(
            "Starting log stream for container xyz",
            "docker-swarm-ctl-backend"
        )
        assert service.should_filter_message(
            "Self-monitoring container detected",
            "docker-swarm-ctl-backend"
        )
        
        # Should not filter from non-monitoring containers
        assert not service.should_filter_message(
            "WebSocket connected: admin",
            "nginx"
        )
        
        # Should not filter non-matching messages
        assert not service.should_filter_message(
            "Regular application log",
            "docker-swarm-ctl-backend"
        )
        
        # Edge cases
        assert not service.should_filter_message("", "docker-swarm-ctl-backend")
        assert not service.should_filter_message(None, "docker-swarm-ctl-backend")
    
    def test_add_monitoring_pattern(self, service):
        """Test adding new monitoring patterns"""
        service.clear_cache()
        
        # Initially not self-monitoring
        assert not service.is_self_monitoring("custom-monitor")
        
        # Add pattern
        service.add_monitoring_pattern("custom-monitor")
        
        # Now should be detected
        assert service.is_self_monitoring("custom-monitor-app")
        
        # Duplicate add should be ignored
        initial_length = len(service.SELF_MONITORING_PATTERNS)
        service.add_monitoring_pattern("custom-monitor")
        assert len(service.SELF_MONITORING_PATTERNS) == initial_length
    
    def test_add_filter_pattern(self, service):
        """Test adding new filter patterns"""
        test_message = "Custom debug message"
        
        # Initially not filtered
        assert not service.should_filter_message(
            test_message,
            "docker-swarm-ctl-backend"
        )
        
        # Add pattern
        service.add_filter_pattern(r"Custom debug")
        
        # Now should be filtered
        assert service.should_filter_message(
            test_message,
            "docker-swarm-ctl-backend"
        )
    
    def test_get_monitored_containers(self, service):
        """Test tracking of monitored containers"""
        service.clear_cache()
        
        # Initially empty
        assert len(service.get_monitored_containers()) == 0
        
        # Check some containers
        service.is_self_monitoring("docker-swarm-ctl-backend")
        service.is_self_monitoring("nginx")  # Not monitoring
        service.is_self_monitoring("dcp-frontend")
        
        # Should only have monitoring containers
        monitored = service.get_monitored_containers()
        assert len(monitored) == 2
        assert "docker-swarm-ctl-backend" in monitored
        assert "dcp-frontend" in monitored
        assert "nginx" not in monitored
    
    def test_regex_patterns(self, service):
        """Test regex pattern matching in filter"""
        # Test various regex patterns
        messages = [
            ("WebSocket connected from 192.168.1.1", True),
            ("WebSocket disconnected after 5 minutes", True),
            ("Starting log stream", True),
            ("Stopping log stream for container abc", True),
            ("Exec session started by user admin", True),
            ("Stats collection stopped", True),
            ("Normal application log", False),
            ("Error: Database connection failed", False)
        ]
        
        for message, should_filter in messages:
            result = service.should_filter_message(
                message,
                "docker-swarm-ctl-backend"
            )
            assert result == should_filter, f"Failed for message: {message}"