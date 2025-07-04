from typing import Optional
from fastapi import WebSocket, status, Query
from jose import JWTError, jwt
from app.core.config import settings
from app.services.user import UserService
from app.db.session import AsyncSessionLocal
from app.models.user import User
import logging

logger = logging.getLogger(__name__)


async def get_current_user_ws(websocket: WebSocket, token: Optional[str] = Query(None)) -> Optional[User]:
    """Authenticate WebSocket connection using JWT token from query parameters."""
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return None
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return None
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return None
    
    async with AsyncSessionLocal() as db:
        user_service = UserService(db)
        user = await user_service.get_by_id(user_id)
        if user is None or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found or inactive")
            return None
        return user


def check_permission(user: User, required_role: str) -> bool:
    """Check if user has required role or higher permission."""
    role_hierarchy = {"viewer": 0, "operator": 1, "admin": 2}
    user_level = role_hierarchy.get(user.role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    return user_level >= required_level