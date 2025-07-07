# Phase 2: Docker Swarm Support Implementation Plan

## Overview
Implement comprehensive Docker Swarm management features leveraging the existing multi-host infrastructure. The platform already has Docker hosts with swarm_manager and swarm_worker types configured.

## Implementation Order

### 1. Backend Data Models & Services (Week 1)

#### New Data Classes in docker_service.py:
```python
class NodeData:
    """Docker Swarm node information"""
    - id: str
    - hostname: str  
    - role: str (manager/worker)
    - availability: str (active/pause/drain)
    - status: str (ready/down/unknown)
    - state: str (ready/disconnected)
    - addr: str (IP address)
    - resources: Dict (CPU/memory)
    - engine_version: str
    - labels: Dict[str, str]
    - created_at: datetime
    - updated_at: datetime

class ServiceData:
    """Docker Swarm service information"""
    - id: str
    - name: str
    - mode: str (replicated/global)
    - replicas: int (for replicated mode)
    - image: str
    - created_at: datetime
    - updated_at: datetime
    - endpoint_spec: Dict (ports config)
    - update_config: Dict (rolling update settings)
    - labels: Dict[str, str]
    - constraints: List[str]
    - env: List[str]
    - mounts: List[Dict]
    - networks: List[str]
    - secrets: List[str]
    - configs: List[str]

class TaskData:
    """Docker Swarm task (service instance) information"""
    - id: str
    - service_id: str
    - node_id: str
    - container_id: Optional[str]
    - slot: Optional[int]
    - status: Dict (state, message, timestamp)
    - desired_state: str
    - created_at: datetime
    - updated_at: datetime

class SecretData:
    """Docker Swarm secret information"""
    - id: str
    - name: str
    - created_at: datetime
    - updated_at: datetime
    - labels: Dict[str, str]
    - spec: Dict (secret spec without data)

class ConfigData:
    """Docker Swarm config information"""
    - id: str
    - name: str
    - data: Optional[str] (base64 encoded)
    - created_at: datetime
    - updated_at: datetime
    - labels: Dict[str, str]
```

#### Extend DockerOperationExecutor:
```python
# Add to DockerOperationExecutor class:

# Swarm operations
async def get_swarm_info(self) -> Dict
async def init_swarm(self, advertise_addr: str, **kwargs) -> str
async def join_swarm(self, remote_addrs: List[str], join_token: str, **kwargs) -> None
async def leave_swarm(self, force: bool = False) -> None
async def update_swarm(self, **kwargs) -> None

# Node operations
async def list_nodes(self, filters: Dict = None) -> List[NodeData]
async def get_node(self, node_id: str) -> NodeData
async def update_node(self, node_id: str, version: int, **kwargs) -> NodeData
async def remove_node(self, node_id: str, force: bool = False) -> None

# Service operations
async def create_service(self, **kwargs) -> ServiceData
async def list_services(self, filters: Dict = None) -> List[ServiceData]
async def get_service(self, service_id: str) -> ServiceData
async def update_service(self, service_id: str, version: int, **kwargs) -> ServiceData
async def remove_service(self, service_id: str) -> None
async def scale_service(self, service_id: str, replicas: int) -> ServiceData
async def service_logs(self, service_id: str, **kwargs) -> AsyncIterator[str]
async def list_service_tasks(self, service_id: str) -> List[TaskData]

# Secret operations
async def create_secret(self, name: str, data: bytes, labels: Dict = None) -> SecretData
async def list_secrets(self, filters: Dict = None) -> List[SecretData]
async def get_secret(self, secret_id: str) -> SecretData
async def remove_secret(self, secret_id: str) -> None

# Config operations
async def create_config(self, name: str, data: bytes, labels: Dict = None) -> ConfigData
async def list_configs(self, filters: Dict = None) -> List[ConfigData]
async def get_config(self, config_id: str) -> ConfigData
async def remove_config(self, config_id: str) -> None
```

### 2. API Endpoints (Week 1-2)

