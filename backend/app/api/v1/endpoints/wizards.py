"""
Wizard API Endpoints

Provides REST API for the wizard framework.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models import User, WizardStatus, WizardType
from app.services.wizard_service import get_wizard_service
from app.schemas.wizard import (
    WizardCreate,
    WizardResponse,
    WizardListResponse,
    WizardStepUpdate,
    WizardTestRequest,
    WizardTestResult,
    WizardCompletionResult
)
from app.services.wizards.ssh_host_wizard import SSHHostWizard
from app.api.decorators import audit_operation
from app.api.decorators_enhanced import handle_api_errors, standard_response
from app.core.exceptions import ValidationError, NotFoundError


router = APIRouter()


@router.post("/start", response_model=WizardResponse)
@handle_api_errors("start_wizard")
@audit_operation("wizard.start", "wizard")
async def start_wizard(
    request: Request,
    wizard_data: WizardCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a new wizard"""
    wizard_service = get_wizard_service(db)
    
    wizard = await wizard_service.create_wizard(
        user=current_user,
        wizard_type=wizard_data.wizard_type,
        resource_id=wizard_data.resource_id,
        resource_type=wizard_data.resource_type,
        initial_state=wizard_data.initial_state
    )
    
    return WizardResponse.from_orm(wizard)


@router.get("/my-pending", response_model=WizardListResponse)
@handle_api_errors("list_pending_wizards")
async def list_pending_wizards(
    wizard_type: Optional[WizardType] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's pending wizards"""
    wizard_service = get_wizard_service(db)
    
    wizards = await wizard_service.list_user_wizards(
        user=current_user,
        status=WizardStatus.in_progress,
        wizard_type=wizard_type
    )
    
    return WizardListResponse(
        wizards=[WizardResponse.from_orm(w) for w in wizards],
        total=len(wizards)
    )


@router.get("/{wizard_id}", response_model=WizardResponse)
@handle_api_errors("get_wizard")
async def get_wizard(
    wizard_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get wizard details"""
    wizard_service = get_wizard_service(db)
    
    wizard = await wizard_service.get_wizard(
        wizard_id=wizard_id,
        user=current_user
    )
    
    return WizardResponse.from_orm(wizard)


@router.put("/{wizard_id}/step", response_model=WizardResponse)
@handle_api_errors("update_wizard_step")
@audit_operation("wizard.update_step", "wizard", lambda r: r.id)
async def update_wizard_step(
    request: Request,
    wizard_id: str,
    step_update: WizardStepUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current wizard step data"""
    wizard_service = get_wizard_service(db)
    
    wizard = await wizard_service.update_step(
        wizard_id=wizard_id,
        user=current_user,
        step_data=step_update.step_data
    )
    
    return WizardResponse.from_orm(wizard)


@router.post("/{wizard_id}/next", response_model=WizardResponse)
@handle_api_errors("next_wizard_step")
@audit_operation("wizard.next_step", "wizard", lambda r: r.id)
async def next_wizard_step(
    request: Request,
    wizard_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Move to next wizard step"""
    wizard_service = get_wizard_service(db)
    
    wizard = await wizard_service.next_step(
        wizard_id=wizard_id,
        user=current_user
    )
    
    return WizardResponse.from_orm(wizard)


@router.post("/{wizard_id}/back", response_model=WizardResponse)
@handle_api_errors("previous_wizard_step")
@audit_operation("wizard.previous_step", "wizard", lambda r: r.id)
async def previous_wizard_step(
    request: Request,
    wizard_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Go back to previous wizard step"""
    wizard_service = get_wizard_service(db)
    
    wizard = await wizard_service.previous_step(
        wizard_id=wizard_id,
        user=current_user
    )
    
    return WizardResponse.from_orm(wizard)


@router.post("/{wizard_id}/test", response_model=WizardTestResult)
@handle_api_errors("test_wizard_step")
async def test_wizard_step(
    wizard_id: str,
    test_request: WizardTestRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Run test/validation for current wizard step"""
    wizard_service = get_wizard_service(db)
    
    result = await wizard_service.test_step(
        wizard_id=wizard_id,
        user=current_user,
        test_type=test_request.test_type
    )
    
    return WizardTestResult(**result)


@router.post("/{wizard_id}/complete", response_model=WizardCompletionResult)
@handle_api_errors("complete_wizard")
@audit_operation("wizard.complete", "wizard", lambda r: r.resource_id if hasattr(r, 'resource_id') else None)
async def complete_wizard(
    request: Request,
    wizard_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete wizard and create resources"""
    wizard_service = get_wizard_service(db)
    
    result = await wizard_service.complete_wizard(
        wizard_id=wizard_id,
        user=current_user
    )
    
    return WizardCompletionResult(
        success=True,
        message="Wizard completed successfully",
        resource_id=result.get("resource_id"),
        resource_type=result.get("resource_type"),
        details=result
    )


@router.delete("/{wizard_id}")
@handle_api_errors("cancel_wizard")
@audit_operation("wizard.cancel", "wizard")
@standard_response("Wizard cancelled successfully")
async def cancel_wizard(
    request: Request,
    wizard_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a wizard"""
    wizard_service = get_wizard_service(db)
    
    await wizard_service.cancel_wizard(
        wizard_id=wizard_id,
        user=current_user
    )
    
    return {"wizard_id": wizard_id}


@router.post("/generate-ssh-key")
@handle_api_errors("generate_ssh_key")
async def generate_ssh_key(
    comment: Optional[str] = Query(None, description="SSH key comment"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a new SSH key pair"""
    ssh_wizard = SSHHostWizard(db)
    
    # Generate key with comment
    if not comment:
        comment = f"docker-control-platform@{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    private_key, public_key = ssh_wizard.generate_ssh_key_pair(comment)
    
    return {
        "private_key": private_key,
        "public_key": public_key,
        "comment": comment
    }