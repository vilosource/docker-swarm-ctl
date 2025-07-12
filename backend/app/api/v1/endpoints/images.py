from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Response, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.rate_limit import rate_limit
from app.core.exceptions import ResourceConflictError, ResourceNotFoundError, DockerOperationError
from app.schemas.image import ImageResponse, ImagePull
from app.services.async_docker_service import IAsyncDockerService, AsyncDockerServiceFactory
from app.services.audit import AuditService
from app.models.user import User
from app.utils.tasks import task_manager
from app.api.decorators import audit_operation, handle_docker_errors
from app.api.decorators_enhanced import handle_api_errors


router = APIRouter()


def format_image(image_data) -> ImageResponse:
    """Format async image data for response"""
    # AsyncImageData has properties: id, tags, size, created
    
    # Convert created string to datetime
    created_dt = image_data.created
    if isinstance(created_dt, str):
        try:
            created_dt = datetime.fromisoformat(created_dt.replace('Z', '+00:00'))
        except ValueError:
            created_dt = datetime.utcnow()
    
    return ImageResponse(
        id=image_data.id,
        tags=image_data.tags or [],
        created=created_dt,
        size=image_data.size,
        labels={}  # AsyncImageData doesn't have labels property yet
    )


async def get_docker_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> IAsyncDockerService:
    """Dependency to get async Docker service instance"""
    return AsyncDockerServiceFactory.create(current_user, db, multi_host=True)


@router.get("/", response_model=List[ImageResponse])
@handle_api_errors("list_images")
async def list_images(
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IAsyncDockerService = Depends(get_docker_service)
):
    """List images from specified or default Docker host"""
    images = await docker_service.list_images(host_id=host_id)
    return [format_image(img) for img in images]


@router.post("/pull")
@rate_limit("10/hour")
@handle_api_errors("pull_image")
@audit_operation("image.pull", "image", lambda r: r.get("message", ""))
async def pull_image(
    request: Request,
    response: Response,
    image_data: ImagePull,
    background_tasks: BackgroundTasks,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IAsyncDockerService = Depends(get_docker_service)
):
    """Pull an image from registry to specified or default Docker host"""
    task_id = str(uuid.uuid4())
    
    # Create background task
    async def pull_task():
        try:
            task_manager.update_task(task_id, "in_progress", "Pulling image...")
            
            image = await docker_service.pull_image(
                repository=image_data.repository,
                tag=image_data.tag,
                auth_config=image_data.auth_config,
                host_id=host_id
            )
            
            task_manager.update_task(
                task_id, 
                "completed", 
                f"Successfully pulled {image_data.repository}:{image_data.tag}"
            )
            
            return image
        except Exception as e:
            task_manager.update_task(task_id, "failed", str(e))
            raise
    
    background_tasks.add_task(pull_task)
    
    return {
        "task_id": task_id,
        "message": f"Image pull started for {image_data.repository}:{image_data.tag}"
    }


@router.get("/{image_id}")
@handle_api_errors("get_image")
async def get_image(
    image_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IAsyncDockerService = Depends(get_docker_service)
):
    """Get specific image details from specified or default Docker host"""
    try:
        image = await docker_service.get_image(image_id, host_id=host_id)
        return format_image(image)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found")


@router.delete("/{image_id}")
@rate_limit("30/hour")
@handle_api_errors("remove_image")
@audit_operation("image.delete", "image", lambda r: r.get("message", ""))
async def remove_image(
    request: Request,
    response: Response,
    image_id: str,
    force: bool = False,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
    docker_service: IAsyncDockerService = Depends(get_docker_service)
):
    """Remove an image from specified or default Docker host"""
    await docker_service.remove_image(image_id, force=force, host_id=host_id)
    return {"message": f"Image {image_id} removed"}


@router.get("/{image_id}/history")
@handle_api_errors("get_image_history")
async def get_image_history(
    image_id: str,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    docker_service: IAsyncDockerService = Depends(get_docker_service)
):
    """Get image history from specified or default Docker host"""
    try:
        history = await docker_service.get_image_history(image_id, host_id=host_id)
        return {
            "image_id": image_id,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/prune")
@rate_limit("5/hour")
@handle_api_errors("prune_images")
@audit_operation("image.prune", "system", lambda r: "prune completed")
async def prune_images(
    request: Request,
    response: Response,
    host_id: Optional[str] = Query(None, description="Docker host ID"),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    docker_service: IAsyncDockerService = Depends(get_docker_service)
):
    """Prune unused images from specified or default Docker host"""
    try:
        result = await docker_service.prune_images(host_id=host_id)
        return {
            "message": "Image prune completed",
            "images_deleted": result.get("ImagesDeleted", []),
            "space_reclaimed": result.get("SpaceReclaimed", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))