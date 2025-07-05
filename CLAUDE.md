# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Docker Control Platform - A web-based platform for managing Docker environments with a React frontend and FastAPI backend. Built with a phased approach:
- **Phase 1**: Local Docker host management with authentication, user management, and rate limiting
- **Phase 2**: Multi-server support with kubectl-like CLI tool
- **Phase 3**: Docker Swarm orchestration features

## Git Guidelines
- Git commit message should never mention Claude 
- Never add any mention of Claude or claude in git commit messages

## Tech Stack

### Backend
- **FastAPI**: Modern async Python web framework
- **PostgreSQL**: User and configuration storage
- **Redis**: Caching and Celery message broker
- **Celery**: Background task processing
- **Docker SDK for Python**: Docker API integration
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migration management
- **Pydantic**: Data validation and settings management

### Frontend
- **React 18+** with TypeScript
- **Vite**: Build tool and dev server
- **TanStack Query**: Server state management
- **React Router**: Client-side routing
- **Tailwind CSS or MUI**: UI components

### Security & Auth
- **JWT tokens**: Access and refresh token pattern
- **SlowAPI**: Rate limiting
- **Passlib + bcrypt**: Password hashing
- **python-jose**: JWT creation/validation
- Future: Azure Entra ID integration

## Development Commands

### Quick Start
```bash
# Start all services with hot-reload enabled
docker-compose up

# Or run in background
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Backend Development
```bash
# Backend code is mounted as volume - changes auto-reload
# To add new Python packages:
docker-compose exec backend pip install <package>
# Then update requirements.txt and rebuild:
docker-compose build backend

# Run database migrations
docker-compose exec backend alembic upgrade head

# Create initial admin user
docker-compose exec backend python scripts/init_db.py

# Access Python shell
docker-compose exec backend python
```

### Frontend Development
```bash
# Frontend code is mounted as volume - Vite HMR handles updates
# To add new npm packages:
docker-compose exec frontend npm install <package>
# Then rebuild:
docker-compose build frontend
```

### Testing
```bash
# Backend tests
docker-compose exec backend pytest
docker-compose exec backend pytest --cov=app  # With coverage

# Frontend tests
docker-compose exec frontend npm test
docker-compose exec frontend npm run test:coverage
```

### Development URLs
- **Application**: http://localhost (through Nginx)
- **API**: http://localhost/api
- **WebSocket**: ws://localhost/ws
- **PostgreSQL**: localhost:5432 (for development tools)
- **Redis**: localhost:6379 (for development tools)

## Architecture

### API Structure
```
/api/users/         # User management (CRUD, login/logout)
/api/containers/    # Container operations
/api/images/        # Image management
/api/system/        # Docker system info
/api/tasks/         # Background task status
/ws/                # WebSocket endpoints
```

### Authentication Flow
1. POST `/api/users/login` → Receive access & refresh tokens
2. Include access token in requests: `Authorization: Bearer <token>`
3. Refresh token before expiration via `/api/users/refresh`
4. Three roles: `admin`, `operator`, `viewer`

### Real-time Features (WebSockets)
- Container logs streaming: `/ws/containers/{id}/logs`
- Container exec sessions: `/ws/containers/{id}/exec`
- Task progress updates: `/ws/tasks/{id}`
- Docker events: `/ws/events`
- Container stats: `/ws/containers/{id}/stats`

### Background Tasks (Celery)
- Long-running operations (image pulls, system prune)
- Return task ID immediately
- Monitor progress via WebSocket connection to `/ws/tasks/{id}`

### Database Models
- **User**: Authentication and authorization
- **RefreshToken**: Token management and revocation
- Future: Server configurations, audit logs

### Configuration
All settings via environment variables or `.env` file:
- `SECRET_KEY`: JWT signing key
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection
- `DOCKER_HOST`: Docker daemon socket/TCP address
- `RATE_LIMIT_*`: Rate limiting configuration

## Security Considerations
- Rate limiting on all endpoints (stricter on auth endpoints)
- JWT tokens with short expiration (30 min access, 7 day refresh)
- Role-based access control (RBAC)
- Docker socket mounted read-only
- Security headers (CORS, XSS protection, etc.)
- Prepared for Azure Entra ID integration
- Input validation to prevent command injection
- Audit logging for all state-changing operations

## Docker Integration
- Primary: Unix socket `/var/run/docker.sock`
- Alternative: TCP with TLS certificates
- Future: SSH connection support
- All Docker operations through Docker SDK for Python

## Key Architecture Components
- **Error Handling**: Standardized error responses with proper HTTP codes
- **Audit Logging**: Track all user actions for security and compliance
- **Health Checks**: Multiple endpoints for monitoring and orchestration
- **WebSocket Management**: Auto-reconnect, error handling, connection pooling
- **Security Layers**: Input validation, CORS, security headers, SQL injection prevention

See ARCHITECTURE.md for detailed implementation patterns.

## Development Architecture
- **Nginx**: Reverse proxy handling routing and WebSocket upgrades
- **Docker Compose**: Full stack development environment
- **Hot Reload**: Code mounted as volumes for instant updates
- **WebSocket-first**: Real-time features from the start