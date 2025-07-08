"""
Swarm service schemas
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ServiceMode(BaseModel):
    """Service mode configuration"""
    replicated: Optional[Dict[str, int]] = Field(None, alias="Replicated", description="Replicated mode with replica count")
    global_mode: Optional[Dict] = Field(None, alias="Global", description="Global mode (one task per node)")
    replicated_job: Optional[Dict] = Field(None, alias="ReplicatedJob")
    global_job: Optional[Dict] = Field(None, alias="GlobalJob")
    
    class Config:
        allow_population_by_field_name = True


class ServicePort(BaseModel):
    """Service port configuration"""
    name: Optional[str] = Field(None, alias="Name")
    protocol: str = Field("tcp", alias="Protocol", description="Protocol: 'tcp' or 'udp'")
    target_port: int = Field(..., alias="TargetPort", description="Container port")
    published_port: Optional[int] = Field(None, alias="PublishedPort", description="Host port")
    publish_mode: str = Field("ingress", alias="PublishMode", description="'ingress' or 'host'")
    
    class Config:
        allow_population_by_field_name = True


class ServiceMount(BaseModel):
    """Service mount configuration"""
    type: str = Field(..., alias="Type", description="Mount type: 'bind', 'volume', 'tmpfs', or 'npipe'")
    source: Optional[str] = Field(None, alias="Source", description="Mount source")
    target: str = Field(..., alias="Target", description="Container path")
    read_only: bool = Field(False, alias="ReadOnly")
    consistency: Optional[str] = Field(None, alias="Consistency")
    bind_options: Optional[Dict] = Field(None, alias="BindOptions")
    volume_options: Optional[Dict] = Field(None, alias="VolumeOptions")
    tmpfs_options: Optional[Dict] = Field(None, alias="TmpfsOptions")
    
    class Config:
        allow_population_by_field_name = True


class ServicePlacement(BaseModel):
    """Service placement constraints"""
    constraints: List[str] = Field(default_factory=list, alias="Constraints")
    preferences: List[Dict] = Field(default_factory=list, alias="Preferences")
    max_replicas: Optional[int] = Field(None, alias="MaxReplicas")
    platforms: Optional[List[Dict]] = Field(None, alias="Platforms")
    
    class Config:
        allow_population_by_field_name = True


class ServiceResources(BaseModel):
    """Service resource requirements"""
    limits: Optional[Dict[str, Any]] = Field(None, alias="Limits", description="Resource limits")
    reservations: Optional[Dict[str, Any]] = Field(None, alias="Reservations", description="Resource reservations")
    
    class Config:
        allow_population_by_field_name = True


class ServiceRestartPolicy(BaseModel):
    """Service restart policy"""
    condition: str = Field("any", alias="Condition", description="'none', 'on-failure', or 'any'")
    delay: Optional[int] = Field(None, alias="Delay", description="Delay between restarts (ns)")
    max_attempts: Optional[int] = Field(None, alias="MaxAttempts")
    window: Optional[int] = Field(None, alias="Window", description="Window for restart attempts (ns)")
    
    class Config:
        allow_population_by_field_name = True


class ServiceUpdateConfig(BaseModel):
    """Service update configuration"""
    parallelism: int = Field(1, alias="Parallelism", description="Number of tasks to update simultaneously")
    delay: Optional[int] = Field(None, alias="Delay", description="Delay between updates (ns)")
    failure_action: str = Field("pause", alias="FailureAction", description="'pause', 'continue', or 'rollback'")
    monitor: Optional[int] = Field(None, alias="Monitor", description="Duration to monitor for failures (ns)")
    max_failure_ratio: Optional[float] = Field(None, alias="MaxFailureRatio")
    order: str = Field("stop-first", alias="Order", description="'stop-first' or 'start-first'")
    
    class Config:
        allow_population_by_field_name = True


class ServiceHealthCheck(BaseModel):
    """Service health check configuration"""
    test: List[str] = Field(..., alias="Test", description="Health check command")
    interval: Optional[int] = Field(None, alias="Interval", description="Time between checks (ns)")
    timeout: Optional[int] = Field(None, alias="Timeout", description="Check timeout (ns)")
    retries: Optional[int] = Field(None, alias="Retries", description="Consecutive failures needed")
    start_period: Optional[int] = Field(None, alias="StartPeriod", description="Grace period (ns)")
    
    class Config:
        allow_population_by_field_name = True


class ServiceCreate(BaseModel):
    """Service creation request"""
    name: str = Field(..., description="Service name")
    image: str = Field(..., description="Container image")
    command: Optional[List[str]] = Field(None, description="Override default command")
    args: Optional[List[str]] = Field(None, description="Command arguments")
    env: Optional[List[str]] = Field(None, description="Environment variables")
    workdir: Optional[str] = Field(None, description="Working directory")
    user: Optional[str] = Field(None, description="User")
    groups: Optional[List[str]] = Field(None, description="Additional groups")
    
    # Service configuration
    mode: ServiceMode = Field(default_factory=lambda: ServiceMode(replicated={"Replicas": 1}))
    replicas: Optional[int] = Field(None, description="Number of replicas (for replicated mode)")
    
    # Placement
    constraints: Optional[List[str]] = Field(None, description="Placement constraints")
    preferences: Optional[List[Dict]] = Field(None, description="Placement preferences")
    max_replicas: Optional[int] = Field(None, description="Maximum replicas per node")
    
    # Resources
    cpu_limit: Optional[float] = Field(None, description="CPU limit (cores)")
    cpu_reservation: Optional[float] = Field(None, description="CPU reservation (cores)")
    memory_limit: Optional[int] = Field(None, description="Memory limit (bytes)")
    memory_reservation: Optional[int] = Field(None, description="Memory reservation (bytes)")
    
    # Networking
    networks: Optional[List[str]] = Field(None, description="Networks to attach")
    ports: Optional[List[ServicePort]] = Field(None, description="Published ports")
    endpoint_mode: str = Field("vip", description="Endpoint mode: 'vip' or 'dnsrr'")
    
    # Storage
    mounts: Optional[List[ServiceMount]] = Field(None, description="Mounts")
    secrets: Optional[List[str]] = Field(None, description="Secrets to expose")
    configs: Optional[List[str]] = Field(None, description="Configs to expose")
    
    # Updates
    update_config: Optional[ServiceUpdateConfig] = Field(None, description="Update configuration")
    rollback_config: Optional[ServiceUpdateConfig] = Field(None, description="Rollback configuration")
    
    # Restart
    restart_policy: Optional[ServiceRestartPolicy] = Field(None, description="Restart policy")
    
    # Health
    healthcheck: Optional[ServiceHealthCheck] = Field(None, description="Health check")
    
    # Labels
    labels: Dict[str, str] = Field(default_factory=dict, description="Service labels")
    container_labels: Dict[str, str] = Field(default_factory=dict, description="Container labels")


class ServiceUpdate(BaseModel):
    """Service update request"""
    version: int = Field(..., description="Service version for update")
    
    # All fields from ServiceCreate are optional for updates
    name: Optional[str] = None
    image: Optional[str] = None
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    env: Optional[List[str]] = None
    workdir: Optional[str] = None
    user: Optional[str] = None
    
    mode: Optional[ServiceMode] = None
    replicas: Optional[int] = None
    
    constraints: Optional[List[str]] = None
    preferences: Optional[List[Dict]] = None
    max_replicas: Optional[int] = None
    
    cpu_limit: Optional[float] = None
    cpu_reservation: Optional[float] = None
    memory_limit: Optional[int] = None
    memory_reservation: Optional[int] = None
    
    networks: Optional[List[str]] = None
    ports: Optional[List[ServicePort]] = None
    endpoint_mode: Optional[str] = None
    
    mounts: Optional[List[ServiceMount]] = None
    secrets: Optional[List[str]] = None
    configs: Optional[List[str]] = None
    
    update_config: Optional[ServiceUpdateConfig] = None
    rollback_config: Optional[ServiceUpdateConfig] = None
    restart_policy: Optional[ServiceRestartPolicy] = None
    healthcheck: Optional[ServiceHealthCheck] = None
    
    labels: Optional[Dict[str, str]] = None
    container_labels: Optional[Dict[str, str]] = None
    
    force_update: bool = Field(False, description="Force update even if no changes")


class ServiceScale(BaseModel):
    """Service scaling request"""
    replicas: int = Field(..., description="Number of replicas")


class ServiceUpdateStatus(BaseModel):
    """Service update status"""
    state: str = Field(..., alias="State", description="Update state: 'updating', 'paused', 'completed', etc.")
    started_at: Optional[datetime] = Field(None, alias="StartedAt")
    completed_at: Optional[datetime] = Field(None, alias="CompletedAt")
    message: Optional[str] = Field(None, alias="Message")
    
    class Config:
        allow_population_by_field_name = True


class ServiceEndpoint(BaseModel):
    """Service endpoint information"""
    spec: Optional[Dict] = Field(None, alias="Spec")
    ports: List[ServicePort] = Field(default_factory=list, alias="Ports")
    virtual_ips: List[Dict[str, str]] = Field(default_factory=list, alias="VirtualIPs")
    
    class Config:
        allow_population_by_field_name = True


class Service(BaseModel):
    """Swarm service information"""
    id: str = Field(..., alias="ID")
    version: Dict[str, int] = Field(..., alias="Version")
    created_at: datetime = Field(..., alias="CreatedAt")
    updated_at: datetime = Field(..., alias="UpdatedAt")
    spec: Dict = Field(..., alias="Spec", description="Service specification")
    endpoint: Optional[ServiceEndpoint] = Field(None, alias="Endpoint")
    update_status: Optional[ServiceUpdateStatus] = Field(None, alias="UpdateStatus")
    
    # Computed fields for easier access
    name: str = Field(None)
    image: str = Field(None)
    mode: str = Field(None)
    replicas: Optional[int] = Field(None)
    
    class Config:
        allow_population_by_field_name = True
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set computed fields from spec
        if self.spec:
            self.name = self.spec.get("Name", "")
            task_template = self.spec.get("TaskTemplate", {})
            container_spec = task_template.get("ContainerSpec", {})
            self.image = container_spec.get("Image", "")
            
            mode = self.spec.get("Mode", {})
            if "Replicated" in mode:
                self.mode = "replicated"
                self.replicas = mode["Replicated"].get("Replicas", 0)
            elif "Global" in mode:
                self.mode = "global"
                self.replicas = None
            else:
                self.mode = "unknown"


class ServiceListFilters(BaseModel):
    """Filters for listing services"""
    id: Optional[List[str]] = Field(None, description="Service IDs")
    label: Optional[List[str]] = Field(None, description="Service labels (e.g., 'key=value')")
    name: Optional[List[str]] = Field(None, description="Service names")
    mode: Optional[List[str]] = Field(None, description="Service modes ('replicated' or 'global')")


class ServiceListResponse(BaseModel):
    """Response for listing services"""
    services: List[Service]
    total: int


class ServiceLogsQuery(BaseModel):
    """Query parameters for service logs"""
    details: bool = Field(False, description="Show extra details")
    follow: bool = Field(False, description="Follow log output")
    stdout: bool = Field(True, description="Include stdout")
    stderr: bool = Field(True, description="Include stderr")
    since: Optional[int] = Field(None, description="Only logs since this timestamp")
    timestamps: bool = Field(False, description="Add timestamps")
    tail: Optional[str] = Field(None, description="Number of lines to show from end")