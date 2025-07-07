"""
Unit tests for user service
"""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user import UserService
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import NotFoundError, DuplicateError
from app.core.password import verify_password


@pytest.mark.asyncio
class TestUserService:
    """Test UserService class"""
    
    async def test_create_user(self, async_session: AsyncSession):
        """Test creating a new user"""
        service = UserService(async_session)
        
        user_data = UserCreate(
            email="newuser@example.com",
            username="newuser",
            password="password123",
            full_name="New User",
            role="viewer"
        )
        
        user = await service.create(user_data)
        
        assert user.email == user_data.email
        assert user.username == user_data.username
        assert user.full_name == user_data.full_name
        assert user.role == user_data.role
        assert user.is_active is True
        assert verify_password("password123", user.hashed_password)
    
    async def test_create_duplicate_email(self, async_session: AsyncSession, test_user: User):
        """Test creating user with duplicate email"""
        service = UserService(async_session)
        
        user_data = UserCreate(
            email=test_user.email,  # Duplicate email
            username="another",
            password="password123",
            full_name="Another User",
            role="viewer"
        )
        
        with pytest.raises(DuplicateError) as exc_info:
            await service.create(user_data)
        
        assert "email" in str(exc_info.value)
    
    async def test_create_duplicate_username(self, async_session: AsyncSession, test_user: User):
        """Test creating user with duplicate username"""
        service = UserService(async_session)
        
        user_data = UserCreate(
            email="another@example.com",
            username=test_user.username,  # Duplicate username
            password="password123",
            full_name="Another User",
            role="viewer"
        )
        
        with pytest.raises(DuplicateError) as exc_info:
            await service.create(user_data)
        
        assert "username" in str(exc_info.value)
    
    async def test_get_user_by_id(self, async_session: AsyncSession, test_user: User):
        """Test getting user by ID"""
        service = UserService(async_session)
        
        user = await service.get_by_id(test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    async def test_get_nonexistent_user(self, async_session: AsyncSession):
        """Test getting non-existent user"""
        service = UserService(async_session)
        
        user = await service.get_by_id(uuid.uuid4())
        assert user is None
    
    async def test_get_user_by_email(self, async_session: AsyncSession, test_user: User):
        """Test getting user by email"""
        service = UserService(async_session)
        
        user = await service.get_by_email(test_user.email)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    async def test_update_user(self, async_session: AsyncSession, test_user: User):
        """Test updating user"""
        service = UserService(async_session)
        
        update_data = UserUpdate(
            full_name="Updated Name",
            is_active=False
        )
        
        updated_user = await service.update(test_user.id, update_data)
        
        assert updated_user.full_name == "Updated Name"
        assert updated_user.is_active is False
        assert updated_user.email == test_user.email  # Unchanged
        assert updated_user.username == test_user.username  # Unchanged
    
    async def test_update_user_password(self, async_session: AsyncSession, test_user: User):
        """Test updating user password"""
        service = UserService(async_session)
        
        update_data = UserUpdate(password="newpassword123")
        
        updated_user = await service.update(test_user.id, update_data)
        
        assert verify_password("newpassword123", updated_user.hashed_password)
        assert not verify_password("testpassword", updated_user.hashed_password)
    
    async def test_update_nonexistent_user(self, async_session: AsyncSession):
        """Test updating non-existent user"""
        service = UserService(async_session)
        
        update_data = UserUpdate(full_name="Updated")
        
        with pytest.raises(NotFoundError):
            await service.update(uuid.uuid4(), update_data)
    
    async def test_delete_user(self, async_session: AsyncSession, test_user: User):
        """Test deleting user"""
        service = UserService(async_session)
        
        # Delete user
        await service.delete(test_user.id)
        
        # User should not exist anymore
        user = await service.get_by_id(test_user.id)
        assert user is None
    
    async def test_delete_nonexistent_user(self, async_session: AsyncSession):
        """Test deleting non-existent user"""
        service = UserService(async_session)
        
        with pytest.raises(NotFoundError):
            await service.delete(uuid.uuid4())
    
    async def test_list_users(self, async_session: AsyncSession, test_user: User, admin_user: User):
        """Test listing users"""
        service = UserService(async_session)
        
        # List all users
        users = await service.list(skip=0, limit=10)
        
        assert len(users) == 2
        user_ids = [u.id for u in users]
        assert test_user.id in user_ids
        assert admin_user.id in user_ids
    
    async def test_list_users_pagination(self, async_session: AsyncSession, test_user: User, admin_user: User):
        """Test listing users with pagination"""
        service = UserService(async_session)
        
        # First page
        page1 = await service.list(skip=0, limit=1)
        assert len(page1) == 1
        
        # Second page
        page2 = await service.list(skip=1, limit=1)
        assert len(page2) == 1
        
        # Should be different users
        assert page1[0].id != page2[0].id
    
    async def test_count_users(self, async_session: AsyncSession, test_user: User, admin_user: User):
        """Test counting users"""
        service = UserService(async_session)
        
        count = await service.count()
        assert count == 2