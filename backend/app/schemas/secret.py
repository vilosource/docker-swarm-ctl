"""
Swarm secret schemas
"""

from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import base64


class SecretSpec(BaseModel):
    """Secret specification"""
    name: str = Field(..., alias="Name", description="Secret name")
    labels: Dict[str, str] = Field(default_factory=dict, alias="Labels")
    data: Optional[str] = Field(None, alias="Data", description="Base64 encoded secret data")
    driver: Optional[Dict] = Field(None, alias="Driver")
    templating: Optional[Dict] = Field(None, alias="Templating")
    
    class Config:
        allow_population_by_field_name = True


class SecretCreate(BaseModel):
    """Secret creation request"""
    name: str = Field(..., description="Secret name")
    data: str = Field(..., description="Secret data (will be base64 encoded)")
    labels: Dict[str, str] = Field(default_factory=dict, description="Secret labels")
    driver: Optional[Dict] = Field(None, description="Secret driver")
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


class Secret(BaseModel):
    """Swarm secret information"""
    id: str = Field(..., alias="ID")
    version: Dict[str, int] = Field(..., alias="Version")
    created_at: datetime = Field(..., alias="CreatedAt")
    updated_at: datetime = Field(..., alias="UpdatedAt")
    spec: SecretSpec = Field(..., alias="Spec")
    
    # Computed fields
    name: str = Field(None)
    labels: Dict[str, str] = Field(None)
    
    class Config:
        allow_population_by_field_name = True
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set computed fields
        if self.spec:
            self.name = self.spec.name
            self.labels = self.spec.labels


class SecretReference(BaseModel):
    """Secret reference for service creation"""
    secret_id: str = Field(..., alias="SecretID", description="Secret ID")
    secret_name: str = Field(..., alias="SecretName", description="Secret name")
    file_name: Optional[str] = Field(None, alias="File", description="Target file name")
    file_uid: Optional[str] = Field(None, alias="UID", description="File UID")
    file_gid: Optional[str] = Field(None, alias="GID", description="File GID")
    file_mode: Optional[int] = Field(None, alias="Mode", description="File mode")
    
    class Config:
        allow_population_by_field_name = True


class SecretListFilters(BaseModel):
    """Filters for listing secrets"""
    id: Optional[List[str]] = Field(None, description="Secret IDs")
    label: Optional[List[str]] = Field(None, description="Secret labels (e.g., 'key=value')")
    name: Optional[List[str]] = Field(None, description="Secret names")


class SecretListResponse(BaseModel):
    """Response for listing secrets"""
    secrets: List[Secret]
    total: int