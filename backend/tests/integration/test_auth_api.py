"""
Integration tests for authentication API endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import uuid

from app.main import app
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.password import get_password_hash
from app.core.security import create_refresh_token


@pytest.mark.asyncio
class TestAuthAPI:
    """Test authentication API endpoints"""
    
    async def test_login_success(self, async_session: AsyncSession, test_user: User):
        """Test successful login"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "testpassword"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    async def test_login_invalid_credentials(self, async_session: AsyncSession, test_user: User):
        """Test login with invalid credentials"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Wrong password
            response = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "wrongpassword"
                }
            )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    async def test_login_nonexistent_user(self, async_session: AsyncSession):
        """Test login with non-existent user"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": "nonexistent@example.com",
                    "password": "password"
                }
            )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    async def test_login_inactive_user(self, async_session: AsyncSession):
        """Test login with inactive user"""
        # Create inactive user
        user = User(
            id=uuid.uuid4(),
            email="inactive@example.com",
            username="inactive",
            full_name="Inactive User",
            hashed_password=get_password_hash("password"),
            is_active=False,
            role="viewer"
        )
        async_session.add(user)
        await async_session.commit()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": user.email,
                    "password": "password"
                }
            )
        
        assert response.status_code == 403
        assert "Inactive user" in response.json()["detail"]
    
    async def test_refresh_token(self, async_session: AsyncSession, test_user: User):
        """Test token refresh"""
        # Create refresh token
        refresh_token = create_refresh_token({"sub": str(test_user.id)})
        
        # Store in database
        token_obj = RefreshToken(
            token=refresh_token,
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        async_session.add(token_obj)
        await async_session.commit()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    async def test_refresh_invalid_token(self, async_session: AsyncSession):
        """Test refresh with invalid token"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "invalid.token.here"}
            )
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]
    
    async def test_refresh_revoked_token(self, async_session: AsyncSession, test_user: User):
        """Test refresh with revoked token"""
        # Create refresh token
        refresh_token = create_refresh_token({"sub": str(test_user.id)})
        
        # Store as revoked
        token_obj = RefreshToken(
            token=refresh_token,
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7),
            revoked=True
        )
        async_session.add(token_obj)
        await async_session.commit()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]
    
    async def test_logout(self, async_session: AsyncSession, test_user: User, auth_token: str):
        """Test logout"""
        # Create refresh token
        refresh_token = create_refresh_token({"sub": str(test_user.id)})
        
        # Store in database
        token_obj = RefreshToken(
            token=refresh_token,
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        async_session.add(token_obj)
        await async_session.commit()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/logout",
                json={"refresh_token": refresh_token},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
        
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]
        
        # Verify token is revoked
        await async_session.refresh(token_obj)
        assert token_obj.revoked is True
    
    async def test_rate_limiting(self, async_session: AsyncSession):
        """Test rate limiting on login endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make multiple rapid requests
            for i in range(6):
                response = await client.post(
                    "/api/v1/auth/login",
                    data={
                        "username": f"test{i}@example.com",
                        "password": "password"
                    }
                )
                
                if i < 5:
                    # First 5 should succeed (or fail with 401)
                    assert response.status_code in [200, 401]
                else:
                    # 6th should be rate limited
                    assert response.status_code == 429