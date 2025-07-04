from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.password import get_password_hash
from app.core.exceptions import ResourceNotFoundError, ResourceConflictError


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, user_data: UserCreate) -> User:
        try:
            user = User(
                email=user_data.email,
                username=user_data.username,
                full_name=user_data.full_name,
                role=user_data.role,
                is_active=user_data.is_active,
                hashed_password=get_password_hash(user_data.password)
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError as e:
            await self.db.rollback()
            if "email" in str(e.orig):
                raise ResourceConflictError("User", f"User with email {user_data.email} already exists")
            elif "username" in str(e.orig):
                raise ResourceConflictError("User", f"User with username {user_data.username} already exists")
            raise
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        result = await self.db.execute(
            select(User).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def update(self, user_id: UUID, user_data: UserUpdate) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))
        
        update_data = user_data.dict(exclude_unset=True)
        
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError as e:
            await self.db.rollback()
            if "email" in str(e.orig):
                raise ResourceConflictError("User", f"User with email {user_data.email} already exists")
            elif "username" in str(e.orig):
                raise ResourceConflictError("User", f"User with username {user_data.username} already exists")
            raise
    
    async def delete(self, user_id: UUID) -> None:
        user = await self.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))
        
        await self.db.delete(user)
        await self.db.commit()
    
    async def count(self) -> int:
        result = await self.db.execute(select(func.count(User.id)))
        return result.scalar()