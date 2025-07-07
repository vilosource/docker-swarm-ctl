"""
Unit tests for authentication
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt
import uuid

from app.core.security import (
    create_access_token,
    create_refresh_token
)
from app.core.password import get_password_hash, verify_password
from app.core.config import settings
from app.core.exceptions import TokenInvalidError


class TestPasswordHashing:
    """Test password hashing functions"""
    
    def test_password_hash_verification(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Should verify correctly
        assert verify_password(password, hashed) is True
        
        # Wrong password should not verify
        assert verify_password("wrongpassword", hashed) is False
    
    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes"""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # Both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokenCreation:
    """Test token creation functions"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        user_id = str(uuid.uuid4())
        data = {"sub": user_id, "role": "operator"}
        token = create_access_token(data)
        
        # Decode token
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        assert payload["sub"] == user_id
        assert payload["role"] == "operator"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        user_id = str(uuid.uuid4())
        data = {"sub": user_id}
        token = create_refresh_token(data)
        
        # Decode token
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_token_expiration(self):
        """Test token expiration times"""
        user_id = str(uuid.uuid4())
        
        # Access token
        access_token = create_access_token({"sub": user_id})
        access_payload = jwt.decode(
            access_token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        access_exp = datetime.fromtimestamp(access_payload["exp"])
        
        # Should expire in configured minutes from now
        expected_exp = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        assert abs((access_exp - expected_exp).total_seconds()) < 5  # Allow 5 seconds tolerance
        
        # Refresh token
        refresh_token = create_refresh_token({"sub": user_id})
        refresh_payload = jwt.decode(
            refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"])
        
        # Should expire in configured days from now
        expected_exp = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        assert abs((refresh_exp - expected_exp).total_seconds()) < 5  # Allow 5 seconds tolerance


class TestTokenVerification:
    """Test token verification by decoding"""
    
    def test_decode_valid_access_token(self):
        """Test decoding of valid access token"""
        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id, "role": "admin"})
        
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        assert payload["sub"] == user_id
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
    
    def test_decode_invalid_token(self):
        """Test decoding of invalid token"""
        with pytest.raises(jwt.JWTError):
            jwt.decode(
                "invalid.token.here",
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
    
    def test_decode_expired_token(self):
        """Test decoding of expired token"""
        user_id = str(uuid.uuid4())
        # Create token with negative expiration
        data = {"sub": user_id}
        data["exp"] = datetime.utcnow() - timedelta(hours=1)
        
        token = jwt.encode(
            data,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
    
    def test_decode_wrong_secret_token(self):
        """Test decoding with wrong secret"""
        user_id = str(uuid.uuid4())
        data = {"sub": user_id, "exp": datetime.utcnow() + timedelta(hours=1)}
        
        # Create token with different secret
        token = jwt.encode(
            data,
            "wrong_secret",
            algorithm=settings.algorithm
        )
        
        with pytest.raises(jwt.JWTError):
            jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )