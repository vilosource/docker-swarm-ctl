from fastapi import APIRouter, Depends
import docker

from dsctl_server.core.auth import get_current_user, UserPrincipal

router = APIRouter()

@router.get("/cluster/info")
def get_cluster_info(current_user: UserPrincipal = Depends(get_current_user)):
    """Returns information about the Docker Swarm cluster."""
    try:
        client = docker.from_env()
        info = client.info()
        return info
    except docker.errors.DockerException as e:
        return {"error": str(e)}
