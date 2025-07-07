# WebSocket Agent Architecture

## Overview

This document describes the architecture for a WebSocket-based agent system that allows Docker hosts behind firewalls or NAT to connect to the Docker Control Platform without exposing their Docker TCP ports.

## Motivation

Currently, the Docker Control Platform connects to Docker hosts via TCP (ports 2375/2376), requiring hosts to:
- Have publicly accessible IP addresses or be on the same network
- Open firewall ports for incoming connections
- Maintain TLS certificates for secure connections

Many enterprise environments restrict inbound connections, making it impossible to manage Docker hosts in:
- Corporate networks with strict firewall rules
- Hosts behind NAT without port forwarding
- Air-gapped or semi-isolated networks
- Dynamic IP environments

## Architecture Overview

```
┌─────────────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│   Docker Host       │         │  Docker Control      │         │   Web Client    │
│                     │         │  Platform Server     │         │                 │
│ ┌─────────────────┐ │         │                      │         │                 │
│ │  Docker Daemon  │ │         │ ┌──────────────────┐ │         │                 │
│ │ (unix socket)   │ │         │ │ Agent Manager    │ │         │                 │
│ └────────┬────────┘ │         │ │                  │ │         │                 │
│          │          │         │ │ - Registry       │ │         │                 │
│ ┌────────▼────────┐ │         │ │ - Health Check   │ │         │                 │
│ │ Docker CTL      │ │ Outbound│ │ - Command Router │ │         │                 │
│ │ Agent           ├─┼─────────┼─┤                  │ │         │                 │
│ │                 │ │WebSocket│ └────────┬─────────┘ │         │                 │
│ │ - WS Client     │ │         │          │           │         │                 │
│ │ - Command Exec  │ │         │ ┌────────▼─────────┐ │         │                 │
│ │ - Health Report │ │         │ │ Docker Service   │ │         │   API/WS        │
│ └─────────────────┘ │         │ │ (Modified)       ├─┼─────────┼─────────────────┤
└─────────────────────┘         │ │                  │ │         │                 │
                                │ │ - Agent Adapter  │ │         │                 │
                                │ └──────────────────┘ │         └─────────────────┘
                                └──────────────────────┘
```

## Core Components

### 1. Docker CTL Agent

A lightweight Python/Go agent that runs on Docker hosts:

```python
# Key components
class DockerCtlAgent:
    def __init__(self, server_url: str, agent_id: str, auth_token: str):
        self.ws_client = WebSocketClient(server_url)
        self.docker_client = docker.from_env()
        self.command_handler = CommandHandler(self.docker_client)
        self.health_reporter = HealthReporter()
        
    async def connect(self):
        # Establish WebSocket connection with authentication
        # Handle reconnection logic
        # Start health reporting
        
    async def handle_command(self, command: dict):
        # Route commands to appropriate Docker operations
        # Return results via WebSocket
```

### 2. Agent Manager (Server Side)

Manages agent connections and lifecycle:

```python
class AgentManager:
    def __init__(self):
        self.agents: Dict[str, AgentConnection] = {}
        self.registry: AgentRegistry = AgentRegistry()
        
    async def register_agent(self, agent_id: str, connection: WebSocket):
        # Validate agent credentials
        # Store connection
        # Update database
        
    async def execute_command(self, agent_id: str, operation: str, params: dict):
        # Find agent connection
        # Send command
        # Wait for response with timeout
```

### 3. Modified Docker Service Architecture

Extend the existing adapter pattern to support agent connections:

```python
class AgentHostAdapter(DockerClientAdapter):
    """Adapter for Docker hosts connected via agents"""
    
    def __init__(self, agent_manager: AgentManager, agent_id: str):
        self.agent_manager = agent_manager
        self.agent_id = agent_id
        
    async def execute_operation(self, operation: str, **kwargs):
        # Send command to agent via WebSocket
        # Wait for response
        # Transform response to match expected format
```

## Communication Protocol

