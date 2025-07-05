from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from fastapi import Request

from app.models.audit_log import AuditLog
from app.models.user import User


# Helper function for endpoints
async def audit_log(
    db: AsyncSession,
    user: User,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    host_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> AuditLog:
    """Helper function to create audit logs"""
    audit_entry = AuditLog(
        user_id=user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        host_id=host_id,
        details=details,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    db.add(audit_entry)
    await db.commit()
    
    return audit_entry


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log(
        self,
        user: User,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        host_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        audit_log = AuditLog(
            user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            host_id=host_id,
            details=details,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        
        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)
        
        return audit_log
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_action(
        self,
        action: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id
                )
            )
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()