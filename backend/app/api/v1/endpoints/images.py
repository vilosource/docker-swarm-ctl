from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.core.security import get_current_active_user, require_role
from app.core.rate_limit import rate_limit
from app.schemas.image import ImageResponse, ImagePull
from app.services.docker_client import get_docker_client
from app.services.audit import AuditService
from app.models.user import User
from app.utils.tasks import task_manager


router = APIRouter()


def format_image(image) -> ImageResponse:
    return ImageResponse(
        id=image.id.split(':')[1][:12] if ':' in image.id else image.id[:12],
        tags=image.tags,
        created=image.attrs["Created"],
        size=image.attrs["Size"],
        labels=image.labels or {}
    )


@router.get("/", response_model=List[ImageResponse])
async def list_images(
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    images = client.images.list()
    return [format_image(img) for img in images]


@router.post("/pull")
@rate_limit("10/hour")
async def pull_image(
    request: Request,
    image_data: ImagePull,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db)
):
    task_id = str(uuid.uuid4())
    
    # Create background task
    async def pull_task():
        client = get_docker_client()
        try:
            task_manager.update_task(task_id, "in_progress", "Pulling image...")
            
            image = client.images.pull(
                image_data.repository,
                tag=image_data.tag,
                auth_config=image_data.auth_config
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
    
    # Log the action
    audit_service = AuditService(db)
    await audit_service.log(
        user=current_user,
        action="image.pull",
        details={
            "repository": image_data.repository,
            "tag": image_data.tag,
            "task_id": task_id
        },
        request=request
    )
    
    return {
        "task_id": task_id,
        "message": f"Image pull started for {image_data.repository}:{image_data.tag}"
    }


@router.get("/{image_id}")
async def get_image(
    image_id: str,
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    
    try:
        image = client.images.get(image_id)
        return format_image(image)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found")


@router.delete("/{image_id}")
@rate_limit("30/hour")
async def remove_image(
    request: Request,
    image_id: str,
    force: bool = False,
    current_user: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db)
):
    client = get_docker_client()
    
    try:
        client.images.remove(image_id, force=force)
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="image.delete",
            resource_type="image",
            resource_id=image_id,
            details={"force": force},
            request=request
        )
        
        return {"message": f"Image {image_id} removed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{image_id}/history")
async def get_image_history(
    image_id: str,
    current_user: User = Depends(get_current_active_user)
):
    client = get_docker_client()
    
    try:
        image = client.images.get(image_id)
        history = image.history()
        
        return {
            "image_id": image_id,
            "history": [
                {
                    "created": h.get("Created"),
                    "created_by": h.get("CreatedBy"),
                    "size": h.get("Size", 0),
                    "comment": h.get("Comment", "")
                }
                for h in history
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/prune")
@rate_limit("5/hour")
async def prune_images(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    client = get_docker_client()
    
    try:
        result = client.images.prune()
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log(
            user=current_user,
            action="image.prune",
            details=result,
            request=request
        )
        
        return {
            "message": "Image prune completed",
            "images_deleted": result.get("ImagesDeleted", []),
            "space_reclaimed": result.get("SpaceReclaimed", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))