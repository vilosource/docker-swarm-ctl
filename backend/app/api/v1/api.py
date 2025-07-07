from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, containers, images, system, health, hosts, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(hosts.router, prefix="/hosts", tags=["hosts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(containers.router, prefix="/containers", tags=["containers"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(health.router, prefix="/health", tags=["health"])