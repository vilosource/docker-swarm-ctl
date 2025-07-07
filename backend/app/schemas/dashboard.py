"""
Dashboard schemas for multi-host aggregated statistics
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, UUID4

from app.models import HostStatus


class HostStats(BaseModel):
    """Per-host statistics for dashboard"""
    containers: int = Field(0, description="Total containers on host")
    containers_running: int = Field(0, description="Running containers")
    containers_stopped: int = Field(0, description="Stopped containers")
    containers_paused: int = Field(0, description="Paused containers")
    images: int = Field(0, description="Total images")
    docker_version: Optional[str] = None
    os_type: Optional[str] = None
    architecture: Optional[str] = None
    memory_total: Optional[int] = None
    cpu_count: Optional[int] = None


class HostSummary(BaseModel):
    """Host summary for dashboard display"""
    id: UUID4
    name: str
    display_name: Optional[str]
    status: HostStatus
    last_health_check: Optional[datetime]
    is_default: bool
    stats: HostStats


class HostOverview(BaseModel):
    """Overview of all hosts"""
    total: int = Field(0, description="Total number of hosts")
    healthy: int = Field(0, description="Number of healthy hosts")
    unhealthy: int = Field(0, description="Number of unhealthy hosts") 
    unreachable: int = Field(0, description="Number of unreachable hosts")
    pending: int = Field(0, description="Number of pending hosts")


class ResourceStats(BaseModel):
    """Aggregated resource statistics across all hosts"""
    containers: dict = Field(
        default_factory=lambda: {
            "total": 0,
            "running": 0,
            "stopped": 0,
            "paused": 0
        }
    )
    images: dict = Field(
        default_factory=lambda: {
            "total": 0,
            "size": 0
        }
    )
    volumes: dict = Field(
        default_factory=lambda: {
            "total": 0,
            "size": 0
        }
    )
    networks: dict = Field(
        default_factory=lambda: {
            "total": 0
        }
    )


class DashboardResponse(BaseModel):
    """Complete dashboard response with multi-host data"""
    hosts: HostOverview
    resources: ResourceStats
    host_details: List[HostSummary]
    generated_at: datetime = Field(default_factory=datetime.utcnow)