"""
Rate limiting implementation using SlowAPI
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, Response
from typing import Optional

from app.core.config import settings
from app.core.logging import logger


def get_user_id(request: Request) -> str:
    """
    Get user identifier for rate limiting.
    Uses authenticated user ID if available, otherwise falls back to IP address.
    """
    # Try to get authenticated user from request state
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_user_id,
    default_limits=[settings.rate_limit_default] if settings.rate_limit_enabled else [],
    enabled=settings.rate_limit_enabled,
    headers_enabled=True,  # Include rate limit headers in response
    strategy="fixed-window",  # Use fixed window strategy
    storage_uri=settings.redis_url,  # Use Redis for distributed rate limiting
)


def configure_rate_limiting(app):
    """Configure rate limiting for the FastAPI application"""
    if not settings.rate_limit_enabled:
        logger.info("Rate limiting is disabled")
        return
    
    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add SlowAPI middleware
    app.add_middleware(SlowAPIMiddleware)
    
    # Set the limiter on the app state
    app.state.limiter = limiter
    
    logger.info("Rate limiting configured with Redis backend")


# Export common rate limit decorators
def rate_limit(limit: str):
    """
    Rate limit decorator for endpoints.
    
    Example:
        @rate_limit("5/minute")
        async def login(...)
    """
    return limiter.limit(limit)


# Common rate limits
auth_limit = limiter.limit(settings.rate_limit_auth)
default_limit = limiter.limit(settings.rate_limit_default)
strict_limit = limiter.limit(settings.rate_limit_strict)
relaxed_limit = limiter.limit(settings.rate_limit_relaxed)