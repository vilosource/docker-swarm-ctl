"""
Unit tests for ContainerConfigBuilder
"""

import pytest
from app.api.decorators_enhanced import ContainerConfigBuilder


class MockContainerCreate:
    """Mock container create schema for testing"""
    def __init__(self, **kwargs):
        self.image = kwargs.get('image', 'nginx:latest')
        self.name = kwargs.get('name')
        self.command = kwargs.get('command')
        self.environment = kwargs.get('environment')
        self.ports = kwargs.get('ports')
        self.volumes = kwargs.get('volumes')
        self.labels = kwargs.get('labels')
        self.restart_policy = kwargs.get('restart_policy')
        self.host_config = kwargs.get('host_config')


class TestContainerConfigBuilder:
    """Test cases for ContainerConfigBuilder"""
    
    def test_minimal_config(self):
        """Test building config with only required fields"""
        config = MockContainerCreate(image='nginx:latest')
        result = ContainerConfigBuilder.from_create_schema(config)
        
        assert result == {
            'image': 'nginx:latest',
            'detach': True
        }
    
    def test_full_config(self):
        """Test building config with all fields"""
        config = MockContainerCreate(
            image='nginx:latest',
            name='test-container',
            command=['nginx', '-g', 'daemon off;'],
            environment={'ENV_VAR': 'value'},
            ports={'80/tcp': 8080},
            volumes={'/host/path': {'bind': '/container/path', 'mode': 'rw'}},
            labels={'app': 'test'},
            restart_policy='unless-stopped'
        )
        
        result = ContainerConfigBuilder.from_create_schema(config)
        
        assert result['image'] == 'nginx:latest'
        assert result['detach'] is True
        assert result['name'] == 'test-container'
        assert result['command'] == ['nginx', '-g', 'daemon off;']
        assert result['environment'] == {'ENV_VAR': 'value'}
        assert result['ports'] == {'80/tcp': 8080}
        assert result['volumes'] == {'/host/path': {'bind': '/container/path', 'mode': 'rw'}}
        assert result['labels'] == {'app': 'test'}
        assert result['restart_policy'] == {'Name': 'unless-stopped'}
    
    def test_none_values_excluded(self):
        """Test that None values are not included in config"""
        config = MockContainerCreate(
            image='nginx:latest',
            name=None,
            command=None,
            environment=None
        )
        
        result = ContainerConfigBuilder.from_create_schema(config)
        
        assert 'name' not in result
        assert 'command' not in result
        assert 'environment' not in result
        assert result == {
            'image': 'nginx:latest',
            'detach': True
        }
    
    def test_restart_policy_formatting(self):
        """Test restart policy is properly formatted"""
        config = MockContainerCreate(
            image='nginx:latest',
            restart_policy='always'
        )
        
        result = ContainerConfigBuilder.from_create_schema(config)
        
        assert result['restart_policy'] == {'Name': 'always'}
    
    def test_host_config_merge(self):
        """Test that host_config is merged into the main config"""
        config = MockContainerCreate(
            image='nginx:latest',
            host_config={
                'memory': 536870912,  # 512MB
                'cpu_shares': 512
            }
        )
        
        result = ContainerConfigBuilder.from_create_schema(config)
        
        assert result['memory'] == 536870912
        assert result['cpu_shares'] == 512
        assert result['image'] == 'nginx:latest'
        assert result['detach'] is True
    
    def test_empty_collections(self):
        """Test that empty collections are included"""
        config = MockContainerCreate(
            image='nginx:latest',
            environment={},
            labels={},
            volumes={}
        )
        
        result = ContainerConfigBuilder.from_create_schema(config)
        
        # Empty collections should be included
        assert result['environment'] == {}
        assert result['labels'] == {}
        assert result['volumes'] == {}