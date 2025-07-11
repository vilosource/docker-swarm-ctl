# Architecture Documentation

## Overview

Docker Control Platform is built with a microservices architecture using FastAPI (backend) and React (frontend), following SOLID principles and clean architecture patterns.

## Implementation Status

✅ **Phase 1 Completed** - Core functionality implemented including authentication, user management, container/image operations, and UI. See [WorkLog.md](WorkLog.md) for detailed progress tracking.

## Error Handling Strategy

### Standard Error Response Format

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      "additional": "context"
    },
    "field": "field_name"  // For validation errors
  },
  "status": "error",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Error Categories

```python
# Application Exceptions Hierarchy
AppException (500)
├── AuthenticationError (401)
│   ├── InvalidCredentialsError
│   ├── TokenExpiredError
│   └── TokenInvalidError
├── AuthorizationError (403)
│   ├── InsufficientPermissionsError
│   └── ResourceAccessDeniedError
├── ValidationError (400)
│   ├── InvalidInputError
│   └── MissingRequiredFieldError
├── ResourceError (404/409)
│   ├── ResourceNotFoundError (404)
│   └── ResourceConflictError (409)
└── ExternalServiceError (502/503)
    ├── DockerConnectionError (503)
    ├── DockerOperationError (502)
    └── DatabaseConnectionError (503)
```

### WebSocket Error Handling

WebSocket errors are sent as structured messages:

```json
{
  "type": "error",
  "code": "STREAM_ERROR",
  "message": "Failed to stream logs: Container not found",
  "timestamp": "2024-01-01T12:00:00Z",
  "reconnect": true,
  "fatal": false
}
```

Error types:
- `reconnect: true` - Client should attempt reconnection
- `fatal: true` - Close connection, do not reconnect
- `code` - Machine-readable error code for client handling

### Real-time Features (WebSockets)

Implemented WebSocket endpoints for real-time features:

1. **Container Logs Streaming** (`/ws/containers/{id}/logs`)
   - Stream container logs in real-time
   - Support for tail selection (last N lines)
   - Follow mode for continuous streaming
   - Timestamps and stream type (stdout/stderr)

2. **Container Exec Sessions** (`/ws/containers/{id}/exec`)
   - Interactive terminal sessions via WebSocket
   - Automatic shell detection (bash, sh, etc.)
   - Terminal resize support
   - Full TTY support with xterm.js frontend

3. **Container Stats Monitoring** (`/ws/containers/{id}/stats`)
   - Real-time CPU, memory, network, and block I/O statistics
   - Streaming updates every second
   - Formatted data ready for charting
   - Support for both Docker API versions

4. **Task Progress Updates** (`/ws/tasks/{id}`)
   - Monitor background task progress
   - Real-time status updates
   - Error reporting

5. **Docker Events** (`/ws/events`)
   - Stream Docker daemon events
   - Container lifecycle events
   - Image events
   - Network and volume events

### Global Error Handler

```python
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": str(exc),
                "details": exc.details
            },
            "status": "error",
            "request_id": request.state.request_id
        }
    )
```

## Audit Logging System

