from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uuid
import logging

# Apply SSH patch before any other imports that might use docker
from app.services.ssh_docker_patch import apply_ssh_docker_patch
apply_ssh_docker_patch()

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging_config import setup_logging
from app.core.rate_limit import configure_rate_limiting
from app.api.v1.api import api_router
from app.api.v1.websocket import containers_router as ws_containers_router
from app.db.session import engine
from app.db.base import Base
from app.db.base_class import *  # noqa - Import all models
from app.utils.redis import RedisClient
from app.services.logs.stream_manager import get_stream_manager

# Configure logging with self-monitoring filter
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Start log stream manager
    stream_manager = get_stream_manager()
    await stream_manager.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Stop log stream manager
    await stream_manager.stop()
    
    await RedisClient.close()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    docs_url=f"{settings.api_v1_str}/docs",
    redoc_url=f"{settings.api_v1_str}/redoc",
    lifespan=lifespan
)

# Configure rate limiting
configure_rate_limiting(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:;"
        )
    
    return response


# Global exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": str(exc),
                "details": exc.details
            },
            "status": "error",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Generic exception handler for unexpected errors
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": f"Internal server error: {str(exc)}",
                "type": type(exc).__name__
            },
            "status": "error",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Include API router
app.include_router(api_router, prefix=settings.api_v1_str)

# Include WebSocket routers
app.include_router(ws_containers_router, prefix="/ws", tags=["websocket"])
from app.api.v1.websocket import exec_router as ws_exec_router, events_router as ws_events_router
app.include_router(ws_exec_router, prefix="/ws", tags=["websocket"])
app.include_router(ws_events_router, prefix="/ws", tags=["websocket"])


@app.get("/")
async def root():
    return {
        "message": "Docker Control Platform API",
        "version": settings.app_version,
        "docs": f"{settings.api_v1_str}/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)