#### New Pydantic Schemas:
```python
# schemas/swarm.py
class SwarmInfo(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    spec: Dict
    join_tokens: Dict
    root_ca_cert: str

class SwarmInit(BaseModel):
    advertise_addr: str
    listen_addr: Optional[str] = "0.0.0.0:2377"
    force_new_cluster: Optional[bool] = False

class SwarmJoin(BaseModel):
    remote_addrs: List[str]
    join_token: str
    advertise_addr: Optional[str]
    listen_addr: Optional[str] = "0.0.0.0:2377"

# schemas/node.py
class Node(BaseModel):
    id: str
    hostname: str
    role: str
    availability: str
    status: str
    state: str
    addr: str
    resources: Dict
    engine_version: str
    labels: Dict[str, str]
    created_at: datetime
    updated_at: datetime

class NodeUpdate(BaseModel):
    availability: Optional[str]  # active, pause, drain
    role: Optional[str]  # manager, worker
    labels: Optional[Dict[str, str]]

# schemas/service.py
class ServiceCreate(BaseModel):
    name: str
    image: str
    command: Optional[List[str]]
    args: Optional[List[str]]
    env: Optional[List[str]]
    mode: Optional[str] = "replicated"
    replicas: Optional[int] = 1
    constraints: Optional[List[str]]
    labels: Optional[Dict[str, str]]
    mounts: Optional[List[Dict]]
    networks: Optional[List[str]]
    ports: Optional[List[Dict]]
    secrets: Optional[List[str]]
    configs: Optional[List[str]]
    update_config: Optional[Dict]
    restart_policy: Optional[Dict]
    resources: Optional[Dict]
    healthcheck: Optional[Dict]

class ServiceUpdate(BaseModel):
    image: Optional[str]
    replicas: Optional[int]
    env: Optional[List[str]]
    constraints: Optional[List[str]]
    labels: Optional[Dict[str, str]]
    update_config: Optional[Dict]
    force_update: Optional[bool] = False

class Service(BaseModel):
    id: str
    name: str
    mode: str
    replicas: Optional[int]
    image: str
    created_at: datetime
    updated_at: datetime
    endpoint: Dict
    update_status: Optional[Dict]
    tasks_running: int
    tasks_desired: int

# schemas/secret.py
class SecretCreate(BaseModel):
    name: str
    data: str  # base64 encoded
    labels: Optional[Dict[str, str]]

class Secret(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    labels: Dict[str, str]

# schemas/config.py
class ConfigCreate(BaseModel):
    name: str
    data: str  # base64 encoded
    labels: Optional[Dict[str, str]]

class Config(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    labels: Dict[str, str]
```

#### New API Endpoints:

```python
# api/v1/endpoints/swarm.py
@router.get("/", response_model=SwarmInfo)
async def get_swarm_info(host_id: str = Query(...))

@router.post("/init", response_model=SwarmInfo)
async def init_swarm(swarm_init: SwarmInit, host_id: str = Query(...))

@router.post("/join")
async def join_swarm(swarm_join: SwarmJoin, host_id: str = Query(...))

@router.post("/leave")
async def leave_swarm(force: bool = False, host_id: str = Query(...))

@router.put("/", response_model=SwarmInfo)
async def update_swarm(update_data: Dict, host_id: str = Query(...))

# api/v1/endpoints/nodes.py
@router.get("/", response_model=List[Node])
async def list_nodes(host_id: str = Query(...), role: Optional[str] = None)

@router.get("/{node_id}", response_model=Node)
async def get_node(node_id: str, host_id: str = Query(...))

@router.put("/{node_id}", response_model=Node)
async def update_node(node_id: str, update: NodeUpdate, host_id: str = Query(...))

@router.delete("/{node_id}")
async def remove_node(node_id: str, force: bool = False, host_id: str = Query(...))

# api/v1/endpoints/services.py
@router.post("/", response_model=Service)
async def create_service(service: ServiceCreate, host_id: str = Query(...))

@router.get("/", response_model=List[Service])
async def list_services(host_id: str = Query(...), label: Optional[str] = None)

@router.get("/{service_id}", response_model=Service)
async def get_service(service_id: str, host_id: str = Query(...))

@router.put("/{service_id}", response_model=Service)
async def update_service(service_id: str, update: ServiceUpdate, host_id: str = Query(...))

@router.delete("/{service_id}")
async def remove_service(service_id: str, host_id: str = Query(...))

@router.post("/{service_id}/scale", response_model=Service)
async def scale_service(service_id: str, replicas: int, host_id: str = Query(...))

@router.get("/{service_id}/tasks", response_model=List[Task])
async def list_service_tasks(service_id: str, host_id: str = Query(...))

@router.get("/{service_id}/logs")
async def get_service_logs(service_id: str, host_id: str = Query(...), tail: int = 100)

# api/v1/endpoints/secrets.py
@router.post("/", response_model=Secret)
async def create_secret(secret: SecretCreate, host_id: str = Query(...))

@router.get("/", response_model=List[Secret])
async def list_secrets(host_id: str = Query(...))

@router.get("/{secret_id}", response_model=Secret)
async def get_secret(secret_id: str, host_id: str = Query(...))

@router.delete("/{secret_id}")
async def remove_secret(secret_id: str, host_id: str = Query(...))

# api/v1/endpoints/configs.py
@router.post("/", response_model=Config)
async def create_config(config: ConfigCreate, host_id: str = Query(...))

@router.get("/", response_model=List[Config])
async def list_configs(host_id: str = Query(...))

@router.get("/{config_id}", response_model=Config)
async def get_config(config_id: str, host_id: str = Query(...))

@router.delete("/{config_id}")
async def remove_config(config_id: str, host_id: str = Query(...))
```