### WebSocket Endpoint
```
wss://control-platform.com/ws/agents/{agent_id}
```

### Message Format

All messages use JSON with the following structure:

```typescript
interface AgentMessage {
    id: string;           // Unique message ID for request/response matching
    type: MessageType;    // Type of message
    timestamp: string;    // ISO 8601 timestamp
    payload: any;         // Message-specific payload
}

enum MessageType {
    // Agent -> Server
    AUTH = "auth",
    HEARTBEAT = "heartbeat",
    COMMAND_RESPONSE = "command_response",
    EVENT = "event",
    ERROR = "error",
    
    // Server -> Agent
    AUTH_RESPONSE = "auth_response",
    COMMAND = "command",
    CONFIG_UPDATE = "config_update"
}
```

### Example Messages

#### Authentication Flow
```json
// Agent -> Server
{
    "id": "auth-001",
    "type": "auth",
    "timestamp": "2024-01-07T10:00:00Z",
    "payload": {
        "agent_id": "agent-prod-01",
        "auth_token": "jwt-token-here",
        "version": "1.0.0",
        "capabilities": ["docker", "docker-compose", "swarm"]
    }
}

// Server -> Agent
{
    "id": "auth-001",
    "type": "auth_response",
    "timestamp": "2024-01-07T10:00:01Z",
    "payload": {
        "status": "authenticated",
        "session_id": "session-123",
        "config": {
            "heartbeat_interval": 30,
            "command_timeout": 300
        }
    }
}
```

#### Command Execution
```json
// Server -> Agent
{
    "id": "cmd-001",
    "type": "command",
    "timestamp": "2024-01-07T10:05:00Z",
    "payload": {
        "operation": "container.list",
        "params": {
            "all": true,
            "filters": {"label": "app=web"}
        }
    }
}

// Agent -> Server
{
    "id": "cmd-001",
    "type": "command_response",
    "timestamp": "2024-01-07T10:05:01Z",
    "payload": {
        "status": "success",
        "data": [
            {
                "id": "abc123",
                "name": "web-1",
                "image": "nginx:latest",
                "status": "running"
            }
        ]
    }
}
```

## Security Considerations

### 1. Authentication & Authorization

- **Agent Authentication**: JWT tokens or API keys with expiration
- **Mutual TLS**: Optional mTLS for additional security
- **Role-Based Access**: Agents can have limited permissions
- **IP Allowlisting**: Optional IP restrictions for agent connections

### 2. Encryption

- **Transport Security**: All WebSocket connections use WSS (TLS)
- **Message Signing**: Optional HMAC signing of messages
- **Credential Storage**: Encrypted storage of agent credentials

### 3. Attack Prevention

- **Rate Limiting**: Limit command frequency per agent
- **Command Validation**: Whitelist allowed Docker operations
- **Resource Limits**: Prevent resource exhaustion attacks
- **Audit Logging**: Log all agent activities

### 4. Agent Isolation

- **Namespace Isolation**: Agents only see their assigned resources
- **Command Filtering**: Block potentially dangerous operations
- **Output Sanitization**: Clean command outputs before transmission

## Connection Lifecycle

### 1. Initial Connection
```
Agent                          Server
  |                              |
  |------ WebSocket Connect ---->|
  |                              |
  |<----- TLS Handshake -------->|
  |                              |
  |------ Auth Message --------->|
  |                              |
  |<---- Auth Response ----------|
  |                              |
  |------ First Heartbeat ------>|
  |                              |
```

### 2. Reconnection Logic

```python
class ReconnectionStrategy:
    def __init__(self):
        self.base_delay = 1.0
        self.max_delay = 60.0
        self.factor = 2.0
        
    def get_next_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (self.factor ** attempt), self.max_delay)
        # Add jitter to prevent thundering herd
        return delay + random.uniform(0, delay * 0.1)
```

### 3. Graceful Shutdown
- Agent sends disconnect message
- Server marks agent as offline
- Clean up resources
- Update database status

