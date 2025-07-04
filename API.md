# Docker Control Platform API Documentation

## Overview

This document outlines the REST API structure for the Docker Control Platform, organized by development phases.

## Base URL

```
https://api.example.com/api/v1
```

## Authentication

All API requests (except auth endpoints) require a JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

## Common Response Formats

### Success Response
```json
{
  "data": <response_data>,
  "status": "success"
}
```

### Error Response
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  },
  "status": "error"
}
```

### Pagination
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

---

## Phase 1: Local Docker Management

### Authentication & User Management

#### Auth Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/login` | Login with credentials | No |
| POST | `/auth/logout` | Logout and invalidate token | Yes |
| POST | `/auth/refresh` | Refresh access token | No (refresh token) |
| GET | `/auth/me` | Get current user info | Yes |

#### User Management (Admin only)
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/users` | List all users | Admin |
| POST | `/users` | Create new user | Admin |
| GET | `/users/{id}` | Get user details | Admin |
| PUT | `/users/{id}` | Update user | Admin |
| DELETE | `/users/{id}` | Delete user | Admin |
| PUT | `/users/{id}/password` | Change user password | Admin or Self |

### Docker Resources

#### Containers
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/containers` | List containers | Viewer |
| POST | `/containers` | Create container | Operator |
| GET | `/containers/{id}` | Get container details | Viewer |
| PUT | `/containers/{id}` | Update container | Operator |
| DELETE | `/containers/{id}` | Remove container | Operator |
| POST | `/containers/{id}/start` | Start container | Operator |
| POST | `/containers/{id}/stop` | Stop container | Operator |
| POST | `/containers/{id}/restart` | Restart container | Operator |
| GET | `/containers/{id}/logs` | Get recent logs (paginated) | Viewer |
| GET | `/containers/{id}/stats` | Get container stats | Viewer |
| POST | `/containers/{id}/exec` | Execute command (non-interactive) | Operator |
| POST | `/containers/{id}/exec/interactive` | Start interactive session | Operator |

**Query Parameters for GET /containers:**
- `all` (boolean): Show all containers (default: false, shows only running)
- `limit` (integer): Limit number of containers
- `size` (boolean): Display total file sizes
- `filters` (string): JSON encoded filters (e.g., `{"status":"running"}`)

#### Images
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/images` | List images | Viewer |
| POST | `/images/pull` | Pull image (async) | Operator |
| GET | `/images/{id}` | Get image details | Viewer |
| DELETE | `/images/{id}` | Remove image | Operator |
| GET | `/images/{id}/history` | Get image history | Viewer |
| POST | `/images/prune` | Remove unused images | Admin |

**Pull Image Request:**
```json
{
  "image": "nginx:latest",
  "platform": "linux/amd64"
}
```

**Pull Image Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "websocket_url": "/ws/tasks/550e8400-e29b-41d4-a716-446655440000"
}
```

#### Volumes
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/volumes` | List volumes | Viewer |
| POST | `/volumes` | Create volume | Operator |
| GET | `/volumes/{name}` | Get volume details | Viewer |
| DELETE | `/volumes/{name}` | Remove volume | Operator |

#### Networks
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/networks` | List networks | Viewer |
| POST | `/networks` | Create network | Operator |
| GET | `/networks/{id}` | Get network details | Viewer |
| DELETE | `/networks/{id}` | Remove network | Operator |

#### System
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/system/info` | Get Docker system info | Viewer |
| GET | `/system/version` | Get Docker version | Viewer |
| GET | `/system/events` | Stream Docker events | Viewer |
| POST | `/system/prune` | System-wide prune | Admin |

### Task Management
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/tasks/{id}` | Get task status | Owner |
| GET | `/tasks` | List user's tasks | User |

