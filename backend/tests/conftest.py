"""
Pytest configuration and fixtures
"""

import asyncio
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import uuid
from datetime import datetime

from app.db.base import Base
from app.models.user import User
from app.core.password import get_password_hash
from app.core.security import create_access_token


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_engine():
    """Create async engine for tests"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests"""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        role="operator"
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(async_session: AsyncSession) -> User:
    """Create an admin user"""
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        role="admin"
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    """Create an auth token for test user"""
    return create_access_token({"sub": str(test_user.id), "role": test_user.role})


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create an auth token for admin user"""
    return create_access_token({"sub": str(admin_user.id), "role": admin_user.role})


@pytest.fixture
def mock_docker_client():
    """Mock Docker client"""
    with patch("docker.from_env") as mock:
        client = Mock()
        mock.return_value = client
        
        # Mock common Docker client methods
        client.ping.return_value = True
        client.info.return_value = {
            "ServerVersion": "24.0.0",
            "ApiVersion": "1.43",
            "Containers": 5,
            "Images": 10,
            "NCPU": 4,
            "MemTotal": 8589934592
        }
        
        # Mock containers
        client.containers = Mock()
        client.containers.list.return_value = []
        
        # Mock images
        client.images = Mock()
        client.images.list.return_value = []
        
        # Mock networks
        client.networks = Mock()
        client.networks.list.return_value = []
        
        # Mock volumes
        client.volumes = Mock()
        client.volumes.list.return_value = []
        
        yield client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    with patch("app.utils.redis.RedisClient") as mock:
        redis_client = Mock()
        mock.get_client.return_value = redis_client
        
        # Mock common Redis methods
        redis_client.get.return_value = None
        redis_client.set.return_value = True
        redis_client.delete.return_value = True
        redis_client.exists.return_value = False
        
        yield redis_client