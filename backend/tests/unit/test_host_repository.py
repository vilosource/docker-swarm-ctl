"""
Unit tests for HostRepository
"""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import Mock, AsyncMock, MagicMock

from app.repositories.host_repository import HostRepository
from app.models import DockerHost, User, UserRole
from app.core.exceptions import ResourceNotFoundError, ResourceConflictError


class TestHostRepository:
    """Test cases for HostRepository"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.add = Mock()
        db.delete = Mock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        return db
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create a repository instance with mock db"""
        return HostRepository(mock_db)
    
    @pytest.fixture
    def sample_host(self):
        """Create a sample host for testing"""
        host = Mock(spec=DockerHost)
        host.id = uuid4()
        host.name = "test-host"
        host.endpoint = "tcp://localhost:2375"
        host.is_active = True
        host.is_default = False
        host.status = "healthy"
        return host
    
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_db, sample_host):
        """Test getting host by ID when it exists"""
        # Setup mock
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_host
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await repository.get_by_id(str(sample_host.id))
        
        # Verify
        assert result == sample_host
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_db):
        """Test getting host by ID when it doesn't exist"""
        # Setup mock
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await repository.get_by_id("non-existent-id")
        
        # Verify
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_or_404_found(self, repository, mock_db, sample_host):
        """Test get_by_id_or_404 when host exists"""
        # Setup mock
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_host
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await repository.get_by_id_or_404(str(sample_host.id))
        
        # Verify
        assert result == sample_host
    
    @pytest.mark.asyncio
    async def test_get_by_id_or_404_not_found(self, repository, mock_db):
        """Test get_by_id_or_404 raises when host doesn't exist"""
        # Setup mock
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute & Verify
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await repository.get_by_id_or_404("non-existent-id")
        
        assert "docker_host" in str(exc_info.value)
        assert "non-existent-id" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_exists_by_name_true(self, repository, mock_db, sample_host):
        """Test checking if host exists by name - exists"""
        # Setup mock
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_host
        mock_db.execute.return_value = mock_result
        
        # Execute
        exists = await repository.exists_by_name("test-host")
        
        # Verify
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_exists_by_name_false(self, repository, mock_db):
        """Test checking if host exists by name - doesn't exist"""
        # Setup mock
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute
        exists = await repository.exists_by_name("non-existent")
        
        # Verify
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_create_success(self, repository, mock_db):
        """Test creating a new host"""
        # Setup
        host_data = {
            "name": "new-host",
            "endpoint": "tcp://newhost:2375",
            "is_active": True
        }
        
        # Mock exists check
        mock_exists_result = Mock()
        mock_exists_result.scalar_one_or_none.return_value = None
        
        # Use side_effect to return different results for different calls
        mock_db.execute.side_effect = [mock_exists_result]
        
        # Execute
        result = await repository.create(host_data)
        
        # Verify
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Check that DockerHost was created with correct data
        created_host = mock_db.add.call_args[0][0]
        assert created_host.name == "new-host"
        assert created_host.endpoint == "tcp://newhost:2375"
    
    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, repository, mock_db, sample_host):
        """Test creating host with duplicate name raises error"""
        # Setup
        host_data = {"name": "test-host", "endpoint": "tcp://host:2375"}
        
        # Mock exists check to return existing host
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_host
        mock_db.execute.return_value = mock_result
        
        # Execute & Verify
        with pytest.raises(ResourceConflictError) as exc_info:
            await repository.create(host_data)
        
        assert "already exists" in str(exc_info.value)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_list_by_user_permissions_admin(self, repository, mock_db):
        """Test admin user can see all hosts"""
        # Setup
        admin_user = Mock(spec=User)
        admin_user.id = uuid4()
        admin_user.role = UserRole.admin
        
        hosts = [Mock(spec=DockerHost) for _ in range(3)]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = hosts
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await repository.list_by_user_permissions(admin_user)
        
        # Verify
        assert result == hosts
        assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_update_status(self, repository, mock_db, sample_host):
        """Test updating host status with version info"""
        # Setup
        host_id = str(sample_host.id)
        version_info = {
            "Version": "20.10.17",
            "ApiVersion": "1.41",
            "Os": "linux",
            "Arch": "amd64"
        }
        
        # Mock get_by_id_or_404
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_host
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await repository.update_status(
            host_id,
            status="healthy",
            version_info=version_info
        )
        
        # Verify
        assert sample_host.status == "healthy"
        assert sample_host.docker_version == "20.10.17"
        assert sample_host.api_version == "1.41"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete(self, repository, mock_db, sample_host):
        """Test deleting a host"""
        # Setup
        host_id = str(sample_host.id)
        
        # Mock get_by_id_or_404
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_host
        mock_db.execute.return_value = mock_result
        
        # Execute
        await repository.delete(host_id)
        
        # Verify
        mock_db.delete.assert_called_once_with(sample_host)
        mock_db.commit.assert_called_once()