**Task Status Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "image_pull",
  "status": "in_progress",
  "progress": 45,
  "message": "Pulling layer 3 of 7",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:01:00Z",
  "websocket_url": "/ws/tasks/550e8400-e29b-41d4-a716-446655440000"
}
```

### WebSocket Endpoints

All WebSocket endpoints require authentication via token in the connection URL:
```
ws://localhost/ws/containers/{id}/logs?token=<jwt_token>
```

| Endpoint | Description | Required Role |
|----------|-------------|---------------|
| `/ws/containers/{id}/logs` | Stream container logs in real-time | Viewer |
| `/ws/containers/{id}/exec` | Interactive terminal session | Operator |
| `/ws/containers/{id}/stats` | Stream container statistics | Viewer |
| `/ws/tasks/{id}` | Stream task progress updates | Owner |
| `/ws/events` | Stream Docker daemon events | Viewer |

**WebSocket Message Format:**
```json
{
  "type": "log|stats|event|error",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    // Message-specific payload
  }
}
```

---

## Phase 2: Multi-Server Support

### Server Management
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/servers` | List configured servers | Viewer |
| POST | `/servers` | Add new server | Admin |
| GET | `/servers/{id}` | Get server details | Viewer |
| PUT | `/servers/{id}` | Update server | Admin |
| DELETE | `/servers/{id}` | Remove server | Admin |
| GET | `/servers/{id}/health` | Check server health | Viewer |

### Server-Scoped Operations
All Phase 1 Docker endpoints can be prefixed with `/servers/{server_id}` to target specific servers:

```
GET /servers/{server_id}/containers
GET /servers/{server_id}/images
etc...
```

---

## Phase 3: Docker Swarm Support

### Nodes
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/nodes` | List swarm nodes | Viewer |
| GET | `/nodes/{id}` | Get node details | Viewer |
| PUT | `/nodes/{id}` | Update node | Admin |
| DELETE | `/nodes/{id}` | Remove node | Admin |

### Services
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/services` | List services | Viewer |
| POST | `/services` | Create service | Operator |
| GET | `/services/{id}` | Get service details | Viewer |
| PUT | `/services/{id}` | Update service | Operator |
| DELETE | `/services/{id}` | Remove service | Operator |
| POST | `/services/{id}/scale` | Scale service | Operator |
| GET | `/services/{id}/logs` | Get service logs | Viewer |

### Stacks
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/stacks` | List stacks | Viewer |
| POST | `/stacks` | Deploy stack | Operator |
| GET | `/stacks/{name}` | Get stack details | Viewer |
| PUT | `/stacks/{name}` | Update stack | Operator |
| DELETE | `/stacks/{name}` | Remove stack | Operator |

### Configs & Secrets
| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/configs` | List configs | Viewer |
| POST | `/configs` | Create config | Admin |
| GET | `/configs/{id}` | Get config details | Viewer |
| DELETE | `/configs/{id}` | Remove config | Admin |
| GET | `/secrets` | List secrets | Admin |
| POST | `/secrets` | Create secret | Admin |
| DELETE | `/secrets/{id}` | Remove secret | Admin |

---

## WebSocket Connection Management

### Connection Limits
- Maximum 100 concurrent WebSocket connections per user
- Idle timeout: 5 minutes (with ping/pong keepalive)
- Maximum message size: 1MB

### Authentication
WebSocket connections require JWT token passed as query parameter:
```javascript
const ws = new WebSocket(`ws://localhost/ws/containers/${id}/logs?token=${jwtToken}`);
```

## Rate Limiting

Rate limits are applied per user and IP address:

| Endpoint Type | Rate Limit |
|---------------|------------|
| Auth endpoints | 5 requests per minute |
| Read operations | 100 requests per minute |
| Write operations | 30 requests per minute |
| System operations | 10 requests per minute |

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Error Codes

| Code | Description |
|------|-------------|
| `AUTH_INVALID_CREDENTIALS` | Invalid username or password |
| `AUTH_TOKEN_EXPIRED` | JWT token has expired |
| `AUTH_INSUFFICIENT_PERMISSIONS` | User lacks required role |
| `DOCKER_CONNECTION_ERROR` | Cannot connect to Docker daemon |
| `DOCKER_CONTAINER_NOT_FOUND` | Container ID not found |
| `DOCKER_IMAGE_NOT_FOUND` | Image ID not found |
| `VALIDATION_ERROR` | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests |