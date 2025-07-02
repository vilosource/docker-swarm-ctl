from abc import ABC, abstractmethod
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from starlette.status import HTTP_401_UNAUTHORIZED
from abc import ABC, abstractmethod

from dsctl_server.core.config import settings

class UserPrincipal(BaseModel):
    username: str
    roles: list[str]

class AuthStrategy(ABC):
    @abstractmethod
    def authenticate(self, token: str) -> UserPrincipal | None:
        pass

class StaticTokenAuthStrategy(AuthStrategy):
    def authenticate(self, token: str) -> UserPrincipal | None:
        if token == settings.static_token_secret:
            # For static token, we can assign a default user and role.
            return UserPrincipal(username="static_user", roles=["admin"])
        return None

def get_auth_strategy() -> AuthStrategy:
    if settings.auth_method == "static":
        return StaticTokenAuthStrategy()
    # Future auth methods like 'entra_id' would be added here.
    raise NotImplementedError(f"Auth method '{settings.auth_method}' not implemented.")

# This defines the security scheme for OpenAPI (Swagger UI)
oauth2_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    auth_strategy: AuthStrategy = Depends(get_auth_strategy)
) -> UserPrincipal:
    user = auth_strategy.authenticate(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