### 3. WebSocket Endpoints (Week 2)

```python
# api/v1/websocket/services.py
@router.websocket("/services/{service_id}/logs")
async def service_logs_ws(websocket: WebSocket, service_id: str, host_id: str = Query(...))
    """Stream aggregated logs from all service tasks"""

@router.websocket("/services/{service_id}/events")
async def service_events_ws(websocket: WebSocket, service_id: str, host_id: str = Query(...))
    """Stream service update events (scaling, rolling updates, etc)"""

@router.websocket("/swarm/events")
async def swarm_events_ws(websocket: WebSocket, host_id: str = Query(...))
    """Stream cluster-wide events (node join/leave, service changes)"""
```

### 4. Frontend Implementation (Week 2-3)

#### New React Query Hooks:
```typescript
// hooks/useSwarm.ts
- useSwarmInfo(hostId: string)
- useSwarmInit(hostId: string)
- useSwarmJoin(hostId: string)
- useSwarmLeave(hostId: string)

// hooks/useNodes.ts
- useNodes(hostId: string, filters?: NodeFilters)
- useNode(hostId: string, nodeId: string)
- useUpdateNode(hostId: string)
- useRemoveNode(hostId: string)

// hooks/useServices.ts
- useServices(hostId: string, filters?: ServiceFilters)
- useService(hostId: string, serviceId: string)
- useCreateService(hostId: string)
- useUpdateService(hostId: string)
- useScaleService(hostId: string)
- useRemoveService(hostId: string)
- useServiceTasks(hostId: string, serviceId: string)
- useServiceLogs(hostId: string, serviceId: string)

// hooks/useSecrets.ts
- useSecrets(hostId: string)
- useCreateSecret(hostId: string)
- useRemoveSecret(hostId: string)

// hooks/useConfigs.ts
- useConfigs(hostId: string)
- useCreateConfig(hostId: string)
- useRemoveConfig(hostId: string)
```

#### New Pages:
```typescript
// pages/SwarmOverview.tsx
- Cluster health status card
- Node summary (managers vs workers)
- Service summary (running/desired tasks)
- Resource utilization charts
- Recent cluster events

// pages/Nodes.tsx
- Node list table with filters
- Status badges (role, availability, state)
- Actions: update availability, promote/demote
- Node details modal with resources

// pages/Services.tsx
- Service cards/list view toggle
- Create service button
- Service status (running/desired replicas)
- Quick scale controls
- Service details page with:
  - Task distribution across nodes
  - Service logs
  - Update history
  - Rolling update progress

// pages/ServiceDetail.tsx
- Service configuration
- Task list with node placement
- Aggregated logs view
- Update service form
- Scale dialog
- Delete confirmation

// pages/SecretsConfigs.tsx
- Tabbed interface (Secrets | Configs)
- Create new secret/config
- List with search/filter
- Delete with confirmation
- Used by services indicator
```

#### New Components:
```typescript
// components/swarm/SwarmHealthCard.tsx
- Cluster ID and creation date
- Manager nodes status
- Root CA certificate info
- Join tokens (hidden by default)

// components/swarm/NodeListItem.tsx
- Node hostname and IP
- Role badge (Manager/Worker)
- Availability selector
- Status indicator
- Resource bars (CPU/Memory)

// components/services/ServiceCard.tsx
- Service name and image
- Mode (replicated/global)
- Replica status (3/5 running)
- Quick scale buttons
- Last update timestamp

// components/services/ServiceCreateDialog.tsx
- Multi-step form wizard
- Basic: name, image, command
- Resources: CPU/memory limits
- Networking: ports, networks
- Volumes: mounts configuration
- Advanced: constraints, labels
- Review and create

// components/services/TaskList.tsx
- Task ID and slot
- Node placement
- Container status
- Started timestamp
- Error messages

// components/services/RollingUpdateProgress.tsx
- Update status (updating/paused/completed)
- Progress bar
- Task update details
- Pause/resume controls
```

