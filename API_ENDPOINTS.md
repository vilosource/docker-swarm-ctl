# Docker Control Platform API Endpoints

This document provides a complete reference of all available API endpoints in the Docker Control Platform.

## Base URLs

- **Web Application**: http://localhost
- **API Base URL**: http://localhost/api/v1
- **Swagger UI Documentation**: http://localhost/api/v1/docs
- **OpenAPI Specification**: http://localhost/api/v1/openapi.json

## Authentication

The API uses JWT (JSON Web Token) authentication. Most endpoints require authentication.

### Authentication Flow
1. Login with username/password to receive access and refresh tokens
2. Include access token in requests: `Authorization: Bearer <access_token>`
3. Access tokens expire after 30 minutes
4. Use refresh token to get new access token before expiration
5. Refresh tokens expire after 7 days

### User Roles
- **admin**: Full system access
- **operator**: Can manage containers and images
- **viewer**: Read-only access

## API Endpoints

### Public Endpoints (No Authentication Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get API information and version |
| POST | `/api/v1/auth/login` | User login (returns tokens) |
| GET | `/api/v1/health/` | Basic health check |

### Authentication Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/login` | Login with username/password | None |
| POST | `/api/v1/auth/refresh` | Refresh access token | Any authenticated |
| POST | `/api/v1/auth/logout` | Logout and revoke refresh token | Any authenticated |

### User Management Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/api/v1/users/` | List all users | admin |
| POST | `/api/v1/users/` | Create new user | admin |
| GET | `/api/v1/users/me` | Get current user info | Any authenticated |
| GET | `/api/v1/users/{user_id}` | Get specific user | admin |
| PUT | `/api/v1/users/{user_id}` | Update user | admin |
| DELETE | `/api/v1/users/{user_id}` | Delete user | admin |

### Container Management Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/api/v1/containers/` | List all containers | viewer+ |
| POST | `/api/v1/containers/` | Create new container | operator+ |
| GET | `/api/v1/containers/{container_id}` | Get container details | viewer+ |
| POST | `/api/v1/containers/{container_id}/start` | Start container | operator+ |
| POST | `/api/v1/containers/{container_id}/stop` | Stop container | operator+ |
| POST | `/api/v1/containers/{container_id}/restart` | Restart container | operator+ |
| DELETE | `/api/v1/containers/{container_id}` | Remove container | operator+ |
| GET | `/api/v1/containers/{container_id}/logs` | Get container logs | viewer+ |
| GET | `/api/v1/containers/{container_id}/stats` | Get container statistics | viewer+ |

### Image Management Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/api/v1/images/` | List all images | viewer+ |
| POST | `/api/v1/images/pull` | Pull image (returns task ID) | operator+ |
| GET | `/api/v1/images/{image_id}` | Get image details | viewer+ |
| DELETE | `/api/v1/images/{image_id}` | Remove image | operator+ |
| GET | `/api/v1/images/{image_id}/history` | Get image history | viewer+ |
| POST | `/api/v1/images/prune` | Prune unused images | admin |

### System Information Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/api/v1/system/info` | Get Docker system information | viewer+ |
| GET | `/api/v1/system/version` | Get Docker version | viewer+ |
| POST | `/api/v1/system/prune` | System-wide prune | admin |
| GET | `/api/v1/system/df` | Get disk usage statistics | viewer+ |

### Health Check Endpoints

| Method | Endpoint | Description | Required Role |
|--------|----------|-------------|---------------|
| GET | `/api/v1/health/` | Basic health check | None |
| GET | `/api/v1/health/ready` | Readiness check (DB & Redis) | None |
| GET | `/api/v1/health/live` | Liveness check | None |
| GET | `/api/v1/health/detailed` | Detailed health status | admin |

## WebSocket Endpoints (Planned)

These WebSocket endpoints are documented but not yet implemented:

| Endpoint | Description |
|----------|-------------|
| `/ws/containers/{id}/logs` | Stream container logs in real-time |
| `/ws/containers/{id}/exec` | Interactive container exec sessions |
| `/ws/tasks/{id}` | Monitor background task progress |
| `/ws/events` | Stream Docker events |
| `/ws/containers/{id}/stats` | Stream container statistics |

## Rate Limiting

- Default rate limit: 100 requests per minute
- Authentication endpoints: 5 requests per minute
- Rate limits are per IP address

## Request/Response Format

### Request Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Standard Error Response
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Successful Response Examples

#### Login Response
```json
{
  "access_token": "eyJ0eXAiOiJKV1...",
  "refresh_token": "eyJ0eXAiOiJKV1...",
  "token_type": "bearer"
}
```

#### User Response
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Container Response
```json
{
  "id": "abc123...",
  "name": "my-container",
  "image": "nginx:latest",
  "status": "running",
  "ports": {
    "80/tcp": [{"HostPort": "8080"}]
  },
  "created": "2024-01-01T00:00:00Z"
}
```

## Testing the API

### Using Swagger UI
1. Navigate to http://localhost/api/v1/docs
2. Click "Authorize" and enter your access token
3. Try out any endpoint interactively

### Using curl

#### Login
```bash
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

#### Get Containers
```bash
curl -X GET http://localhost/api/v1/containers/ \
  -H "Authorization: Bearer <access_token>"
```

#### Pull Image
```bash
curl -X POST http://localhost/api/v1/images/pull \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"image": "nginx:latest"}'
```

## Notes

- All timestamps are in ISO 8601 format (UTC)
- Container and image IDs can be either full IDs or short IDs
- Background operations (like image pulls) return a task ID for tracking progress
- All state-changing operations are logged for audit purposes
- CORS is configured to allow requests from localhost origins