"""
Swarm task schemas
"""

from typing import Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TaskState(BaseModel):
    """Task state information"""
    timestamp: datetime = Field(..., alias="Timestamp")
    state: str = Field(..., alias="State", description="Task state: 'new', 'allocated', 'pending', 'assigned', 'accepted', 'preparing', 'ready', 'starting', 'running', 'complete', 'shutdown', 'failed', 'rejected'")
    message: Optional[str] = Field(None, alias="Message")
    err: Optional[str] = Field(None, alias="Err")
    container_exit_code: Optional[int] = Field(None, alias="ContainerExit")
    
    class Config:
        allow_population_by_field_name = True


class TaskStatus(BaseModel):
    """Task status"""
    timestamp: datetime = Field(..., alias="Timestamp")
    state: str = Field(..., alias="State")
    message: Optional[str] = Field(None, alias="Message")
    err: Optional[str] = Field(None, alias="Err")
    container_status: Optional[Dict] = Field(None, alias="ContainerStatus")
    
    class Config:
        allow_population_by_field_name = True


class Task(BaseModel):
    """Swarm task information"""
    id: str = Field(..., alias="ID")
    version: Dict[str, int] = Field(..., alias="Version")
    created_at: datetime = Field(..., alias="CreatedAt")
    updated_at: datetime = Field(..., alias="UpdatedAt")
    
    # Task details
    name: Optional[str] = Field(None, alias="Name")
    labels: Dict[str, str] = Field(default_factory=dict, alias="Labels")
    
    # Task specification
    spec: Dict = Field(..., alias="Spec")
    service_id: str = Field(..., alias="ServiceID")
    slot: Optional[int] = Field(None, alias="Slot")
    node_id: Optional[str] = Field(None, alias="NodeID")
    
    # Status
    status: TaskStatus = Field(..., alias="Status")
    desired_state: str = Field(..., alias="DesiredState")
    
    # Computed fields
    container_id: Optional[str] = Field(None)
    state: str = Field(None)
    
    class Config:
        allow_population_by_field_name = True
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set computed fields
        if self.status:
            self.state = self.status.state
            if self.status.container_status:
                self.container_id = self.status.container_status.get("ContainerID")


class TaskListFilters(BaseModel):
    """Filters for listing tasks"""
    id: Optional[List[str]] = Field(None, description="Task IDs")
    label: Optional[List[str]] = Field(None, description="Task labels (e.g., 'key=value')")
    service: Optional[List[str]] = Field(None, description="Service names or IDs")
    node: Optional[List[str]] = Field(None, description="Node IDs")
    desired_state: Optional[List[str]] = Field(None, description="Desired states")


class TaskListResponse(BaseModel):
    """Response for listing tasks"""
    tasks: List[Task]
    total: int