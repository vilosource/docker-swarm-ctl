"""
Wizard Schemas

Pydantic models for wizard API requests and responses.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, UUID4

from app.models import WizardStatus, WizardType


class WizardCreate(BaseModel):
    """Request model for creating a wizard"""
    wizard_type: WizardType = Field(..., description="Type of wizard to create")
    resource_id: Optional[UUID4] = Field(None, description="ID of resource being configured")
    resource_type: Optional[str] = Field(None, description="Type of resource")
    initial_state: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Initial state data")


class WizardStepUpdate(BaseModel):
    """Request model for updating wizard step data"""
    step_data: Dict[str, Any] = Field(..., description="Data for the current step")


class WizardTestRequest(BaseModel):
    """Request model for running wizard step tests"""
    test_type: str = Field(..., description="Type of test to run")


class WizardResponse(BaseModel):
    """Response model for wizard instance"""
    id: UUID4
    user_id: UUID4
    wizard_type: WizardType
    version: int
    resource_id: Optional[UUID4]
    resource_type: Optional[str]
    current_step: int
    total_steps: int
    status: WizardStatus
    state: Dict[str, Any]
    metadata: Dict[str, Any]
    progress_percentage: float
    can_resume: bool
    is_completed: bool
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, wizard):
        """Create response from ORM model"""
        return cls(
            id=wizard.id,
            user_id=wizard.user_id,
            wizard_type=wizard.wizard_type,
            version=wizard.version,
            resource_id=wizard.resource_id,
            resource_type=wizard.resource_type,
            current_step=wizard.current_step,
            total_steps=wizard.total_steps,
            status=wizard.status,
            state=wizard.state,
            metadata=wizard.wizard_metadata,
            progress_percentage=wizard.get_progress_percentage(),
            can_resume=wizard.can_resume(),
            is_completed=wizard.is_completed(),
            created_at=wizard.created_at,
            updated_at=wizard.updated_at,
            completed_at=wizard.completed_at
        )


class WizardListResponse(BaseModel):
    """Response model for list of wizards"""
    wizards: List[WizardResponse]
    total: int


class WizardTestResult(BaseModel):
    """Response model for wizard test results"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WizardCompletionResult(BaseModel):
    """Response model for wizard completion"""
    success: bool
    message: str
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# SSH Host Wizard specific schemas
class SSHConnectionDetails(BaseModel):
    """SSH connection details step data"""
    host_url: str = Field(..., description="SSH URL (ssh://user@host:port)")
    connection_name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    host_type: str = Field("standalone", pattern="^(standalone|swarm_manager|swarm_worker)$")
    ssh_port: int = Field(22, ge=1, le=65535)
    jump_host: Optional[str] = None
    connection_timeout: int = Field(30, ge=5, le=300)


class SSHAuthentication(BaseModel):
    """SSH authentication step data"""
    auth_method: str = Field(..., pattern="^(existing_key|new_key|password)$")
    private_key: Optional[str] = None
    key_passphrase: Optional[str] = None
    password: Optional[str] = None
    key_comment: Optional[str] = None


class SSHTestResult(BaseModel):
    """SSH connection test result"""
    success: bool
    message: str
    system_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DockerTestResult(BaseModel):
    """Docker API test result"""
    success: bool
    message: str
    docker_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None