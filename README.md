# Docker Control Platform

A web-based platform for managing Docker environments with a React frontend and FastAPI backend.

## Features

### Phase 1 (Implemented)
- **Authentication & Authorization**: JWT-based auth with role-based access control (Admin, Operator, Viewer)
- **User Management**: Full CRUD operations for user accounts
- **Container Management**: Create, start, stop, restart, and remove containers
- **Image Management**: List, pull, and remove Docker images
- **System Information**: View Docker system info and statistics
- **Real-time Features**: 
  - Live container logs streaming with tail selection
  - Interactive container terminal (exec) with automatic shell detection
  - Real-time container stats monitoring with charts
  - WebSocket support for all real-time updates
- **Audit Logging**: Track all user actions for security and compliance
- **Rate Limiting**: Configurable rate limits on all API endpoints with Redis backend

See [WorkLog.md](WorkLog.md) for detailed implementation progress and [PLAN.md](PLAN.md) for the project roadmap.

## Tech Stack

### Backend
- FastAPI with async/await support
- PostgreSQL for data persistence
- Redis for caching and Celery broker
- Docker SDK for Python
- JWT authentication
- SQLAlchemy ORM with Alembic migrations

### Frontend
- React 18 with TypeScript
- Vite for fast development
- TanStack Query for server state
- Bootstrap 5 for UI components
- Zustand for client state
- WebSocket support for real-time features
- Recharts for data visualization
- xterm.js for terminal emulation

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Running with Docker Compose

1. Clone the repository:
```bash
git clone https://github.com/yourusername/docker-control-platform.git
cd docker-control-platform
```

2. Copy the environment file:
```bash
cp .env.example .env
```

3. Start all services:
```bash
docker-compose up -d
```

4. Initialize the database:
```bash
docker-compose exec backend python scripts/init_db.py
```

5. Access the application:
- Frontend: http://localhost
- API Documentation: http://localhost/api/v1/docs

### Default Credentials
- Email: `admin@localhost`
- Password: `changeme123`

**Important**: Change these credentials immediately after first login!

## Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

#### Unit Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

#### Integration Tests (Playwright)
```bash
# Install Playwright
npm install -g @playwright/test
playwright install

# Run tests
playwright test
```

## API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: http://localhost/api/v1/docs
- ReDoc: http://localhost/api/v1/redoc

## Security Features

- **JWT Authentication**: Short-lived access tokens (30 min) with refresh tokens (7 days)
- **Role-based Access Control (RBAC)**: Three roles - Admin, Operator, Viewer
- **Rate Limiting**: 
  - Global default: 100 requests/minute
  - Authentication endpoints: 5 requests/minute
  - Configurable per-endpoint limits
  - Redis-backed for distributed systems
- **Input Validation**: Pydantic schemas for all API inputs
- **Audit Logging**: Complete audit trail of all state-changing operations
- **Security Headers**: CORS, XSS protection, CSRF protection
- **Docker Socket Security**: Mounted read-only to prevent container escapes

## User Roles

### Admin
- Full system access
- User management
- System configuration
- All container and image operations

### Operator
- Container management (create, start, stop, remove)
- Image management (pull, remove)
- View system information

### Viewer
- View containers and images
- View system information
- Read-only access

## Configuration

### Environment Variables

Key configuration options (see `.env.example` for full list):

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_STRICT=10/minute
RATE_LIMIT_RELAXED=1000/hour

# JWT Settings
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql://user:pass@postgres/dbname

# Redis
REDIS_URL=redis://redis:6379/0
```

## Architecture

The platform follows clean architecture principles with:
- Separation of concerns
- Dependency injection
- Repository pattern for data access
- Service layer for business logic
- Comprehensive error handling
- WebSocket support for real-time features

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.