### Audit Log Schema

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Indexes for performance
    INDEX idx_audit_user_created (user_id, created_at DESC),
    INDEX idx_audit_action_created (action, created_at DESC),
    INDEX idx_audit_resource (resource_type, resource_id, created_at DESC)
);
```

### Audit Actions

Standard action format: `<resource>.<action>`

Examples:
- `auth.login` - User login
- `auth.logout` - User logout  
- `container.create` - Container created
- `container.start` - Container started
- `container.stop` - Container stopped
- `container.delete` - Container removed
- `image.pull` - Image pulled
- `image.delete` - Image removed
- `user.create` - User created
- `user.update` - User updated
- `user.delete` - User deleted

### Audit Implementation

```python
class AuditService:
    async def log(
        self,
        user: User,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        audit_log = AuditLog(
            user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        await self.repository.create(audit_log)

# Usage in endpoint
@router.post("/containers")
async def create_container(
    config: ContainerCreateRequest,
    audit: AuditService = Depends()
):
    container = await docker_service.create_container(config)
    await audit.log(
        user=current_user,
        action="container.create",
        resource_type="container",
        resource_id=container.id,
        details={"image": config.image, "name": config.name}
    )
    return container
```

## Frontend Architecture

### State Management (Zustand)

```typescript
// stores/index.ts
interface AppState {
  // Auth State
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  
  // Docker Resources
  containers: Container[];
  images: Image[];
  volumes: Volume[];
  networks: Network[];
  
  // UI State
  loading: Record<string, boolean>;
  errors: Record<string, Error>;
  
  // WebSocket Management
  connections: Map<string, WebSocket>;
  
  // Actions
  auth: {
    login: (credentials: LoginRequest) => Promise<void>;
    logout: () => void;
    refresh: () => Promise<void>;
  };
  
  docker: {
    fetchContainers: () => Promise<void>;
    startContainer: (id: string) => Promise<void>;
    stopContainer: (id: string) => Promise<void>;
    streamLogs: (id: string, onLog: (log: LogEntry) => void) => () => void;
  };
  
  ws: {
    connect: (url: string, handlers: WSHandlers) => void;
    disconnect: (url: string) => void;
    send: (url: string, data: any) => void;
  };
}
```

### WebSocket Management

```typescript
// hooks/useWebSocket.ts
interface UseWebSocketOptions {
  onOpen?: () => void;
  onMessage?: (data: any) => void;
  onError?: (error: Event) => void;
  onClose?: (event: CloseEvent) => void;
  autoReconnect?: boolean;
  reconnectDelay?: number;
  reconnectAttempts?: number;
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {}
) {
  const [state, setState] = useState<{
    connected: boolean;
    connecting: boolean;
    error: Error | null;
  }>({
    connected: false,
    connecting: false,
    error: null
  });

  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    
    setState(s => ({ ...s, connecting: true, error: null }));
    
    const token = useAuthStore(state => state.token);
    ws.current = new WebSocket(`${url}?token=${token}`);
    
    ws.current.onopen = () => {
      setState({ connected: true, connecting: false, error: null });
      reconnectCount.current = 0;
      options.onOpen?.();
    };
    
    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle errors
        if (data.type === 'error') {
          if (data.fatal) {
            ws.current?.close();
          }
          setState(s => ({ ...s, error: new Error(data.message) }));
          return;
        }
        
        options.onMessage?.(data);
      } catch (e) {
        console.error('WebSocket message parse error:', e);
      }
    };
    
    ws.current.onerror = (error) => {
      setState(s => ({ ...s, error: new Error('WebSocket error') }));
      options.onError?.(error);
    };
    
    ws.current.onclose = (event) => {
      setState({ connected: false, connecting: false, error: null });
      options.onClose?.(event);
      
      // Auto-reconnect logic
      if (
        options.autoReconnect &&
        reconnectCount.current < (options.reconnectAttempts || 5)
      ) {
        reconnectCount.current++;
        const delay = Math.min(
          1000 * Math.pow(2, reconnectCount.current),
          options.reconnectDelay || 30000
        );
        reconnectTimeout.current = setTimeout(connect, delay);
      }
    };
  }, [url, options]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimeout.current);
    ws.current?.close();
    ws.current = null;
  }, []);

  const send = useCallback((data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { ...state, send, reconnect: connect, disconnect };
}
```

### Component Structure

```typescript
// components/containers/LogViewer.tsx
export function LogViewer({ containerId }: { containerId: string }) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);
  
  const { connected, error } = useWebSocket(
    `/ws/containers/${containerId}/logs`,
    {
      onMessage: (data) => {
        if (data.type === 'log') {
          setLogs(prev => [...prev, data.data]);
          logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
      },
      autoReconnect: true,
      reconnectDelay: 5000
    }
  );
  
  return (
    <div className="log-viewer">
      {error && <Alert severity="error">{error.message}</Alert>}
      {!connected && <LinearProgress />}
      <pre className="log-content">
        {logs.map((log, i) => (
          <div key={i} className="log-line">
            {log.timestamp} {log.stream}: {log.message}
          </div>
        ))}
        <div ref={logEndRef} />
      </pre>
    </div>
  );
}
```

## Security Implementation

### Input Validation

All input is validated using Pydantic models:

```python
class ContainerCreateRequest(BaseModel):
    image: str = Field(
        ...,
        regex="^[a-zA-Z0-9][a-zA-Z0-9_.-/]+:[a-zA-Z0-9_.-]+$",
        description="Docker image name with tag"
    )
    name: Optional[str] = Field(
        None,
        regex="^[a-zA-Z0-9][a-zA-Z0-9_.-]+$",
        max_length=64
    )
    command: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    ports: Optional[Dict[str, int]] = None
    volumes: Optional[List[str]] = None
    
    @validator('command')
    def validate_command(cls, v):
        if v:
            # Prevent command injection
            forbidden_patterns = [
                r'[;&|`$]',  # Shell operators
                r'\$\(',      # Command substitution
                r'>\s*/',     # Redirect to system paths
            ]
            for cmd in v:
                for pattern in forbidden_patterns:
                    if re.search(pattern, cmd):
                        raise ValueError(f"Forbidden pattern in command: {pattern}")
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        if v:
            # Validate environment variable names
            for key in v.keys():
                if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
                    raise ValueError(f"Invalid environment variable name: {key}")
        return v
    
    @validator('volumes')
    def validate_volumes(cls, v):
        if v:
            # Prevent mounting sensitive host paths
            forbidden_paths = [
                '/etc', '/root', '/home', '/var/run/docker.sock',
                '/proc', '/sys', '/dev'
            ]
            for volume in v:
                host_path = volume.split(':')[0]
                if any(host_path.startswith(fp) for fp in forbidden_paths):
                    raise ValueError(f"Forbidden host path: {host_path}")
        return v
