from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.common import PaginatedResponse
from app.services.user import UserService
from app.services.audit import AuditService
from app.models.user import User


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    users = await user_service.get_all(skip=skip, limit=limit)
    total = await user_service.count()
    
    return PaginatedResponse(
        items=users,
        total=total,
        page=skip // limit + 1,
        per_page=limit,
        pages=(total + limit - 1) // limit
    )


@router.post("/", response_model=UserResponse)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    user = await user_service.create(user_data)
    
    # Log the action
    audit_service = AuditService(db)
    await audit_service.log(
        user=current_user,
        action="user.create",
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "username": user.username, "role": user.role},
        request=request
    )
    
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    user = await user_service.update(user_id, user_data)
    
    # Log the action
    audit_service = AuditService(db)
    await audit_service.log(
        user=current_user,
        action="user.update",
        resource_type="user",
        resource_id=str(user.id),
        details=user_data.dict(exclude_unset=True),
        request=request
    )
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user_service = UserService(db)
    await user_service.delete(user_id)
    
    # Log the action
    audit_service = AuditService(db)
    await audit_service.log(
        user=current_user,
        action="user.delete",
        resource_type="user",
        resource_id=str(user_id),
        request=request
    )
    
    return {"message": "User deleted successfully"}