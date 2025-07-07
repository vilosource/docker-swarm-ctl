"""
Integration tests for user management API endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.main import app
from app.models.user import User


@pytest.mark.asyncio
class TestUsersAPI:
    """Test user management API endpoints"""
    
    async def test_list_users(self, async_session: AsyncSession, admin_token: str, test_user: User, admin_user: User):
        """Test listing users"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/users/",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        
        emails = [user["email"] for user in data]
        assert test_user.email in emails
        assert admin_user.email in emails
    
    async def test_list_users_unauthorized(self, async_session: AsyncSession, auth_token: str):
        """Test listing users without admin role"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/users/",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
        
        assert response.status_code == 403
    
    async def test_get_current_user(self, async_session: AsyncSession, auth_token: str, test_user: User):
        """Test getting current user info"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert "hashed_password" not in data
    
    async def test_get_user_by_id(self, async_session: AsyncSession, admin_token: str, test_user: User):
        """Test getting user by ID"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/users/{test_user.id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
    
    async def test_create_user(self, async_session: AsyncSession, admin_token: str):
        """Test creating a new user"""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "password123",
            "full_name": "New User",
            "role": "viewer"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/users/",
                json=user_data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["role"] == user_data["role"]
        assert "id" in data
        assert "hashed_password" not in data
    
    async def test_create_duplicate_user(self, async_session: AsyncSession, admin_token: str, test_user: User):
        """Test creating user with duplicate email"""
        user_data = {
            "email": test_user.email,  # Duplicate
            "username": "another",
            "password": "password123",
            "full_name": "Another User",
            "role": "viewer"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/users/",
                json=user_data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    async def test_update_user(self, async_session: AsyncSession, admin_token: str, test_user: User):
        """Test updating a user"""
        update_data = {
            "full_name": "Updated Name",
            "role": "admin"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/users/{test_user.id}",
                json=update_data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["role"] == "admin"
        assert data["email"] == test_user.email  # Unchanged
    
    async def test_update_current_user(self, async_session: AsyncSession, auth_token: str, test_user: User):
        """Test updating current user (self)"""
        update_data = {
            "full_name": "Self Updated"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put(
                "/api/v1/users/me",
                json=update_data,
                headers={"Authorization": f"Bearer {auth_token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Self Updated"
    
    async def test_update_user_role_forbidden(self, async_session: AsyncSession, auth_token: str):
        """Test non-admin cannot update roles"""
        update_data = {
            "role": "admin"  # Try to make self admin
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put(
                "/api/v1/users/me",
                json=update_data,
                headers={"Authorization": f"Bearer {auth_token}"}
            )
        
        assert response.status_code == 403
    
    async def test_delete_user(self, async_session: AsyncSession, admin_token: str):
        """Test deleting a user"""
        # Create a user to delete
        user = User(
            id=uuid.uuid4(),
            email="todelete@example.com",
            username="todelete",
            full_name="To Delete",
            hashed_password="hash",
            is_active=True,
            role="viewer"
        )
        async_session.add(user)
        await async_session.commit()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.delete(
                f"/api/v1/users/{user.id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        assert response.status_code == 204
        
        # Verify user is deleted
        deleted_user = await async_session.get(User, user.id)
        assert deleted_user is None
    
    async def test_delete_self_forbidden(self, async_session: AsyncSession, admin_token: str, admin_user: User):
        """Test admin cannot delete themselves"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.delete(
                f"/api/v1/users/{admin_user.id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        assert response.status_code == 403
        assert "Cannot delete yourself" in response.json()["detail"]