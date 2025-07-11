"""
Wizard Framework Models

Provides database models for the wizard system that guides users
through multi-step configuration processes.
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.base import Base


class WizardStatus(str, enum.Enum):
    """Status of a wizard instance"""
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class WizardType(str, enum.Enum):
    """Types of wizards available in the system"""
    ssh_host_setup = "ssh_host_setup"
    swarm_init = "swarm_init"
    service_deployment = "service_deployment"
    backup_config = "backup_config"


class WizardInstance(Base):
    """
    Represents an instance of a wizard for a specific user and resource.
    
    Stores the current state, progress, and configuration data for wizards
    that can be paused and resumed.
    """
    __tablename__ = "wizard_instances"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User who started the wizard
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Wizard metadata
    wizard_type = Column(String(50), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    
    # Resource being configured (e.g., host_id for SSH setup)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    resource_type = Column(String(50), nullable=True)
    
    # Progress tracking
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, nullable=False)
    status = Column(String(20), default=WizardStatus.in_progress)
    
    # State storage (JSON for flexibility)
    state = Column(JSONB, nullable=False, default=dict)
    wizard_metadata = Column("metadata", JSONB, default=dict)  # Additional data like error messages, test results
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="wizard_instances")
    
    def to_dict(self):
        """Convert wizard instance to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "wizard_type": self.wizard_type,
            "version": self.version,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "resource_type": self.resource_type,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "status": self.status,
            "state": self.state,
            "metadata": self.wizard_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    def can_resume(self) -> bool:
        """Check if wizard can be resumed"""
        return self.status == WizardStatus.in_progress
    
    def is_completed(self) -> bool:
        """Check if wizard is completed"""
        return self.status == WizardStatus.completed
    
    def get_progress_percentage(self) -> float:
        """Calculate progress as percentage"""
        if self.total_steps == 0:
            return 0.0
        return (self.current_step / self.total_steps) * 100