### 5. Stack Management (Week 3-4)

#### Backend:
```python
# schemas/stack.py
class StackDeploy(BaseModel):
    name: str
    compose_file: str  # YAML content
    env_vars: Optional[Dict[str, str]]
    prune: Optional[bool] = False

class Stack(BaseModel):
    name: str
    services: List[str]
    networks: List[str]
    secrets: List[str]
    configs: List[str]

# api/v1/endpoints/stacks.py
@router.post("/", response_model=Stack)
async def deploy_stack(stack: StackDeploy, host_id: str = Query(...))

@router.get("/", response_model=List[Stack])
async def list_stacks(host_id: str = Query(...))

@router.get("/{stack_name}", response_model=Stack)
async def get_stack(stack_name: str, host_id: str = Query(...))

@router.delete("/{stack_name}")
async def remove_stack(stack_name: str, host_id: str = Query(...))
```

#### Frontend:
```typescript
// pages/Stacks.tsx
- Stack list with service count
- Deploy from file upload
- Deploy from template
- Stack details with services
- Remove stack confirmation

// components/stacks/StackDeployDialog.tsx
- File upload or paste YAML
- Environment variables form
- Syntax validation
- Preview services to create
- Deploy with progress
```

### 6. Advanced Features (Week 4-5)

#### Service Constraints & Placement:
- Node labels management
- Constraint builder UI
- Placement preference options
- Spread/pack strategies

#### Health Monitoring:
- Service health dashboard
- Task failure analysis
- Node resource alerts
- Automatic service recovery logs

#### Performance Optimization:
- Service list pagination
- Lazy loading task details
- WebSocket connection pooling
- Response caching with TTL

## Testing Strategy

### Unit Tests:
```python
# tests/unit/test_swarm_operations.py
- Test node data parsing
- Test service creation validation
- Test update config generation
- Test secret encoding/decoding

# tests/unit/test_swarm_api.py
- Test endpoint permissions
- Test response schemas
- Test error handling
- Test filtering/pagination
```

### Integration Tests:
```python
# tests/integration/test_swarm_integration.py
- Test with mock Swarm responses
- Test service lifecycle
- Test rolling updates
- Test node operations
```

### E2E Tests:
```typescript
// tests/e2e/swarm.spec.ts
- Create and scale service
- Deploy stack from compose
- Update node availability
- Create and use secret
```

## Security Considerations

1. **Role-based Access**:
   - Admin only: init/join/leave swarm, create services
   - Operator: scale services, view secrets
   - Viewer: read-only access

2. **Audit Logging**:
   - Log all Swarm management operations
   - Include user, timestamp, and changes
   - Store in audit_logs table

3. **Secret Management**:
   - Never log secret values
   - Encrypt at rest in database
   - Use Swarm secret distribution
   - Audit secret access

4. **Input Validation**:
   - Validate service configurations
   - Sanitize constraint expressions
   - Validate resource limits
   - Check image names

## Performance Considerations

1. **Caching**:
   - Cache node list (5s TTL)
   - Cache service list (10s TTL)
   - Cache swarm info (30s TTL)
   - Invalidate on changes

2. **Batch Operations**:
   - Bulk service updates
   - Parallel task queries
   - Aggregate logs efficiently
   - Batch WebSocket messages

3. **Resource Limits**:
   - Limit concurrent operations
   - Set max services per request
   - Limit log streaming connections
   - Configure operation timeouts

## Migration & Rollback

1. **Database Changes**:
   - No schema changes needed
   - Use existing DockerHost model
   - Store configs in Redis cache

2. **Feature Flags**:
   - SWARM_FEATURES_ENABLED
   - Progressive rollout
   - Quick disable option

3. **Compatibility**:
   - Check Docker API version
   - Graceful degradation
   - Clear error messages

## Success Metrics

1. **Functionality**:
   - All CRUD operations work
   - Real-time updates function
   - Logs aggregate correctly
   - Secrets deploy securely

2. **Performance**:
   - < 2s service list load
   - < 5s service creation
   - < 1s scale operation
   - Smooth rolling updates

3. **Reliability**:
   - 99% uptime for API
   - No data loss
   - Graceful error handling
   - Automatic reconnection

## Documentation

1. **User Guide**:
   - Swarm setup tutorial
   - Service deployment guide
   - Stack management howto
   - Troubleshooting tips

2. **API Documentation**:
   - OpenAPI schemas
   - Example requests
   - Error responses
   - WebSocket protocols

3. **Architecture**:
   - Swarm integration design
   - Security model
   - Performance strategies
   - Monitoring approach