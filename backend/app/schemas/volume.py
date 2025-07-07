"""
Volume schemas for Docker volume management
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class VolumeCreate(BaseModel):
    """Schema for creating a volume"""
    name: Optional[str] = Field(None, description="Volume name")
    driver: str = Field("local", description="Volume driver")
    driver_opts: Optional[Dict[str, str]] = Field(None, description="Driver options")
    labels: Optional[Dict[str, str]] = Field(None, description="Volume labels")


class VolumeResponse(BaseModel):
    """Schema for volume response"""
    name: str
    driver: str
    mountpoint: str
    created_at: Optional[datetime] = Field(None, alias="CreatedAt")
    status: Optional[Dict[str, Any]] = Field(None, description="Volume status")
    labels: Dict[str, str] = Field(default_factory=dict)
    scope: str = Field("local")
    options: Optional[Dict[str, str]] = Field(None)
    host_id: Optional[str] = Field(None, description="Docker host ID")
    host_name: Optional[str] = Field(None, description="Docker host name")
    
    class Config:
        populate_by_name = True


class VolumeInspect(BaseModel):
    """Schema for detailed volume inspection"""
    name: str = Field(..., alias="Name")
    driver: str = Field(..., alias="Driver")
    mountpoint: str = Field(..., alias="Mountpoint")
    created_at: datetime = Field(..., alias="CreatedAt")
    status: Optional[Dict[str, Any]] = Field(None, alias="Status")
    labels: Dict[str, str] = Field(default_factory=dict, alias="Labels")
    scope: str = Field(..., alias="Scope")
    options: Optional[Dict[str, str]] = Field(None, alias="Options")
    usage_data: Optional[Dict[str, Any]] = Field(None, alias="UsageData")
    
    class Config:
        populate_by_name = True


class VolumePruneResponse(BaseModel):
    """Response from volume prune operation"""
    volumes_deleted: List[str] = Field(default_factory=list)
    space_reclaimed: int = Field(0)