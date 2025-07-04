from celery import Task
from app.workers.celery import celery_app
from app.services.docker_client import get_docker_client
from app.utils.tasks import task_manager
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def pull_docker_image(self: Task, repository: str, tag: str = "latest", auth_config: dict = None):
    """Pull a Docker image"""
    task_id = self.request.id
    
    try:
        task_manager.update_task(task_id, "in_progress", f"Pulling {repository}:{tag}")
        
        client = get_docker_client()
        
        # Pull the image with progress tracking
        for line in client.api.pull(repository, tag=tag, auth_config=auth_config, stream=True, decode=True):
            if "progress" in line:
                # Update task progress
                task_manager.update_task(task_id, progress=50)
            elif "status" in line:
                task_manager.update_task(task_id, status="in_progress", result=line["status"])
        
        # Get the pulled image
        image = client.images.get(f"{repository}:{tag}")
        
        task_manager.update_task(
            task_id,
            status="completed",
            progress=100,
            result=f"Successfully pulled {repository}:{tag}",
        )
        
        return {
            "status": "success",
            "image_id": image.id,
            "tags": image.tags,
            "size": image.attrs["Size"]
        }
        
    except Exception as e:
        logger.error(f"Failed to pull image {repository}:{tag}: {str(e)}")
        task_manager.update_task(
            task_id,
            status="failed",
            error=str(e)
        )
        raise


@celery_app.task(bind=True)
def system_prune(self: Task, volumes: bool = False):
    """Prune unused Docker resources"""
    task_id = self.request.id
    
    try:
        task_manager.update_task(task_id, "in_progress", "Starting system prune")
        
        client = get_docker_client()
        
        # Prune containers
        task_manager.update_task(task_id, progress=25, result="Pruning containers")
        containers_result = client.containers.prune()
        
        # Prune images
        task_manager.update_task(task_id, progress=50, result="Pruning images")
        images_result = client.images.prune()
        
        # Prune networks
        task_manager.update_task(task_id, progress=75, result="Pruning networks")
        networks_result = client.networks.prune()
        
        # Prune volumes if requested
        volumes_result = {}
        if volumes:
            task_manager.update_task(task_id, progress=90, result="Pruning volumes")
            volumes_result = client.volumes.prune()
        
        result = {
            "containers_deleted": containers_result.get("ContainersDeleted", []),
            "images_deleted": images_result.get("ImagesDeleted", []),
            "networks_deleted": networks_result.get("NetworksDeleted", []),
            "volumes_deleted": volumes_result.get("VolumesDeleted", []) if volumes else [],
            "space_reclaimed": sum([
                containers_result.get("SpaceReclaimed", 0),
                images_result.get("SpaceReclaimed", 0),
                networks_result.get("SpaceReclaimed", 0),
                volumes_result.get("SpaceReclaimed", 0) if volumes else 0
            ])
        }
        
        task_manager.update_task(
            task_id,
            status="completed",
            progress=100,
            result=result
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to prune system: {str(e)}")
        task_manager.update_task(
            task_id,
            status="failed",
            error=str(e)
        )
        raise