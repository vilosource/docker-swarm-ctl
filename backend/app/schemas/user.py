from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID
import re

from app.models.user import UserRole


class UserBase(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.viewer
    is_active: bool = True
    
    @validator("email")
    def validate_email(cls, v):
        # Basic email validation that allows localhost domains for development
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})?$', v):
            raise ValueError("Invalid email format")
        return v
    
    @validator("username")
    def validate_username(cls, v):
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
    @validator("password")
    def validate_password(cls, v):
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v


class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, min_length=5, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPair(Token):
    refresh_token: str