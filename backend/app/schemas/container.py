from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re


class ContainerCreate(BaseModel):
    image: str = Field(
        ...,
        description="Docker image name with tag"
    )
    name: Optional[str] = Field(
        None,
        max_length=64
    )
    command: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    ports: Optional[Dict[str, int]] = None
    volumes: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None
    restart_policy: Optional[str] = Field(None, pattern="^(no|always|on-failure|unless-stopped)$")
    
    @validator("image")
    def validate_image(cls, v):
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.\-/]*(:[\w][\w.-]{0,127})?$", v):
            raise ValueError("Invalid image name format")
        return v
    
    @validator("name")
    def validate_name(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]+$", v):
            raise ValueError("Container name can only contain letters, numbers, hyphens, dots, and underscores")
        return v
    
    @validator("command")
    def validate_command(cls, v):
        if v:
            forbidden_patterns = [
                r'[;&|`$]',
                r'\$\(',
                r'>\s*/',
            ]
            for cmd in v:
                for pattern in forbidden_patterns:
                    if re.search(pattern, cmd):
                        raise ValueError(f"Forbidden pattern in command")
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        if v:
            for key in v.keys():
                if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                    raise ValueError(f"Invalid environment variable name: {key}")
        return v
    
    @validator("volumes")
    def validate_volumes(cls, v):
        if v:
            forbidden_paths = [
                '/etc', '/root', '/home', '/var/run/docker.sock',
                '/proc', '/sys', '/dev'
            ]
            for volume in v:
                host_path = volume.split(':')[0]
                for fp in forbidden_paths:
                    if host_path.startswith(fp):
                        raise ValueError(f"Forbidden host path: {host_path}")
        return v


class ContainerResponse(BaseModel):
    id: str
    name: str
    image: str
    status: str
    state: str
    created: datetime
    ports: Dict[str, Any]
    labels: Dict[str, str]
    host_id: Optional[str] = Field(None, description="Docker host ID (for multi-host deployments)")
    
    class Config:
        from_attributes = True


class ContainerStats(BaseModel):
    cpu_percent: float
    memory_usage: int
    memory_limit: int
    memory_percent: float
    network_rx: int
    network_tx: int
    block_read: int
    block_write: int
    pids: int


class ContainerInspect(BaseModel):
    id: str
    name: str
    image: str
    config: Dict[str, Any]
    environment: List[str]
    mounts: List[Dict[str, Any]]
    network_settings: Dict[str, Any]
    state: Dict[str, Any]
    host_config: Dict[str, Any]