from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, users, containers, images, system, health, hosts, dashboard, volumes, networks,
    swarm, swarms, nodes, services, secrets, configs, wizards
)

api_router = APIRouter()

# Authentication and user management
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Docker host management
api_router.include_router(hosts.router, prefix="/hosts", tags=["hosts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# Wizard framework
api_router.include_router(wizards.router, prefix="/wizards", tags=["wizards"])

# Container management
api_router.include_router(containers.router, prefix="/containers", tags=["containers"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(volumes.router, prefix="/volumes", tags=["volumes"])
api_router.include_router(networks.router, prefix="/networks", tags=["networks"])

# Swarm management
api_router.include_router(swarm.router, prefix="/swarm", tags=["swarm"])
api_router.include_router(swarms.router, prefix="/swarms", tags=["swarms"])
api_router.include_router(nodes.router, prefix="/nodes", tags=["nodes"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(secrets.router, prefix="/secrets", tags=["secrets"])
api_router.include_router(configs.router, prefix="/configs", tags=["configs"])

# System
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(health.router, prefix="/health", tags=["health"])