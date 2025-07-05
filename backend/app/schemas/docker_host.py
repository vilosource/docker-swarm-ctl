from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, UUID4, validator

from app.models import HostType, ConnectionType, HostStatus


class HostCredentialCreate(BaseModel):
    credential_type: str = Field(..., description="Type of credential (tls_cert, tls_key, tls_ca, ssh_key)")
    credential_value: str = Field(..., description="The credential value (will be encrypted)")
    credential_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class HostTagCreate(BaseModel):
    tag_name: str = Field(..., min_length=1, max_length=100)
    tag_value: Optional[str] = Field(None, max_length=255)


class DockerHostCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Unique host name")
    description: Optional[str] = Field(None, description="Host description")
    host_type: HostType = Field(HostType.standalone, description="Type of Docker host")
    connection_type: ConnectionType = Field(ConnectionType.tcp, description="Connection method")
    host_url: str = Field(..., description="Connection URL (e.g., tcp://192.168.1.100:2376)")
    is_active: bool = Field(True, description="Whether the host is active")
    is_default: bool = Field(False, description="Set as default host")
    tags: Optional[List[HostTagCreate]] = Field([], description="Host tags")
    credentials: Optional[List[HostCredentialCreate]] = Field([], description="Host credentials")
    
    @validator('host_url')
    def validate_host_url(cls, v, values):
        connection_type = values.get('connection_type')
        if connection_type == 'unix' and not v.startswith('unix://'):
            raise ValueError('Unix socket URL must start with unix://')
        elif connection_type == 'tcp' and not (v.startswith('tcp://') or v.startswith('https://')):
            raise ValueError('TCP URL must start with tcp:// or https://')
        elif connection_type == 'ssh' and not v.startswith('ssh://'):
            raise ValueError('SSH URL must start with ssh://')
        return v


class DockerHostUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    host_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class HostCredentialResponse(BaseModel):
    id: UUID4
    credential_type: str
    credential_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class HostTagResponse(BaseModel):
    id: UUID4
    tag_name: str
    tag_value: Optional[str]
    
    class Config:
        from_attributes = True


class DockerHostResponse(BaseModel):
    id: UUID4
    name: str
    description: Optional[str]
    host_type: HostType
    connection_type: ConnectionType
    host_url: str
    is_active: bool
    is_default: bool
    status: HostStatus
    last_health_check: Optional[datetime]
    docker_version: Optional[str]
    api_version: Optional[str]
    os_type: Optional[str]
    architecture: Optional[str]
    swarm_id: Optional[str]
    cluster_name: Optional[str]
    is_leader: bool
    created_at: datetime
    updated_at: datetime
    tags: List[HostTagResponse] = []
    
    class Config:
        from_attributes = True


class DockerHostListResponse(BaseModel):
    items: List[DockerHostResponse]
    total: int
    page: int = 1
    per_page: int = 50


class HostConnectionTest(BaseModel):
    success: bool
    message: str
    docker_version: Optional[str] = None
    api_version: Optional[str] = None
    error: Optional[str] = None


class UserHostPermissionCreate(BaseModel):
    user_id: UUID4
    permission_level: str = Field(..., pattern="^(viewer|operator|admin)$")


class UserHostPermissionResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    host_id: UUID4
    permission_level: str
    granted_by: Optional[UUID4]
    granted_at: datetime
    
    class Config:
        from_attributes = True