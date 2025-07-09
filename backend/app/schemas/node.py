"""
Swarm node schemas
"""

from typing import Dict, Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class NodeSpec(BaseModel):
    """Node specification"""
    name: Optional[str] = Field(None, alias="Name")
    labels: Dict[str, str] = Field(default_factory=dict, alias="Labels")
    role: str = Field(..., alias="Role", description="Node role: 'worker' or 'manager'")
    availability: str = Field(..., alias="Availability", description="Node availability: 'active', 'pause', or 'drain'")
    
    class Config:
        populate_by_name = True


class NodeDescription(BaseModel):
    """Node description"""
    hostname: str = Field(..., alias="Hostname")
    platform: Dict[str, str] = Field(..., alias="Platform")
    resources: Dict[str, int] = Field(..., alias="Resources", description="CPU and memory resources")
    engine: Dict[str, Any] = Field(..., alias="Engine", description="Docker engine info")
    tls_info: Optional[Dict] = Field(None, alias="TLSInfo")
    
    class Config:
        populate_by_name = True


class NodeStatus(BaseModel):
    """Node status"""
    state: str = Field(..., alias="State", description="Node state: 'unknown', 'down', or 'ready'")
    message: Optional[str] = Field(None, alias="Message")
    addr: Optional[str] = Field(None, alias="Addr", description="IP address of the node")
    
    class Config:
        populate_by_name = True


class NodeManagerStatus(BaseModel):
    """Manager node status"""
    leader: bool = Field(False, alias="Leader")
    reachability: str = Field(..., alias="Reachability", description="'unknown', 'unreachable', or 'reachable'")
    addr: str = Field(..., alias="Addr", description="Manager address")
    
    class Config:
        populate_by_name = True


class Node(BaseModel):
    """Swarm node information"""
    id: str = Field(..., alias="ID")
    version: Dict[str, int] = Field(..., alias="Version")
    created_at: datetime = Field(..., alias="CreatedAt")
    updated_at: datetime = Field(..., alias="UpdatedAt")
    spec: NodeSpec = Field(..., alias="Spec")
    description: NodeDescription = Field(..., alias="Description")
    status: NodeStatus = Field(..., alias="Status")
    manager_status: Optional[NodeManagerStatus] = Field(None, alias="ManagerStatus")
    
    # Computed fields for easier access
    hostname: str = Field(None)
    role: str = Field(None)
    availability: str = Field(None)
    state: str = Field(None)
    addr: Optional[str] = Field(None)
    engine_version: str = Field(None)
    
    class Config:
        populate_by_name = True
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set computed fields
        if self.description:
            self.hostname = self.description.hostname
            self.engine_version = self.description.engine.get("EngineVersion", "")
        if self.spec:
            self.role = self.spec.role
            self.availability = self.spec.availability
        if self.status:
            self.state = self.status.state
            self.addr = self.status.addr


class NodeUpdate(BaseModel):
    """Node update request"""
    version: int = Field(..., description="The version number of the node object being updated")
    spec: NodeSpec = Field(..., description="Updated node specification")


class NodeListFilters(BaseModel):
    """Filters for listing nodes"""
    id: Optional[List[str]] = Field(None, description="Node IDs")
    label: Optional[List[str]] = Field(None, description="Node labels (e.g., 'key=value')")
    name: Optional[List[str]] = Field(None, description="Node names")
    role: Optional[List[str]] = Field(None, description="Node roles ('worker' or 'manager')")


class NodeListResponse(BaseModel):
    """Response for listing nodes"""
    nodes: List[Node]
    total: int