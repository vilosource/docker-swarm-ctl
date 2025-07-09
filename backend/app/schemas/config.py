"""
Swarm config schemas
"""

from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import base64


class ConfigSpec(BaseModel):
    """Config specification"""
    name: str = Field(..., alias="Name", description="Config name")
    labels: Dict[str, str] = Field(default_factory=dict, alias="Labels")
    data: Optional[str] = Field(None, alias="Data", description="Base64 encoded config data")
    templating: Optional[Dict] = Field(None, alias="Templating")
    
    class Config:
        populate_by_name = True


class ConfigCreate(BaseModel):
    """Config creation request"""
    name: str = Field(..., description="Config name")
    data: str = Field(..., description="Config data (will be base64 encoded)")
    labels: Dict[str, str] = Field(default_factory=dict, description="Config labels")
    templating: Optional[Dict] = Field(None, description="Templating driver")
    
    def get_encoded_data(self) -> bytes:
        """Get base64 encoded data as bytes"""
        if self.data:
            # If data is not already base64 encoded, encode it
            try:
                # Try to decode to check if it's already base64
                base64.b64decode(self.data)
                return self.data.encode()
            except:
                # Not base64, encode it
                return base64.b64encode(self.data.encode())
        return b""


class Config(BaseModel):
    """Swarm config information"""
    id: str = Field(..., alias="ID")
    version: Optional[Dict[str, int]] = Field(None, alias="Version")
    created_at: Optional[datetime] = Field(None, alias="CreatedAt")
    updated_at: Optional[datetime] = Field(None, alias="UpdatedAt")
    spec: Optional[ConfigSpec] = Field(None, alias="Spec")
    
    # Computed fields
    name: str = Field(None)
    labels: Dict[str, str] = Field(None)
    data: Optional[str] = Field(None)
    
    class Config:
        populate_by_name = True
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set computed fields
        if self.spec:
            self.name = self.spec.name
            self.labels = self.spec.labels
            self.data = self.spec.data


class ConfigReference(BaseModel):
    """Config reference for service creation"""
    config_id: str = Field(..., alias="ConfigID", description="Config ID")
    config_name: str = Field(..., alias="ConfigName", description="Config name")
    file_name: Optional[str] = Field(None, alias="File", description="Target file name")
    file_uid: Optional[str] = Field(None, alias="UID", description="File UID")
    file_gid: Optional[str] = Field(None, alias="GID", description="File GID")
    file_mode: Optional[int] = Field(None, alias="Mode", description="File mode")
    
    class Config:
        populate_by_name = True


class ConfigListFilters(BaseModel):
    """Filters for listing configs"""
    id: Optional[List[str]] = Field(None, description="Config IDs")
    label: Optional[List[str]] = Field(None, description="Config labels (e.g., 'key=value')")
    name: Optional[List[str]] = Field(None, description="Config names")


class ConfigListResponse(BaseModel):
    """Response for listing configs"""
    configs: List[Config]
    total: int