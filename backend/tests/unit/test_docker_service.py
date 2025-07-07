"""
Unit tests for Docker service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import docker
from datetime import datetime

from app.services.docker_service import DockerService, DockerServiceFactory
from app.core.exceptions import DockerConnectionError, DockerOperationError


class TestDockerService:
    """Test DockerService class"""
    
    def test_initialization_with_socket(self):
        """Test Docker service initialization with Unix socket"""
        with patch("docker.DockerClient") as mock_client:
            service = DockerService()
            
            mock_client.assert_called_once_with(
                base_url="unix://var/run/docker.sock",
                timeout=30
            )
    
    def test_initialization_with_tcp(self):
        """Test Docker service initialization with TCP"""
        with patch("docker.DockerClient") as mock_client:
            service = DockerService(docker_host="tcp://localhost:2375")
            
            mock_client.assert_called_once_with(
                base_url="tcp://localhost:2375",
                timeout=30
            )
    
    def test_initialization_connection_error(self):
        """Test Docker service initialization with connection error"""
        with patch("docker.DockerClient") as mock_client:
            mock_client.side_effect = docker.errors.DockerException("Connection failed")
            
            with pytest.raises(DockerConnectionError):
                service = DockerService()
    
    @pytest.mark.asyncio
    async def test_list_containers(self, mock_docker_client):
        """Test listing containers"""
        # Setup mock containers
        container1 = Mock()
        container1.id = "abc123"
        container1.name = "test-container-1"
        container1.image.tags = ["nginx:latest"]
        container1.status = "running"
        container1.attrs = {
            "State": {"Status": "running"},
            "Created": "2024-01-01T00:00:00.000000Z",
            "Config": {"Labels": {}}
        }
        
        container2 = Mock()
        container2.id = "def456"
        container2.name = "test-container-2"
        container2.image.tags = ["redis:alpine"]
        container2.status = "exited"
        container2.attrs = {
            "State": {"Status": "exited"},
            "Created": "2024-01-01T00:00:00.000000Z",
            "Config": {"Labels": {}}
        }
        
        mock_docker_client.containers.list.return_value = [container1, container2]
        
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            containers = await service.list_containers(all=True)
        
        assert len(containers) == 2
        assert containers[0].id == "abc123"
        assert containers[0].name == "test-container-1"
        assert containers[0].status == "running"
        assert containers[1].id == "def456"
        assert containers[1].name == "test-container-2"
        assert containers[1].status == "exited"
    
    @pytest.mark.asyncio
    async def test_list_containers_with_filters(self, mock_docker_client):
        """Test listing containers with filters"""
        mock_docker_client.containers.list.return_value = []
        
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            await service.list_containers(
                all=False,
                filters={"status": "running", "label": "app=web"}
            )
        
        mock_docker_client.containers.list.assert_called_once_with(
            all=False,
            filters={"status": "running", "label": "app=web"}
        )
    
    @pytest.mark.asyncio
    async def test_get_container(self, mock_docker_client):
        """Test getting a specific container"""
        container = Mock()
        container.id = "abc123"
        container.name = "test-container"
        container.image.tags = ["nginx:latest"]
        container.status = "running"
        container.attrs = {
            "State": {"Status": "running"},
            "Created": "2024-01-01T00:00:00.000000Z",
            "Config": {"Labels": {}}
        }
        
        mock_docker_client.containers.get.return_value = container
        
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            result = await service.get_container("abc123")
        
        assert result.id == "abc123"
        assert result.name == "test-container"
        mock_docker_client.containers.get.assert_called_once_with("abc123")
    
    @pytest.mark.asyncio
    async def test_get_container_not_found(self, mock_docker_client):
        """Test getting non-existent container"""
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            with pytest.raises(DockerOperationError) as exc_info:
                await service.get_container("nonexistent")
        
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_create_container(self, mock_docker_client):
        """Test creating a container"""
        container = Mock()
        container.id = "abc123"
        container.name = "new-container"
        container.image.tags = ["nginx:latest"]
        container.status = "created"
        container.attrs = {
            "State": {"Status": "created"},
            "Created": "2024-01-01T00:00:00.000000Z",
            "Config": {"Labels": {}}
        }
        
        mock_docker_client.containers.create.return_value = container
        
        config = {
            "image": "nginx:latest",
            "name": "new-container",
            "ports": {"80/tcp": 8080}
        }
        
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            result = await service.create_container(config)
        
        assert result.id == "abc123"
        assert result.name == "new-container"
        mock_docker_client.containers.create.assert_called_once_with(**config)
    
    @pytest.mark.asyncio
    async def test_start_container(self, mock_docker_client):
        """Test starting a container"""
        container = Mock()
        container.start.return_value = None
        mock_docker_client.containers.get.return_value = container
        
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            await service.start_container("abc123")
        
        container.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_container(self, mock_docker_client):
        """Test stopping a container"""
        container = Mock()
        container.stop.return_value = None
        mock_docker_client.containers.get.return_value = container
        
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            await service.stop_container("abc123", timeout=10)
        
        container.stop.assert_called_once_with(timeout=10)
    
    @pytest.mark.asyncio
    async def test_remove_container(self, mock_docker_client):
        """Test removing a container"""
        container = Mock()
        container.remove.return_value = None
        mock_docker_client.containers.get.return_value = container
        
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            await service.remove_container("abc123", force=True, volumes=True)
        
        container.remove.assert_called_once_with(force=True, v=True)
    
    @pytest.mark.asyncio
    async def test_list_images(self, mock_docker_client):
        """Test listing images"""
        image1 = Mock()
        image1.id = "sha256:abc123"
        image1.tags = ["nginx:latest", "nginx:1.21"]
        image1.attrs = {
            "Created": "2024-01-01T00:00:00.000000Z",
            "Size": 142000000,
            "Config": {"Labels": {}}
        }
        
        image2 = Mock()
        image2.id = "sha256:def456"
        image2.tags = ["redis:alpine"]
        image2.attrs = {
            "Created": "2024-01-01T00:00:00.000000Z",
            "Size": 32000000,
            "Config": {"Labels": {}}
        }
        
        mock_docker_client.images.list.return_value = [image1, image2]
        
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            images = await service.list_images()
        
        assert len(images) == 2
        assert images[0].id == "sha256:abc123"
        assert "nginx:latest" in images[0].tags
        assert images[1].id == "sha256:def456"
        assert "redis:alpine" in images[1].tags
    
    @pytest.mark.asyncio
    async def test_get_system_info(self, mock_docker_client):
        """Test getting system info"""
        with patch("docker.from_env", return_value=mock_docker_client):
            service = DockerService()
            info = await service.get_system_info()
        
        assert info["ServerVersion"] == "24.0.0"
        assert info["Containers"] == 5
        assert info["Images"] == 10
        mock_docker_client.info.assert_called_once()


class TestDockerServiceFactory:
    """Test DockerServiceFactory"""
    
    def test_create_single_host_service(self):
        """Test creating single-host Docker service"""
        with patch("app.services.docker_service.DockerService") as mock_service:
            service = DockerServiceFactory.create(None, None, multi_host=False)
            
            mock_service.assert_called_once()
            assert service == mock_service.return_value
    
    def test_create_multi_host_service(self):
        """Test creating multi-host Docker service"""
        user = Mock()
        db = Mock()
        
        with patch("app.services.docker_service.MultiHostDockerService") as mock_service:
            service = DockerServiceFactory.create(user, db, multi_host=True)
            
            mock_service.assert_called_once_with(user, db)
            assert service == mock_service.return_value