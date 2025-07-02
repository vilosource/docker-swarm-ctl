import logging
import docker
from fastapi import FastAPI
from dsctl_server.core.config import settings
from dsctl_server.routers import cluster

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="dsctl-server",
    description="API server for dsctl, a Docker Swarm control tool.",
    version="0.1.0",
)

app.include_router(cluster.router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting dsctl-server...")
    logger.info(f"Authentication method: {settings.auth_method}")


@app.get("/ping")
def ping():
    """A simple health check endpoint."""
    return {"ping": "pong"}

@app.get("/version")
def version():
    """Returns the server and Docker version information."""
    try:
        client = docker.from_env()
        docker_version = client.version()
        return {"server_version": app.version, "docker_version": docker_version}
    except docker.errors.DockerException as e:
        return {"error": str(e)}
