# Development Guide

## Prerequisites

- Docker and Docker Compose installed
- Git
- A code editor (VSCode recommended)
- Postman or similar for API testing (optional)

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/docker-control-platform.git
cd docker-control-platform
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Default settings work for local development
```

### 3. Start Development Environment
```bash
# Start all services
docker-compose up

# Or run in background
docker-compose up -d

# Watch logs
docker-compose logs -f
```

This starts:
- **Nginx** on http://localhost (reverse proxy)
- **Backend API** (FastAPI with auto-reload)
- **Frontend** (React with Vite HMR)
- **PostgreSQL** (exposed on localhost:5432)
- **Redis** (exposed on localhost:6379)
- **Celery Worker** (background tasks)

### 4. Initialize Database
```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create admin user
docker-compose exec backend python scripts/init_db.py
```

## Development Workflow

### Backend Development

#### Code Structure
```
backend/
├── app/
│   ├── api/          # API endpoints
│   ├── core/         # Core functionality
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── main.py       # FastAPI app
```

#### Making Changes
1. **Code changes** - Automatically reload due to mounted volumes
2. **Adding dependencies**:
   ```bash
   # Install in container
   docker-compose exec backend pip install <package>
   
   # Update requirements.txt
   docker-compose exec backend pip freeze > requirements.txt
   
   # Rebuild image
   docker-compose build backend
   ```

#### Database Changes
```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Description"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback
docker-compose exec backend alembic downgrade -1
```

### Frontend Development

#### Code Structure
```
frontend/
├── src/
│   ├── components/   # Reusable components
│   ├── pages/        # Page components
│   ├── hooks/        # Custom React hooks
│   ├── api/          # API client
│   ├── utils/        # Utilities
│   └── App.tsx       # Main app component
```

#### Making Changes
1. **Code changes** - Vite HMR updates browser instantly
2. **Adding dependencies**:
   ```bash
   # Install in container
   docker-compose exec frontend npm install <package>
   
   # Rebuild image
   docker-compose build frontend
   ```

## Testing

### Backend Tests
```bash
# Run all tests
docker-compose exec backend pytest

# Run specific test
docker-compose exec backend pytest tests/test_auth.py

# With coverage
docker-compose exec backend pytest --cov=app --cov-report=html
```

### Frontend Tests
```bash
# Run tests
docker-compose exec frontend npm test

# Watch mode
docker-compose exec frontend npm test -- --watch

# Coverage
docker-compose exec frontend npm run test:coverage
```

### WebSocket Testing
```bash
# Using wscat
npm install -g wscat
wscat -c "ws://localhost/ws/containers/abc123/logs?token=YOUR_JWT_TOKEN"

# Or use Postman WebSocket support
```

## API Development

### Authentication
1. Login at `POST /api/v1/auth/login`
2. Get JWT token
3. Include in headers: `Authorization: Bearer <token>`
4. For WebSockets: `ws://localhost/ws/endpoint?token=<token>`

### OpenAPI Documentation
- Swagger UI: http://localhost/api/docs
- ReDoc: http://localhost/api/redoc

### Testing Endpoints
```bash
# Using curl
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@local", "password": "admin123"}'

# Get containers
curl http://localhost/api/v1/containers \
  -H "Authorization: Bearer <token>"
```

## Debugging

### Backend Debugging
```bash
# Access Python shell
docker-compose exec backend python

# View logs
docker-compose logs -f backend

# Debug with pdb
# Add to code: import pdb; pdb.set_trace()
# Then attach to container:
docker-compose exec backend /bin/bash
```

### Frontend Debugging
- Use browser DevTools
- React Developer Tools extension
- Network tab for API calls
- Console for errors

### Database Access
```bash
# PostgreSQL CLI
docker-compose exec db psql -U postgres docker_control

# Or use any PostgreSQL client on localhost:5432
```

### Redis Access
```bash
# Redis CLI
docker-compose exec redis redis-cli

# Or use any Redis client on localhost:6379
```

## Common Issues

### Port Already in Use
```bash
# Check what's using the port
lsof -i :80
lsof -i :5432

# Change ports in docker-compose.yml if needed
```

### Permission Issues
```bash
# Fix Docker socket permissions
sudo chmod 666 /var/run/docker.sock
```

### WebSocket Connection Failed
- Check Nginx logs: `docker-compose logs nginx`
- Verify token is valid
- Check browser console for errors

### Database Connection Issues
- Ensure PostgreSQL is running: `docker-compose ps`
- Check credentials in .env
- Verify DATABASE_URL format

## Production Build

### Backend
```bash
# Build production image
docker build -f backend/Dockerfile -t docker-control-backend backend/

# Run production mode
docker run -e DATABASE_URL=... docker-control-backend
```

### Frontend
```bash
# Build production image
docker build -f frontend/Dockerfile -t docker-control-frontend frontend/

# Or build locally
cd frontend
npm run build
# Output in dist/ directory
```

## Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes with proper tests
3. Ensure all tests pass
4. Update documentation if needed
5. Submit pull request

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)