```

### CORS Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # CORS settings
    cors_origins: List[str] = Field(
        ["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
```

### Security Headers Middleware

```python
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Only in production
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:;"
        )
    
    return response
```

### SQL Injection Prevention

Using SQLAlchemy with parameterized queries:

```python
# Good - Parameterized query
async def get_user_by_email(email: str) -> Optional[User]:
    query = select(User).where(User.email == email)
    result = await session.execute(query)
    return result.scalar_one_or_none()

# Never do string concatenation
# BAD: query = f"SELECT * FROM users WHERE email = '{email}'"
```

## Health Check System

### Health Check Endpoints

```python
# api/v1/health.py
@router.get("/health", tags=["health"])
async def basic_health_check():
    """Basic health check for load balancers"""
    return {
        "status": "healthy",
        "service": "docker-control-api",
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/health/ready", tags=["health"])
async def readiness_check():
    """Readiness probe - checks if service is ready to accept traffic"""
    checks = {}
    
    # Check database
    try:
        await db.execute("SELECT 1")
        checks["database"] = "ready"
    except Exception:
        checks["database"] = "not_ready"
        
    # Check Redis
    try:
        await redis.ping()
        checks["redis"] = "ready"
    except Exception:
        checks["redis"] = "not_ready"
    
    all_ready = all(status == "ready" for status in checks.values())
    
    return JSONResponse(
        status_code=200 if all_ready else 503,
        content={
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@router.get("/health/live", tags=["health"])
async def liveness_check():
    """Liveness probe - checks if service is alive"""
    return {"alive": True, "timestamp": datetime.utcnow().isoformat()}

@router.get(
    "/health/detailed",
    tags=["health"],
    dependencies=[Depends(require_role("admin"))]
)
async def detailed_health_check():
    """Detailed health check with component status"""
    health_status = {
        "status": "checking",
        "timestamp": datetime.utcnow().isoformat(),
        "version": {
            "api": settings.app_version,
            "python": sys.version,
        },
        "components": {}
    }
    
    # Database check
    try:
        start = time.time()
        await db.execute("SELECT 1")
        health_status["components"]["database"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis check
    try:
        start = time.time()
        await redis.ping()
        info = await redis.info()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - start) * 1000, 2),
            "version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients")
        }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Docker check
    try:
        start = time.time()
        docker_client = get_docker_client()
        docker_info = docker_client.info()
        health_status["components"]["docker"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - start) * 1000, 2),
            "version": docker_info.get("ServerVersion"),
            "containers": docker_info.get("Containers"),
            "images": docker_info.get("Images")
        }
    except Exception as e:
        health_status["components"]["docker"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Celery check
    try:
        celery_status = celery_app.control.inspect().stats()
        if celery_status:
            worker_count = len(celery_status)
            health_status["components"]["celery"] = {
                "status": "healthy",
                "workers": worker_count
            }
        else:
            health_status["components"]["celery"] = {
                "status": "unhealthy",
                "error": "No workers available"
            }
    except Exception as e:
        health_status["components"]["celery"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Overall status
    all_healthy = all(
        component.get("status") == "healthy"
        for component in health_status["components"].values()
    )
    health_status["status"] = "healthy" if all_healthy else "unhealthy"
    
    return health_status
```

## Wizard Framework

### Overview

The platform includes a comprehensive wizard framework for guiding users through complex multi-step configuration processes. This is particularly useful for setting up SSH hosts, initializing swarm clusters, and deploying services.

### Wizard Architecture

```python
# Wizard Instance Model
class WizardInstance(BaseModel):
    id: UUID
    user_id: UUID
    wizard_type: WizardType  # e.g., "ssh_host_setup", "swarm_init"
    version: int
    resource_id: Optional[UUID]  # ID of created resource
    resource_type: Optional[str]  # Type of created resource
    current_step: int
    total_steps: int
    status: WizardStatus  # in_progress, completed, cancelled, failed
    state: Dict[str, Any]  # JSONB field for step data
    metadata: Dict[str, Any]  # JSONB field for wizard metadata
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
```

