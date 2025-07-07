"""
Network schemas for Docker network management
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class NetworkCreate(BaseModel):
    """Schema for creating a network"""
    name: str = Field(..., description="Network name")
    driver: str = Field("bridge", description="Network driver")
    options: Optional[Dict[str, str]] = Field(None, description="Driver options")
    ipam: Optional[Dict[str, Any]] = Field(None, description="IPAM configuration")
    enable_ipv6: bool = Field(False, description="Enable IPv6")
    internal: bool = Field(False, description="Internal network")
    attachable: bool = Field(True, description="Attachable network")
    labels: Optional[Dict[str, str]] = Field(None, description="Network labels")


class NetworkResponse(BaseModel):
    """Schema for network response"""
    id: str = Field(..., alias="Id")
    name: str = Field(..., alias="Name")
    driver: str = Field(..., alias="Driver")
    scope: str = Field(..., alias="Scope")
    ipam: Optional[Dict[str, Any]] = Field(None, alias="IPAM")
    internal: bool = Field(False, alias="Internal")
    attachable: bool = Field(False, alias="Attachable")
    ingress: bool = Field(False, alias="Ingress")
    containers: Dict[str, Dict[str, Any]] = Field(default_factory=dict, alias="Containers")
    options: Optional[Dict[str, str]] = Field(None, alias="Options")
    labels: Dict[str, str] = Field(default_factory=dict, alias="Labels")
    created: Optional[datetime] = Field(None, alias="Created")
    enable_ipv6: bool = Field(False, alias="EnableIPv6")
    host_id: Optional[str] = Field(None, description="Docker host ID")
    host_name: Optional[str] = Field(None, description="Docker host name")
    
    class Config:
        populate_by_name = True


class NetworkInspect(BaseModel):
    """Schema for detailed network inspection"""
    name: str = Field(..., alias="Name")
    id: str = Field(..., alias="Id")
    created: datetime = Field(..., alias="Created")
    scope: str = Field(..., alias="Scope")
    driver: str = Field(..., alias="Driver")
    enable_ipv6: bool = Field(..., alias="EnableIPv6")
    ipam: Dict[str, Any] = Field(..., alias="IPAM")
    internal: bool = Field(..., alias="Internal")
    attachable: bool = Field(..., alias="Attachable")
    ingress: bool = Field(..., alias="Ingress")
    config_from: Optional[Dict[str, Any]] = Field(None, alias="ConfigFrom")
    config_only: bool = Field(False, alias="ConfigOnly")
    containers: Dict[str, Dict[str, Any]] = Field(default_factory=dict, alias="Containers")
    options: Optional[Dict[str, str]] = Field(None, alias="Options")
    labels: Dict[str, str] = Field(default_factory=dict, alias="Labels")
    
    class Config:
        populate_by_name = True


class NetworkConnect(BaseModel):
    """Schema for connecting container to network"""
    container: str = Field(..., description="Container ID or name")
    endpoint_config: Optional[Dict[str, Any]] = Field(None, description="Endpoint configuration")


class NetworkDisconnect(BaseModel):
    """Schema for disconnecting container from network"""
    container: str = Field(..., description="Container ID or name")
    force: bool = Field(False, description="Force disconnection")


class NetworkPruneResponse(BaseModel):
    """Response from network prune operation"""
    networks_deleted: List[str] = Field(default_factory=list)