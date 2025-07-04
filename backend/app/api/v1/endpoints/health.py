from datetime import datetime
import time
import sys
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.core.config import settings
from app.core.security import require_role
from app.services.docker_client import get_docker_client
from app.utils.redis import get_redis_client


router = APIRouter()


@router.get("/")
async def basic_health_check():
    return {
        "status": "healthy",
        "service": "docker-control-api",
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    checks = {}
    
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ready"
    except Exception:
        checks["database"] = "not_ready"
    
    # Check Redis
    try:
        redis = await get_redis_client()
        await redis.ping()
        checks["redis"] = "ready"
    except Exception:
        checks["redis"] = "not_ready"
    
    all_ready = all(status == "ready" for status in checks.values())
    
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@router.get("/live")
async def liveness_check():
    return {"alive": True, "timestamp": datetime.utcnow().isoformat()}


@router.get("/detailed", dependencies=[Depends(require_role("admin"))])
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    health_status = {
        "status": "checking",
        "timestamp": datetime.utcnow().isoformat(),
        "version": {
            "api": settings.app_version,
            "python": sys.version,
        },
        "components": {}
    }
    
    # Database check
    try:
        start = time.time()
        await db.execute(text("SELECT 1"))
        health_status["components"]["database"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis check
    try:
        start = time.time()
        redis = await get_redis_client()
        await redis.ping()
        info = await redis.info()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - start) * 1000, 2),
            "version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0)
        }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Docker check
    try:
        start = time.time()
        docker_client = get_docker_client()
        docker_info = docker_client.info()
        health_status["components"]["docker"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - start) * 1000, 2),
            "version": docker_info.get("ServerVersion"),
            "containers": docker_info.get("Containers"),
            "images": docker_info.get("Images")
        }
    except Exception as e:
        health_status["components"]["docker"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Overall status
    all_healthy = all(
        component.get("status") == "healthy"
        for component in health_status["components"].values()
    )
    health_status["status"] = "healthy" if all_healthy else "unhealthy"
    
    return health_status