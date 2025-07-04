from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
import secrets

from app.db.session import get_db
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, get_current_active_user
from app.core.password import verify_password
from app.core.exceptions import InvalidCredentialsError, TokenInvalidError
from app.schemas.user import UserLogin, TokenPair, Token
from app.services.user import UserService
from app.services.audit import AuditService
from app.models.refresh_token import RefreshToken


router = APIRouter()


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    user = await user_service.get_by_email(form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise InvalidCredentialsError()
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Store refresh token
    refresh_token_obj = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    )
    db.add(refresh_token_obj)
    
    # Log the login
    audit_service = AuditService(db)
    await audit_service.log(
        user=user,
        action="auth.login",
        request=request
    )
    
    await db.commit()
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = jwt.decode(
            refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise TokenInvalidError()
    except JWTError:
        raise TokenInvalidError()
    
    # Check if refresh token exists and is not revoked
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.revoked == False
        )
    )
    stored_token = result.scalar_one_or_none()
    
    if not stored_token or stored_token.expires_at < datetime.utcnow():
        raise TokenInvalidError()
    
    # Get user
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user or not user.is_active:
        raise TokenInvalidError()
    
    # Create new access token
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    
    return Token(access_token=access_token)


@router.post("/logout")
async def logout(
    request: Request,
    refresh_token: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Revoke refresh token
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.user_id == current_user.id
        )
    )
    stored_token = result.scalar_one_or_none()
    
    if stored_token:
        stored_token.revoked = True
    
    # Log the logout
    audit_service = AuditService(db)
    await audit_service.log(
        user=current_user,
        action="auth.logout",
        request=request
    )
    
    await db.commit()
    
    return {"message": "Successfully logged out"}