"""
Swarm management schemas
"""

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SwarmSpec(BaseModel):
    """Swarm specification"""
    name: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)
    orchestration: Optional[Dict] = None
    raft: Optional[Dict] = None
    dispatcher: Optional[Dict] = None
    ca_config: Optional[Dict] = Field(None, alias="CAConfig")
    encryption_config: Optional[Dict] = Field(None, alias="EncryptionConfig")
    task_defaults: Optional[Dict] = Field(None, alias="TaskDefaults")


class SwarmInfo(BaseModel):
    """Swarm information response"""
    id: str = Field(..., alias="ID")
    created_at: datetime = Field(..., alias="CreatedAt")
    updated_at: datetime = Field(..., alias="UpdatedAt")
    spec: SwarmSpec = Field(..., alias="Spec")
    version: Dict[str, int] = Field(..., alias="Version")
    join_tokens: Dict[str, str] = Field(..., alias="JoinTokens")
    root_ca_cert: str = Field(..., alias="RootCACert", description="Root CA certificate (PEM format)")
    
    class Config:
        populate_by_name = True


class SwarmInit(BaseModel):
    """Swarm initialization request"""
    advertise_addr: str = Field(..., description="Externally reachable address advertised to nodes")
    listen_addr: str = Field("0.0.0.0:2377", description="Listen address for inter-manager communication")
    force_new_cluster: bool = Field(False, description="Force creating a new cluster from this node")
    default_addr_pool: Optional[List[str]] = Field(None, description="Default address pools for global scope networks")
    subnet_size: Optional[int] = Field(None, description="Subnet size for default address pools")
    data_path_addr: Optional[str] = Field(None, description="Address for data path traffic")
    data_path_port: Optional[int] = Field(None, description="Port for data path traffic")
    spec: Optional[SwarmSpec] = Field(None, description="Initial swarm specification")


class SwarmJoin(BaseModel):
    """Swarm join request"""
    remote_addrs: List[str] = Field(..., description="Addresses of manager nodes already in the swarm")
    join_token: str = Field(..., description="Secret token to join the swarm")
    advertise_addr: Optional[str] = Field(None, description="Externally reachable address advertised to nodes")
    listen_addr: str = Field("0.0.0.0:2377", description="Listen address for inter-manager communication")
    data_path_addr: Optional[str] = Field(None, description="Address for data path traffic")


class SwarmLeave(BaseModel):
    """Swarm leave request"""
    force: bool = Field(False, description="Force leave swarm, even if this is the last manager")


class SwarmUpdate(BaseModel):
    """Swarm update request"""
    version: int = Field(..., description="The version number of the swarm object being updated")
    rotate_worker_token: bool = Field(False, description="Rotate the worker join token")
    rotate_manager_token: bool = Field(False, description="Rotate the manager join token")
    rotate_manager_unlock_key: bool = Field(False, description="Rotate the manager unlock key")
    spec: Optional[SwarmSpec] = Field(None, description="New swarm specification")


class SwarmTokens(BaseModel):
    """Swarm join tokens response"""
    worker: str = Field(..., description="Worker join token")
    manager: str = Field(..., description="Manager join token")


class SwarmUnlockKey(BaseModel):
    """Swarm unlock key response"""
    unlock_key: str = Field(..., description="Unlock key for encrypted swarm")