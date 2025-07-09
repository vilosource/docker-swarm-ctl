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
    created_at: Optional[datetime] = Field(None, alias="CreatedAt")
    updated_at: Optional[datetime] = Field(None, alias="UpdatedAt")
    spec: Optional[SwarmSpec] = Field(None, alias="Spec")
    version: Optional[Dict[str, int]] = Field(None, alias="Version")
    join_tokens: Optional[Dict[str, str]] = Field(None, alias="JoinTokens")
    root_ca_cert: Optional[str] = Field(None, alias="RootCACert", description="Root CA certificate (PEM format)")
    root_rotation_in_progress: Optional[bool] = Field(None, alias="RootRotationInProgress")
    tls_info: Optional[Dict] = Field(None, alias="TLSInfo")
    cluster_info: Optional[Dict] = Field(None, alias="ClusterInfo")
    
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
    cluster_name: Optional[str] = Field(None, description="User-friendly name for the swarm cluster")
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


class HostInfo(BaseModel):
    """Basic host information for swarm cluster views"""
    id: str
    display_name: str
    host_type: Optional[str] = None
    is_leader: Optional[bool] = False
    url: Optional[str] = None


class SwarmClusterInfo(BaseModel):
    """Swarm cluster information with aggregated data"""
    swarm_id: str
    cluster_name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    manager_count: int = 0
    worker_count: int = 0
    total_nodes: int = 0
    ready_nodes: int = 0
    service_count: int = 0
    leader_host: HostInfo
    hosts: List[HostInfo] = Field(default_factory=list)
    swarm_spec: Optional[Dict] = None
    join_tokens: Optional[Dict[str, str]] = None


class SwarmClusterListResponse(BaseModel):
    """Response for listing swarm clusters"""
    swarms: List[SwarmClusterInfo]
    total: int