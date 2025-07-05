# Multi-Host and Docker Swarm Architecture Plan

## Executive Summary

This document outlines the architectural design for extending Docker Control Platform to support multiple Docker hosts and Docker Swarm orchestration. The implementation is divided into two major phases:
- **Phase 2**: Multi-host support with centralized management
- **Phase 3**: Docker Swarm cluster management and orchestration

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Architecture Overview](#architecture-overview)
3. [Database Schema Design](#database-schema-design)
4. [Backend Architecture](#backend-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [CLI Tool Design](#cli-tool-design)
7. [Security Architecture](#security-architecture)
8. [Migration Strategy](#migration-strategy)
9. [Implementation Phases](#implementation-phases)
10. [Technical Specifications](#technical-specifications)
11. [API Design](#api-design)
12. [Performance Considerations](#performance-considerations)
13. [Monitoring and Observability](#monitoring-and-observability)

## Current State Analysis

### Existing Architecture
- **Single Host**: Currently supports only one Docker host via environment configuration
- **Connection**: Uses `DockerClientFactory` singleton pattern
- **Configuration**: Static configuration through environment variables
- **API Structure**: All endpoints assume single Docker daemon
- **WebSocket**: Direct connection to single Docker instance

### Limitations
- No multi-host management capability
- Cannot switch between Docker contexts
- No Swarm-aware operations
- Limited scalability for enterprise deployments

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
├─────────────────────────────────────────────────────────────────┤
│                     React Frontend (SPA)                         │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐        │
│  │Host Selector│  │ Dashboard   │  │ Swarm Topology   │        │
│  └────────────┘  └─────────────┘  └──────────────────┘        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTPS/WSS
┌─────────────────────────┴───────────────────────────────────────┐
│                        Nginx (Reverse Proxy)                     │
├─────────────────────────┬───────────────────────────────────────┤
│                         │                                        │
│  ┌─────────────────────┴────────────────────────────┐         │
│  │              FastAPI Backend                       │         │
│  │  ┌─────────────┐  ┌──────────────────────────┐   │         │
│  │  │ Host API    │  │ Docker Connection Manager │   │         │
│  │  └─────────────┘  └──────────────────────────┘   │         │
│  │  ┌─────────────┐  ┌──────────────────────────┐   │         │
│  │  │ Swarm API   │  │ WebSocket Manager         │   │         │
│  │  └─────────────┘  └──────────────────────────┘   │         │
│  └───────────────────────────────────────────────────┘         │
├─────────────────────────┬───────────────────────────────────────┤
│                         │                                        │
│  ┌──────────┐  ┌──────┴────────┐  ┌───────────────┐          │
│  │PostgreSQL│  │     Redis      │  │    Celery     │          │
│  │          │  │ (Cache/Queue)  │  │   Workers     │          │
│  └──────────┘  └───────────────┘  └───────────────┘          │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Docker API
    ┌─────────────────────┼─────────────────────────────────┐
    │                     │                                  │
    ▼                     ▼                                  ▼
┌──────────┐       ┌──────────┐                      ┌──────────┐
│Docker    │       │Docker    │                      │Docker    │
│Host 1    │       │Host 2    │       ...            │Swarm     │
│          │       │(Worker)  │                      │Manager   │
└──────────┘       └──────────┘                      └──────────┘
```

## Database Schema Design

### New Tables

```sql
-- Docker hosts configuration
CREATE TABLE docker_hosts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    host_type VARCHAR(50) NOT NULL, -- 'standalone', 'swarm_manager', 'swarm_worker'
    connection_type VARCHAR(50) NOT NULL, -- 'unix', 'tcp', 'ssh'
    host_url VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    
    -- Swarm specific fields
    swarm_id VARCHAR(255),
    cluster_name VARCHAR(255),
    is_leader BOOLEAN DEFAULT false,
    
    -- Metadata
    status VARCHAR(50) DEFAULT 'pending', -- 'healthy', 'unhealthy', 'pending'
    last_health_check TIMESTAMP,
    docker_version VARCHAR(50),
    api_version VARCHAR(50),
    os_type VARCHAR(50),
    architecture VARCHAR(50),
    
    -- Audit fields
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_hosts_status (status, is_active),
    INDEX idx_hosts_swarm (swarm_id, host_type),
    CONSTRAINT unique_default CHECK (
        (SELECT COUNT(*) FROM docker_hosts WHERE is_default = true) <= 1
    )
);

-- Encrypted credentials storage
CREATE TABLE host_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id UUID NOT NULL REFERENCES docker_hosts(id) ON DELETE CASCADE,
    credential_type VARCHAR(50) NOT NULL, -- 'tls_cert', 'tls_key', 'tls_ca', 'ssh_key', 'password'
    encrypted_value TEXT NOT NULL, -- AES-256 encrypted
    metadata JSONB, -- Additional metadata like fingerprints
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(host_id, credential_type)
);

-- User permissions per host
CREATE TABLE user_host_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    host_id UUID NOT NULL REFERENCES docker_hosts(id) ON DELETE CASCADE,
    permission_level VARCHAR(50) NOT NULL, -- 'viewer', 'operator', 'admin'
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, host_id),
    INDEX idx_user_hosts (user_id, permission_level)
);

-- Host tags for grouping and filtering
CREATE TABLE host_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id UUID NOT NULL REFERENCES docker_hosts(id) ON DELETE CASCADE,
    tag_name VARCHAR(100) NOT NULL,
    tag_value VARCHAR(255),
    
    UNIQUE(host_id, tag_name),
    INDEX idx_tags_name (tag_name, tag_value)
);

-- Connection pool statistics
CREATE TABLE host_connection_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id UUID NOT NULL REFERENCES docker_hosts(id) ON DELETE CASCADE,
    active_connections INT DEFAULT 0,
    total_connections BIGINT DEFAULT 0,
    failed_connections BIGINT DEFAULT 0,
    avg_response_time_ms FLOAT,
    last_error TEXT,
    last_error_at TIMESTAMP,
    measured_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_stats_host_time (host_id, measured_at DESC)
);
```

### Relationships
- `users` → `user_host_permissions` → `docker_hosts`
- `docker_hosts` → `host_credentials` (encrypted storage)
- `docker_hosts` → `host_tags` (metadata)
- `audit_logs` extended with `host_id` field

## Backend Architecture

### Connection Management

```python
# app/services/docker_connection_manager.py

class DockerConnectionManager:
    """Manages Docker client connections for multiple hosts"""
    
    def __init__(self):
        self._connections: Dict[str, DockerClient] = {}
        self._pools: Dict[str, asyncio.Queue] = {}
        self._health_checks: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
    
    async def get_client(
        self, 
        host_id: str, 
        user: User,
        db: AsyncSession
    ) -> DockerClient:
        """Get Docker client for specific host with permission check"""
        # Check user permissions
        await self._check_permissions(host_id, user, db)
        
        # Get or create connection
        if host_id not in self._connections:
            async with self._lock:
                if host_id not in self._connections:
                    await self._create_connection(host_id, db)
        
        return self._connections[host_id]
    
    async def _create_connection(self, host_id: str, db: AsyncSession):
        """Create new Docker connection"""
        host = await self._get_host_config(host_id, db)
        credentials = await self._get_credentials(host_id, db)
        
        if host.connection_type == "unix":
            client = docker.DockerClient(base_url=host.host_url)
        elif host.connection_type == "tcp":
            tls_config = self._build_tls_config(credentials)
            client = docker.DockerClient(
                base_url=host.host_url,
                tls=tls_config
            )
        elif host.connection_type == "ssh":
            client = docker.DockerClient(
                base_url=host.host_url,
                use_ssh_client=True,
                ssh_config=self._build_ssh_config(credentials)
            )
        
        # Test connection
        client.ping()
        self._connections[host_id] = client
        
    async def close_all(self):
        """Close all connections"""
        for client in self._connections.values():
            client.close()
        self._connections.clear()
```

### API Structure Updates

```python
# All endpoints accept optional host_id parameter
@router.get("/containers")
async def list_containers(
    host_id: Optional[str] = Query(None, description="Target host ID"),
    all: bool = Query(False),
    current_user: User = Depends(get_current_user),
    docker_manager: DockerConnectionManager = Depends(get_docker_manager),
    db: AsyncSession = Depends(get_db)
):
    # Use default host if not specified
    if not host_id:
        host_id = await get_default_host_id(db, current_user)
    
    client = await docker_manager.get_client(host_id, current_user, db)
    containers = client.containers.list(all=all)
    return [serialize_container(c) for c in containers]

# Multi-host aggregation endpoint
@router.get("/containers/all-hosts")
async def list_containers_all_hosts(
    current_user: User = Depends(get_current_user),
    docker_manager: DockerConnectionManager = Depends(get_docker_manager),
    db: AsyncSession = Depends(get_db)
):
    hosts = await get_user_accessible_hosts(db, current_user)
    results = {}
    
    # Parallel queries to all hosts
    tasks = []
    for host in hosts:
        task = fetch_host_containers(docker_manager, host.id, current_user, db)
        tasks.append(task)
    
    host_containers = await asyncio.gather(*tasks, return_exceptions=True)
    
    for host, containers in zip(hosts, host_containers):
        if isinstance(containers, Exception):
            results[host.id] = {"error": str(containers)}
        else:
            results[host.id] = {
                "host_name": host.name,
                "containers": containers
            }
    
    return results
```

### Swarm-Specific Endpoints

```python
# app/api/v1/swarm.py

@router.get("/swarm/info")
async def get_swarm_info(
    host_id: str = Query(..., description="Swarm manager host ID"),
    current_user: User = Depends(get_current_user),
    docker_manager: DockerConnectionManager = Depends(get_docker_manager),
    db: AsyncSession = Depends(get_db)
):
    client = await docker_manager.get_client(host_id, current_user, db)
    
    # Verify this is a swarm manager
    info = client.info()
    if not info.get("Swarm", {}).get("LocalNodeState") == "active":
        raise HTTPException(400, "Host is not part of a swarm")
    
    if not info.get("Swarm", {}).get("ControlAvailable"):
        raise HTTPException(400, "Host is not a swarm manager")
    
    return {
        "swarm_id": info["Swarm"]["NodeID"],
        "nodes": client.nodes.list(),
        "services": client.services.list(),
        "networks": client.networks.list(filters={"scope": "swarm"}),
    }

@router.post("/swarm/services")
async def create_service(
    service_spec: ServiceSpec,
    host_id: str = Query(..., description="Swarm manager host ID"),
    current_user: User = Depends(get_current_active_user),
    docker_manager: DockerConnectionManager = Depends(get_docker_manager),
    db: AsyncSession = Depends(get_db)
):
    client = await docker_manager.get_client(host_id, current_user, db)
    
    service = client.services.create(
        image=service_spec.image,
        name=service_spec.name,
        replicas=service_spec.replicas,
        networks=service_spec.networks,
        mounts=service_spec.mounts,
        env=service_spec.env,
        constraints=service_spec.constraints
    )
    
    await log_audit_event(
        db,
        user=current_user,
        action="swarm.service.create",
        resource_type="service",
        resource_id=service.id,
        details={"service_name": service_spec.name, "host_id": host_id}
    )
    
    return serialize_service(service)
```

### WebSocket Updates

```python
# app/api/v1/websocket/multi_host.py

class MultiHostWebSocketManager:
    """Manages WebSocket connections across multiple hosts"""
    
    def __init__(self):
        self.connections: Dict[str, Dict[str, WebSocket]] = {}  # host_id -> connection_id -> ws
        self.streams: Dict[str, DockerEventStream] = {}  # host_id -> event stream
    
    async def connect_to_host_events(
        self,
        websocket: WebSocket,
        host_id: str,
        user: User,
        docker_manager: DockerConnectionManager,
        db: AsyncSession
    ):
        """Stream Docker events from specific host"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        
        # Store connection
        if host_id not in self.connections:
            self.connections[host_id] = {}
        self.connections[host_id][connection_id] = websocket
        
        try:
            # Get Docker client
            client = await docker_manager.get_client(host_id, user, db)
            
            # Start event stream if not exists
            if host_id not in self.streams:
                self.streams[host_id] = await self._start_event_stream(client, host_id)
            
            # Subscribe to events
            async for event in self.streams[host_id]:
                message = {
                    "type": "docker_event",
                    "host_id": host_id,
                    "event": event,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Broadcast to all connections for this host
                await self._broadcast_to_host(host_id, message)
                
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "host_id": host_id
            })
        finally:
            # Cleanup
            if host_id in self.connections:
                self.connections[host_id].pop(connection_id, None)
                if not self.connections[host_id]:
                    # Stop stream if no more connections
                    if host_id in self.streams:
                        await self.streams[host_id].close()
                        del self.streams[host_id]
```

## Frontend Architecture

### State Management

```typescript
// stores/hostStore.ts

interface HostState {
  hosts: DockerHost[];
  currentHostId: string | null;
  hostStatuses: Record<string, HostStatus>;
  loading: boolean;
  error: string | null;
}

export const useHostStore = create<HostState & HostActions>((set, get) => ({
  hosts: [],
  currentHostId: null,
  hostStatuses: {},
  loading: false,
  error: null,
  
  // Actions
  async fetchHosts() {
    set({ loading: true });
    try {
      const hosts = await api.hosts.list();
      const defaultHost = hosts.find(h => h.is_default) || hosts[0];
      set({ 
        hosts, 
        currentHostId: defaultHost?.id || null,
        loading: false 
      });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
  
  async selectHost(hostId: string) {
    set({ currentHostId: hostId });
    // Update all API calls to use new host
    api.setDefaultHost(hostId);
  },
  
  async addHost(hostConfig: HostConfig) {
    const host = await api.hosts.create(hostConfig);
    set(state => ({
      hosts: [...state.hosts, host]
    }));
    return host;
  },
  
  subscribeToHostEvents() {
    const ws = new WebSocket(`/ws/hosts/events`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'host_status_update') {
        set(state => ({
          hostStatuses: {
            ...state.hostStatuses,
            [data.host_id]: data.status
          }
        }));
      }
    };
  }
}));
```

### UI Components

```typescript
// components/HostSelector.tsx

export function HostSelector() {
  const { hosts, currentHostId, selectHost } = useHostStore();
  const { showWarning } = useToast();
  
  const handleHostChange = async (hostId: string) => {
    const host = hosts.find(h => h.id === hostId);
    
    if (host?.status !== 'healthy') {
      showWarning(`Host ${host?.name} is currently ${host?.status}`);
    }
    
    await selectHost(hostId);
  };
  
  return (
    <div className="host-selector">
      <Dropdown>
        <Dropdown.Toggle variant="outline-secondary" size="sm">
          <ServerIcon className="me-2" />
          {hosts.find(h => h.id === currentHostId)?.name || 'Select Host'}
        </Dropdown.Toggle>
        
        <Dropdown.Menu>
          <Dropdown.Header>Docker Hosts</Dropdown.Header>
          {hosts.map(host => (
            <Dropdown.Item
              key={host.id}
              onClick={() => handleHostChange(host.id)}
              active={host.id === currentHostId}
            >
              <div className="d-flex align-items-center">
                <StatusIndicator status={host.status} />
                <div className="ms-2">
                  <div>{host.name}</div>
                  {host.host_type === 'swarm_manager' && (
                    <small className="text-muted">Swarm Manager</small>
                  )}
                </div>
              </div>
            </Dropdown.Item>
          ))}
          <Dropdown.Divider />
          <Dropdown.Item onClick={() => navigate('/hosts/add')}>
            <PlusIcon className="me-2" />
            Add New Host
          </Dropdown.Item>
        </Dropdown.Menu>
      </Dropdown>
    </div>
  );
}
```

```typescript
// components/SwarmTopology.tsx

export function SwarmTopology({ hostId }: { hostId: string }) {
  const { data: swarmInfo } = useSwarmInfo(hostId);
  
  if (!swarmInfo) return <Loading />;
  
  return (
    <div className="swarm-topology">
      <div className="topology-header">
        <h3>Swarm Cluster: {swarmInfo.cluster_name}</h3>
        <div className="cluster-stats">
          <span>Nodes: {swarmInfo.nodes.length}</span>
          <span>Services: {swarmInfo.services.length}</span>
          <span>Tasks: {swarmInfo.total_tasks}</span>
        </div>
      </div>
      
      <div className="topology-visualization">
        {swarmInfo.nodes.map(node => (
          <NodeCard
            key={node.id}
            node={node}
            services={swarmInfo.services.filter(s => 
              s.tasks.some(t => t.node_id === node.id)
            )}
          />
        ))}
      </div>
      
      <ServiceDistributionChart services={swarmInfo.services} />
    </div>
  );
}
```

### API Client Updates

```typescript
// api/client.ts

class APIClient {
  private currentHostId: string | null = null;
  
  setDefaultHost(hostId: string) {
    this.currentHostId = hostId;
  }
  
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    if (this.currentHostId) {
      headers['X-Docker-Host-ID'] = this.currentHostId;
    }
    
    return headers;
  }
  
  // Update all methods to include host context
  async listContainers(hostId?: string): Promise<Container[]> {
    const params = new URLSearchParams();
    if (hostId) params.append('host_id', hostId);
    
    return this.get(`/containers?${params}`);
  }
  
  // Multi-host aggregation
  async listAllHostContainers(): Promise<MultiHostContainers> {
    return this.get('/containers/all-hosts');
  }
}
```

## CLI Tool Design

### Architecture

```go
// cmd/dsctl/main.go

package main

import (
    "github.com/spf13/cobra"
    "dsctl/pkg/config"
    "dsctl/pkg/client"
)

func main() {
    cfg := config.Load()
    apiClient := client.New(cfg)
    
    rootCmd := &cobra.Command{
        Use:   "dsctl",
        Short: "Docker Swarm Control CLI",
        Long:  "A kubectl-style CLI for managing Docker hosts and Swarm clusters",
    }
    
    // Add subcommands
    rootCmd.AddCommand(
        NewContextCommand(cfg),
        NewGetCommand(apiClient),
        NewCreateCommand(apiClient),
        NewDeleteCommand(apiClient),
        NewExecCommand(apiClient),
        NewLogsCommand(apiClient),
        NewSwarmCommand(apiClient),
    )
    
    rootCmd.Execute()
}
```

### Configuration Management

```yaml
# ~/.dsctl/config.yaml

apiVersion: v1
kind: Config
current-context: production

contexts:
- name: production
  server: https://docker-control.company.com
  host: prod-swarm-manager-1
  user: john.doe

- name: staging
  server: https://staging.docker-control.company.com
  host: staging-docker-1
  user: john.doe

- name: local
  server: http://localhost
  host: default
  user: admin

users:
- name: john.doe
  token: eyJhbGciOiJIUzI1NiIs...
  
- name: admin
  token: eyJhbGciOiJIUzI1NiIs...

preferences:
  output: table  # json, yaml, table
  color: true
  page-size: 50
```

### Command Examples

```bash
# Context management
dsctl context list
dsctl context use production
dsctl context current

# Container operations
dsctl get containers
dsctl get container nginx-1 --output json
dsctl exec nginx-1 -- bash -il
dsctl logs nginx-1 --follow --tail 100

# Multi-host operations
dsctl get containers --all-hosts
dsctl get hosts
dsctl add host prod-docker-2 --url tcp://10.0.1.2:2376 --tls

# Swarm operations
dsctl swarm init --advertise-addr 10.0.1.1
dsctl swarm join-token worker
dsctl service create --name web --replicas 3 nginx:latest
dsctl service scale web=5
dsctl service update web --image nginx:alpine
dsctl stack deploy -f docker-compose.yml myapp

# Node management
dsctl node list
dsctl node inspect prod-worker-1
dsctl node update prod-worker-1 --availability drain
dsctl node promote prod-worker-1

# Output formatting
dsctl get services -o json | jq '.[] | {name, replicas}'
dsctl get nodes -o custom-columns=NAME:.Name,STATUS:.Status
```

## Security Architecture

### Authentication & Authorization

```python
# Enhanced permission checking
async def check_host_permission(
    db: AsyncSession,
    user: User,
    host_id: str,
    required_level: str = "viewer"
) -> bool:
    # Admin users have access to all hosts
    if user.role == UserRole.admin:
        return True
    
    # Check specific host permission
    permission = await db.execute(
        select(UserHostPermission)
        .where(
            UserHostPermission.user_id == user.id,
            UserHostPermission.host_id == host_id
        )
    )
    perm = permission.scalar_one_or_none()
    
    if not perm:
        return False
    
    # Check permission hierarchy
    levels = {"viewer": 0, "operator": 1, "admin": 2}
    return levels.get(perm.permission_level, 0) >= levels.get(required_level, 0)
```

### Credential Encryption

```python
# app/services/encryption.py

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class CredentialEncryption:
    def __init__(self, master_key: str):
        # Derive encryption key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'docker-control-platform',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

# Usage in host credential storage
async def store_host_credentials(
    db: AsyncSession,
    host_id: str,
    credentials: Dict[str, str],
    encryption: CredentialEncryption
):
    for cred_type, value in credentials.items():
        encrypted_value = encryption.encrypt(value)
        
        cred = HostCredential(
            host_id=host_id,
            credential_type=cred_type,
            encrypted_value=encrypted_value
        )
        db.add(cred)
    
    await db.commit()
```

### Network Security

```yaml
# Docker host connection security
tls_verification:
  ca_cert: /path/to/ca.pem
  client_cert: /path/to/cert.pem
  client_key: /path/to/key.pem
  verify_hostname: true

ssh_config:
  private_key_path: /path/to/id_rsa
  known_hosts_path: ~/.ssh/known_hosts
  strict_host_checking: true
  
firewall_rules:
  - port: 2376
    protocol: tcp
    source: 10.0.0.0/8
    description: Docker TLS API
  
  - port: 2377
    protocol: tcp
    source: 10.0.0.0/8
    description: Swarm management
    
  - port: 7946
    protocol: tcp/udp
    source: 10.0.0.0/8
    description: Container network discovery
```

## Migration Strategy

### Phase 2.1: Multi-Host Foundation (Week 1-2)

1. **Database Migration**
   ```sql
   -- Add host_id to existing tables
   ALTER TABLE audit_logs ADD COLUMN host_id UUID REFERENCES docker_hosts(id);
   
   -- Create default host from current configuration
   INSERT INTO docker_hosts (name, host_url, connection_type, is_default)
   VALUES ('default', 'unix:///var/run/docker.sock', 'unix', true);
   ```

2. **Backend Services**
   - Implement `DockerConnectionManager`
   - Create host CRUD endpoints
   - Add host_id parameter to existing endpoints
   - Implement backward compatibility layer

3. **Frontend Updates**
   - Add host selector component
   - Update API client for host context
   - Create host management UI

### Phase 2.2: Multi-Host Operations (Week 2-3)

1. **API Updates**
   - Update all Docker operations for multi-host
   - Implement parallel operations
   - Add aggregation endpoints
   - WebSocket multiplexing

2. **UI Enhancements**
   - Multi-host dashboard
   - Comparative views
   - Cross-host operations

### Phase 2.3: CLI Tool (Week 3-4)

1. **Core Implementation**
   - Command structure
   - Config management
   - API client
   - Output formatting

2. **Features**
   - Context switching
   - Interactive mode
   - Shell completion
   - Plugin system

### Phase 3.1: Swarm Foundation (Week 1-2)

1. **Swarm Detection**
   - Auto-detect Swarm clusters
   - Sync node information
   - Manager election tracking

2. **Basic Operations**
   - Service CRUD
   - Node management
   - Network operations

### Phase 3.2: Swarm Advanced (Week 3-4)

1. **Orchestration**
   - Stack deployment
   - Rolling updates
   - Health monitoring
   - Secret management

2. **Visualization**
   - Topology view
   - Service distribution
   - Task tracking

### Phase 3.3: Swarm Monitoring (Week 4-5)

1. **Observability**
   - Log aggregation
   - Metrics collection
   - Alert integration
   - Performance analysis

## Technical Specifications

### Connection Types

```python
# Connection URL formats
connection_specs = {
    "unix": {
        "format": "unix:///var/run/docker.sock",
        "requires_tls": False,
        "default_port": None
    },
    "tcp": {
        "format": "tcp://[HOST]:[PORT]",
        "requires_tls": True,
        "default_port": 2376
    },
    "ssh": {
        "format": "ssh://[USER]@[HOST]:[PORT]",
        "requires_tls": False,
        "default_port": 22
    }
}
```

### Host Discovery

```python
async def discover_swarm_nodes(manager_client: DockerClient) -> List[SwarmNode]:
    """Discover all nodes in a Swarm cluster"""
    nodes = []
    
    for node in manager_client.nodes.list():
        node_info = {
            "id": node.id,
            "hostname": node.attrs["Description"]["Hostname"],
            "role": node.attrs["Spec"]["Role"],
            "availability": node.attrs["Spec"]["Availability"],
            "status": node.attrs["Status"]["State"],
            "addr": node.attrs["Status"]["Addr"],
            "is_leader": node.attrs.get("ManagerStatus", {}).get("Leader", False)
        }
        nodes.append(node_info)
    
    return nodes
```

### Performance Optimizations

```python
# Parallel host operations
async def parallel_container_list(
    host_ids: List[str],
    docker_manager: DockerConnectionManager,
    user: User,
    db: AsyncSession
) -> Dict[str, List[Container]]:
    """Fetch containers from multiple hosts in parallel"""
    
    async def fetch_host_containers(host_id: str):
        try:
            client = await docker_manager.get_client(host_id, user, db)
            containers = await asyncio.to_thread(client.containers.list)
            return host_id, [serialize_container(c) for c in containers]
        except Exception as e:
            logger.error(f"Failed to fetch from {host_id}: {e}")
            return host_id, []
    
    # Create tasks for parallel execution
    tasks = [fetch_host_containers(host_id) for host_id in host_ids]
    
    # Execute in parallel with timeout
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    container_map = {}
    for result in results:
        if isinstance(result, tuple):
            host_id, containers = result
            container_map[host_id] = containers
        else:
            logger.error(f"Task failed: {result}")
    
    return container_map
```

## API Design

### RESTful Endpoints

```yaml
# Host Management
GET    /api/v1/hosts                    # List all hosts
POST   /api/v1/hosts                    # Add new host
GET    /api/v1/hosts/{id}               # Get host details
PUT    /api/v1/hosts/{id}               # Update host
DELETE /api/v1/hosts/{id}               # Remove host
POST   /api/v1/hosts/{id}/test          # Test connection

# Multi-Host Operations
GET    /api/v1/containers?host_id={id}  # List containers on specific host
GET    /api/v1/containers/all-hosts     # List containers on all hosts
GET    /api/v1/images/all-hosts         # List images on all hosts

# Swarm Operations
GET    /api/v1/swarm/info?host_id={id}  # Get Swarm info
POST   /api/v1/swarm/init               # Initialize Swarm
POST   /api/v1/swarm/join               # Join Swarm
POST   /api/v1/swarm/leave              # Leave Swarm

# Service Management
GET    /api/v1/swarm/services           # List services
POST   /api/v1/swarm/services           # Create service
GET    /api/v1/swarm/services/{id}      # Get service details
PUT    /api/v1/swarm/services/{id}      # Update service
DELETE /api/v1/swarm/services/{id}      # Remove service
POST   /api/v1/swarm/services/{id}/scale # Scale service

# Node Management
GET    /api/v1/swarm/nodes              # List nodes
GET    /api/v1/swarm/nodes/{id}         # Get node details
PUT    /api/v1/swarm/nodes/{id}         # Update node
DELETE /api/v1/swarm/nodes/{id}         # Remove node

# Stack Management
GET    /api/v1/swarm/stacks             # List stacks
POST   /api/v1/swarm/stacks             # Deploy stack
GET    /api/v1/swarm/stacks/{name}      # Get stack details
DELETE /api/v1/swarm/stacks/{name}      # Remove stack
```

### WebSocket Endpoints

```yaml
# Multi-Host WebSockets
WS  /ws/hosts/{id}/events         # Docker events from specific host
WS  /ws/hosts/{id}/stats          # System stats from host
WS  /ws/hosts/all/events          # Aggregated events from all hosts

# Swarm WebSockets
WS  /ws/swarm/{id}/events         # Swarm cluster events
WS  /ws/swarm/{id}/logs           # Service logs aggregation
WS  /ws/swarm/{id}/metrics        # Cluster metrics stream
```

## Performance Considerations

### Connection Pooling

```python
class ConnectionPool:
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.pools: Dict[str, asyncio.Queue] = {}
        self.connection_counts: Dict[str, int] = {}
    
    async def acquire(self, host_id: str) -> DockerClient:
        if host_id not in self.pools:
            self.pools[host_id] = asyncio.Queue(maxsize=self.max_connections)
            self.connection_counts[host_id] = 0
        
        pool = self.pools[host_id]
        
        try:
            # Try to get existing connection
            client = pool.get_nowait()
            # Verify connection is still valid
            client.ping()
            return client
        except (asyncio.QueueEmpty, Exception):
            # Create new connection if under limit
            if self.connection_counts[host_id] < self.max_connections:
                client = await self._create_client(host_id)
                self.connection_counts[host_id] += 1
                return client
            else:
                # Wait for available connection
                client = await pool.get()
                client.ping()
                return client
    
    async def release(self, host_id: str, client: DockerClient):
        if host_id in self.pools:
            await self.pools[host_id].put(client)
```

### Caching Strategy

```python
# Redis caching for multi-host data
class MultiHostCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 30  # seconds
    
    async def get_containers(self, host_id: str) -> Optional[List[Dict]]:
        key = f"host:{host_id}:containers"
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def set_containers(self, host_id: str, containers: List[Dict]):
        key = f"host:{host_id}:containers"
        await self.redis.setex(
            key, 
            self.default_ttl, 
            json.dumps(containers)
        )
    
    async def invalidate_host(self, host_id: str):
        pattern = f"host:{host_id}:*"
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)
```

### Rate Limiting

```python
# Per-host rate limiting
rate_limiter_config = {
    "default": "100/minute",
    "swarm_operations": "20/minute",
    "multi_host_aggregation": "10/minute"
}

@router.get("/containers/all-hosts")
@limiter.limit("10/minute")  # Expensive operation
async def list_all_host_containers(...):
    pass
```

## Monitoring and Observability

### Metrics Collection

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# Metrics definitions
docker_api_requests = Counter(
    'docker_api_requests_total',
    'Total Docker API requests',
    ['host_id', 'operation', 'status']
)

docker_api_duration = Histogram(
    'docker_api_duration_seconds',
    'Docker API request duration',
    ['host_id', 'operation']
)

active_docker_connections = Gauge(
    'active_docker_connections',
    'Number of active Docker connections',
    ['host_id']
)

host_health_status = Gauge(
    'host_health_status',
    'Docker host health status (1=healthy, 0=unhealthy)',
    ['host_id', 'host_name']
)
```

### Health Monitoring

```python
class HostHealthMonitor:
    def __init__(self, docker_manager: DockerConnectionManager):
        self.docker_manager = docker_manager
        self.health_check_interval = 30  # seconds
        
    async def monitor_hosts(self, db: AsyncSession):
        """Background task to monitor host health"""
        while True:
            hosts = await get_all_hosts(db)
            
            for host in hosts:
                try:
                    client = await self.docker_manager.get_client(
                        host.id, 
                        system_user, 
                        db
                    )
                    
                    # Perform health check
                    info = await asyncio.to_thread(client.info)
                    
                    await update_host_status(
                        db, 
                        host.id,
                        status="healthy",
                        docker_version=info.get("ServerVersion"),
                        api_version=info.get("ApiVersion")
                    )
                    
                    # Update metrics
                    host_health_status.labels(
                        host_id=host.id,
                        host_name=host.name
                    ).set(1)
                    
                except Exception as e:
                    logger.error(f"Health check failed for {host.name}: {e}")
                    
                    await update_host_status(
                        db,
                        host.id,
                        status="unhealthy",
                        last_error=str(e)
                    )
                    
                    host_health_status.labels(
                        host_id=host.id,
                        host_name=host.name
                    ).set(0)
            
            await asyncio.sleep(self.health_check_interval)
```

### Logging

```python
# Structured logging for multi-host operations
import structlog

logger = structlog.get_logger()

# Log with context
logger.info(
    "docker_operation",
    operation="container_list",
    host_id=host_id,
    host_name=host.name,
    user_id=user.id,
    duration=duration,
    container_count=len(containers)
)

# Audit log for Swarm operations
await log_audit_event(
    db,
    user=current_user,
    action="swarm.service.scale",
    resource_type="service",
    resource_id=service_id,
    details={
        "host_id": host_id,
        "cluster_name": cluster_name,
        "old_replicas": old_replicas,
        "new_replicas": new_replicas
    }
)
```

## Test Environment Setup

### Overview

For proper testing of multi-host and Docker Swarm features, we need a test environment with multiple Docker hosts. This section covers manual VM setup since automated tools like Vagrant may not work in all environments.

### VM Requirements

#### Essential VMs (minimum for testing):

1. **Control Platform VM** (where Docker Control Platform runs)
   - IP: 10.0.0.10 (or your preferred range)
   - Specs: 4 CPU cores, 4GB RAM, 40GB disk
   - Purpose: Hosts the application, PostgreSQL, Redis
   - Docker: Not required (unless managing itself)

2. **Docker Host 1** (Swarm Manager)
   - IP: 10.0.0.11
   - Specs: 4 CPU cores, 4GB RAM, 20GB disk
   - Purpose: Swarm manager node
   - Docker: Required with remote API enabled

3. **Docker Host 2** (Swarm Worker)
   - IP: 10.0.0.21
   - Specs: 2 CPU cores, 2GB RAM, 20GB disk
   - Purpose: Swarm worker node
   - Docker: Required with remote API enabled

4. **Docker Host 3** (Standalone)
   - IP: 10.0.0.30
   - Specs: 2 CPU cores, 2GB RAM, 20GB disk
   - Purpose: Standalone Docker host for testing
   - Docker: Required with remote API enabled

### Docker Configuration on Test VMs

After creating your VMs, configure Docker on each host (except Control Platform):

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Enable Docker remote API
# Option A: With TLS (recommended for production-like testing)
sudo mkdir -p /etc/docker/certs
# Generate or copy TLS certificates here

sudo tee /etc/docker/daemon.json <<EOF
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"],
  "tls": true,
  "tlscert": "/etc/docker/certs/server-cert.pem",
  "tlskey": "/etc/docker/certs/server-key.pem",
  "tlsverify": true,
  "tlscacert": "/etc/docker/certs/ca.pem"
}
EOF

# Option B: Without TLS (for development testing only!)
sudo tee /etc/docker/daemon.json <<EOF
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
EOF

# Update systemd to not conflict with daemon.json
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf <<EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
EOF

# Restart Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# Verify remote API is accessible
curl http://localhost:2375/version  # or https://localhost:2376/version with --cert flags
```

### Initialize Swarm Cluster

On your designated Swarm Manager (10.0.0.11):

```bash
# Initialize Swarm
docker swarm init --advertise-addr 10.0.0.11

# Get join tokens (save these!)
docker swarm join-token manager
docker swarm join-token worker
```

On your Worker nodes (10.0.0.21):

```bash
# Join as worker (use the token from above)
docker swarm join --token SWMTKN-1-xxxxx 10.0.0.11:2377
```

### Test Environment Configuration File

Create this configuration file after setting up your VMs:

```python
# tests/fixtures/test_environments.py
TEST_ENVIRONMENTS = {
    "docker_hosts": [
        {
            "name": "swarm-manager-1",
            "host": "10.0.0.11",  # Update with your actual IP
            "port": 2375,  # or 2376 for TLS
            "type": "swarm_manager",
            "connection": "tcp",
            "tls": False,  # Set to True if using TLS
            "description": "Main Swarm Manager"
        },
        {
            "name": "swarm-worker-1", 
            "host": "10.0.0.21",  # Update with your actual IP
            "port": 2375,
            "type": "swarm_worker",
            "connection": "tcp",
            "tls": False,
            "description": "Swarm Worker Node 1"
        },
        {
            "name": "docker-standalone",
            "host": "10.0.0.30",  # Update with your actual IP
            "port": 2375,
            "type": "standalone",
            "connection": "tcp", 
            "tls": False,
            "description": "Standalone Docker Host"
        }
    ],
    "swarm_cluster": {
        "name": "test-swarm",
        "manager_ip": "10.0.0.11",
        "worker_ips": ["10.0.0.21"]
    },
    "control_platform": {
        "host": "10.0.0.10",
        "api_port": 8000,
        "frontend_port": 80
    }
}
```

### Network Connectivity Testing

Before integrating with the platform, verify connectivity:

```bash
# From Control Platform VM, test each Docker host:
# Without TLS
curl http://10.0.0.11:2375/version
curl http://10.0.0.21:2375/version
curl http://10.0.0.30:2375/version

# With TLS (if configured)
curl --cert client-cert.pem --key client-key.pem --cacert ca.pem https://10.0.0.11:2376/version

# Test Docker commands remotely
export DOCKER_HOST=tcp://10.0.0.11:2375
docker info
docker ps
```

### Quick Verification Script

Use this script to verify all hosts are accessible:

```python
# test_vm_connectivity.py
import docker
import json

test_hosts = {
    "swarm-manager": "tcp://10.0.0.11:2375",
    "swarm-worker": "tcp://10.0.0.21:2375",
    "standalone": "tcp://10.0.0.30:2375"
}

for name, url in test_hosts.items():
    try:
        client = docker.DockerClient(base_url=url)
        info = client.info()
        print(f"\n{name} ({url}):")
        print(f"  Docker Version: {info['ServerVersion']}")
        print(f"  Containers: {info['Containers']}")
        print(f"  Images: {info['Images']}")
        if 'Swarm' in info:
            print(f"  Swarm: {info['Swarm']['LocalNodeState']}")
        client.close()
    except Exception as e:
        print(f"\n{name} ({url}): Connection failed - {e}")
```

### Testing Scenarios

With your manual VMs, test these scenarios:

1. **Multi-Host Container Management**
   - List containers across all hosts
   - Start/stop containers on specific hosts
   - View aggregated statistics

2. **Swarm Operations**
   - Deploy services: `docker service create --name web --replicas 3 nginx`
   - Scale services: `docker service scale web=5`
   - Deploy stacks: `docker stack deploy -c docker-compose.yml myapp`

3. **Mixed Environment**
   - Manage both Swarm and standalone hosts
   - Test failover scenarios
   - Monitor resource usage across hosts

### Firewall Rules

Ensure these ports are open between VMs:

- **2375/2376**: Docker API (TCP)
- **2377**: Swarm management (TCP)
- **7946**: Container network discovery (TCP/UDP)
- **4789**: Overlay network traffic (UDP)

### Troubleshooting

Common issues and solutions:

1. **Cannot connect to Docker daemon**
   - Check firewall rules
   - Verify daemon.json syntax
   - Ensure systemd override is in place

2. **Swarm join fails**
   - Check network connectivity on port 2377
   - Verify join token is correct
   - Ensure time is synchronized between nodes

3. **TLS handshake failures**
   - Verify certificate paths
   - Check certificate validity
   - Ensure CA cert is trusted

## Conclusion

This architecture provides a robust foundation for multi-host Docker management and Swarm orchestration. Key benefits include:

1. **Scalability**: Support for unlimited Docker hosts with connection pooling
2. **Security**: Per-host access control and encrypted credential storage
3. **Performance**: Parallel operations and intelligent caching
4. **Flexibility**: Multiple connection types (Unix, TCP, SSH)
5. **Observability**: Comprehensive monitoring and audit logging
6. **User Experience**: Seamless host switching and aggregated views

The phased implementation approach ensures minimal disruption to existing functionality while progressively adding advanced features.