## Database Schema Extensions

### New Tables

```sql
-- Agent registration and management
CREATE TABLE docker_agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    host_id UUID REFERENCES docker_hosts(id),
    auth_token_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'disconnected',
    version VARCHAR(50),
    capabilities JSONB,
    last_heartbeat TIMESTAMP,
    connected_at TIMESTAMP,
    disconnected_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent connection events for monitoring
CREATE TABLE agent_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES docker_agents(id),
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX idx_agent_status ON docker_agents(status);
CREATE INDEX idx_agent_heartbeat ON docker_agents(last_heartbeat);
CREATE INDEX idx_agent_events_created ON agent_events(created_at);
```

### Modified Tables

```sql
-- Add connection_mode to docker_hosts
ALTER TABLE docker_hosts 
ADD COLUMN connection_mode VARCHAR(50) DEFAULT 'direct' 
CHECK (connection_mode IN ('direct', 'agent'));

-- Add agent_id reference
ALTER TABLE docker_hosts 
ADD COLUMN agent_id UUID REFERENCES docker_agents(id);
```

## Implementation Phases

### Phase 1: Agent Development
1. Basic WebSocket client
2. Docker command execution
3. Authentication flow
4. Health reporting

### Phase 2: Server Integration
1. Agent Manager service
2. WebSocket endpoint
3. AgentHostAdapter implementation
4. Database schema updates

### Phase 3: Security & Reliability
1. Implement reconnection logic
2. Add rate limiting
3. Implement audit logging
4. Add monitoring metrics

### Phase 4: Advanced Features
1. Agent auto-update mechanism
2. Multi-region support
3. Command queuing for offline agents
4. Agent grouping and bulk operations

## Monitoring & Observability

### Metrics to Track
- Agent connection count
- Command execution latency
- Reconnection frequency
- Command success/failure rates
- WebSocket message throughput

### Health Checks
- Agent heartbeat monitoring
- Docker daemon accessibility
- Network latency measurements
- Resource usage (CPU, memory, bandwidth)

## Configuration

### Agent Configuration (agent.yaml)
```yaml
server:
  url: wss://control-platform.com
  verify_ssl: true
  
agent:
  id: ${AGENT_ID}
  auth_token: ${AGENT_AUTH_TOKEN}
  
docker:
  socket: unix:///var/run/docker.sock
  timeout: 300
  
logging:
  level: info
  file: /var/log/docker-ctl-agent.log
  
reconnection:
  enabled: true
  max_attempts: -1  # Infinite
  base_delay: 1.0
  max_delay: 60.0
```

### Server Configuration
```python
# Addition to existing config
AGENT_CONFIG = {
    "websocket_timeout": 300,
    "heartbeat_interval": 30,
    "max_agents_per_host": 100,
    "command_timeout": 300,
    "enable_agent_mode": True,
}
```

## Future Enhancements

### 1. Agent Clustering
- Multiple agents per host for redundancy
- Load balancing between agents
- Automatic failover

### 2. Edge Computing Features
- Local command caching
- Offline operation mode
- Edge-to-edge communication

### 3. Advanced Security
- Zero-trust networking
- Hardware security module (HSM) support
- Certificate pinning

### 4. Performance Optimizations
- Binary protocol option (MessagePack/Protobuf)
- Command compression
- Intelligent caching

## Migration Strategy

### For Existing TCP Hosts
1. Deploy agent alongside existing TCP connection
2. Test agent connection in parallel
3. Switch connection_mode from 'direct' to 'agent'
4. Disable TCP port access

### Rollback Plan
1. Keep TCP configuration in database
2. Switch connection_mode back to 'direct'
3. Stop agent service
4. Re-enable TCP access

## Conclusion

The WebSocket agent architecture provides a secure, scalable solution for managing Docker hosts behind restrictive firewalls. By reversing the connection model, we enable management of previously inaccessible hosts while maintaining security and performance.