### SSH Host Setup Wizard

The SSH host setup wizard guides users through:

1. **Connection Details** - Host URL, SSH port, display name
2. **Authentication** - SSH key generation/import or password
3. **SSH Test** - Verify SSH connectivity
4. **Docker Test** - Verify Docker API access
5. **Confirmation** - Tags and finalization

Features:
- ED25519 SSH key generation
- Encrypted credential storage
- Connection testing with detailed feedback
- Pauseable/resumable wizard state
- Hosts created with `setup_pending` status

### Wizard API Endpoints

```python
# Start a new wizard
POST /api/v1/wizards/start
{
    "wizard_type": "ssh_host_setup",
    "initial_state": {}
}

# Update current step data
PUT /api/v1/wizards/{wizard_id}/step
{
    "step_data": {
        "connection_name": "Production Server",
        "host_url": "ssh://admin@server.example.com"
    }
}

# Navigate between steps
POST /api/v1/wizards/{wizard_id}/next
POST /api/v1/wizards/{wizard_id}/previous

# Test current step
POST /api/v1/wizards/{wizard_id}/test
{
    "test_type": "ssh_connection"
}

# Complete wizard
POST /api/v1/wizards/{wizard_id}/complete

# Cancel wizard
POST /api/v1/wizards/{wizard_id}/cancel

# Generate SSH key pair
POST /api/v1/wizards/generate-ssh-key?comment=user@host
```

### Frontend Wizard Components

```typescript
// Base wizard modal component
<WizardModal
    title="SSH Host Setup"
    currentStep={currentStep}
    totalSteps={totalSteps}
    onNext={handleNext}
    onPrevious={handlePrevious}
    onCancel={handleCancel}
>
    {renderCurrentStep()}
</WizardModal>

// Step components
<ConnectionDetailsStep wizard={wizard} onChange={updateStepData} />
<AuthenticationStep wizard={wizard} onChange={updateStepData} />
<SSHTestStep wizard={wizard} onTest={runTest} />
<DockerTestStep wizard={wizard} onTest={runTest} />
<ConfirmationStep wizard={wizard} onChange={updateStepData} />
```

### State Persistence

Wizard state is stored in PostgreSQL JSONB fields, allowing:
- Complex nested data structures
- Efficient querying
- Atomic updates
- Schema flexibility

Important: JSONB fields require reassignment for updates:
```python
# Correct way to update JSONB
new_state = dict(wizard.state)
new_state.update(step_data)
wizard.state = new_state  # Reassignment triggers SQLAlchemy tracking
```

## Initial Data & Seeds

### Database Initialization

```python
# scripts/init_db.py
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.security import get_password_hash
from app.db.session import async_session
from app.models import User
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    """Initialize database with required data"""
    async with async_session() as session:
        # Check if admin user exists
        result = await session.execute(
            select(User).where(User.email == "admin@localhost")
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            # Create admin user
            admin_user = User(
                email="admin@localhost",
                username="admin",
                full_name="System Administrator",
                role="admin",
                is_active=True,
                hashed_password=get_password_hash("changeme123")
            )
            session.add(admin_user)
            
            # Create demo users for development
            if settings.debug:
                demo_users = [
                    User(
                        email="operator@localhost",
                        username="operator",
                        full_name="Demo Operator",
                        role="operator",
                        is_active=True,
                        hashed_password=get_password_hash("demo123")
                    ),
                    User(
                        email="viewer@localhost",
                        username="viewer",
                        full_name="Demo Viewer",
                        role="viewer",
                        is_active=True,
                        hashed_password=get_password_hash("demo123")
                    )
                ]
                session.add_all(demo_users)
            
            await session.commit()
            
            print("=" * 60)
            print("DATABASE INITIALIZED")
            print("=" * 60)
            print("Admin user created:")
            print("  Email: admin@localhost")
            print("  Password: changeme123")
            print("")
            print("⚠️  IMPORTANT: Change this password immediately!")
            
            if settings.debug:
                print("")
                print("Demo users created (development only):")
                print("  operator@localhost / demo123 (Operator role)")
                print("  viewer@localhost / demo123 (Viewer role)")
            
            print("=" * 60)
        else:
            logger.info("Database already initialized")

async def create_sample_data():
    """Create sample data for development"""
    if not settings.debug:
        logger.warning("Sample data creation skipped in production")
        return
    
    # This would create sample containers, images, etc.
    # But since we're interfacing with real Docker, we skip this
    pass

if __name__ == "__main__":
    asyncio.run(init_db())