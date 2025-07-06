# Default Users Documentation

## Overview

The Docker Control Platform includes a database initialization system that creates default users for development and testing purposes. When volumes are deleted or the system is deployed fresh, these users need to be recreated.

## Database Initialization

### Automatic Initialization

When the backend starts, it automatically runs database migrations. However, users must be created manually using the initialization scripts.

### Initialize Default Users

```bash
# Ensure services are running
docker compose up -d

# Initialize the database with default admin
docker compose exec backend python scripts/init_db.py

# Create additional test users (optional)
docker compose exec backend python scripts/create_test_users.py
```

## Default Admin User

The system creates a default administrative user with the following credentials:

| Field | Value |
|-------|-------|
| Email | admin@localhost.local |
| Password | changeme123 |
| Username | admin |
| Role | admin |
| Full Name | System Administrator |

**⚠️ SECURITY WARNING**: This default password MUST be changed immediately in any non-development environment.

## Development Demo Users

When `DEBUG=true` is set in the environment, the init script also creates two demo users:

| Email | Password | Role | Purpose |
|-------|----------|------|---------|
| operator@localhost | demo123 | operator | Testing operator permissions |
| viewer@localhost | demo123 | viewer | Testing read-only access |

## Additional Test Users

The `create_test_users.py` script creates a comprehensive set of test users representing different teams and use cases:

### Team Structure

1. **DevOps Team**
   - Team Lead (admin role)
   - Senior Engineers (operator roles)
   
2. **Development Team**
   - Developers (viewer roles for read-only access)
   
3. **QA Team**
   - QA Lead (operator role for testing)
   - QA Engineers (viewer roles)
   
4. **Management**
   - Engineering Manager (viewer role for oversight)
   
5. **External Users**
   - Contractors (viewer roles with limited access)
   
6. **Service Accounts**
   - CI/CD automation (operator role)
   - Monitoring services (viewer role)

### Role Permissions

| Role | Permissions |
|------|------------|
| **admin** | • Full system access<br>• User management<br>• All Docker operations<br>• System configuration<br>• Multi-host management |
| **operator** | • Container lifecycle management<br>• Image operations<br>• Volume and network management<br>• Execute commands in containers<br>• View system information |
| **viewer** | • Read-only access to all resources<br>• View container logs<br>• View system statistics<br>• No modification capabilities |

## Environment Variables

The default admin credentials can be customized via environment variables:

```bash
# In .env file or docker-compose.yml
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your-secure-password
```

## Scripts

### init_db.py

Location: `/backend/scripts/init_db.py`

- Creates the default admin user
- Creates demo users in debug mode
- Checks for existing users to avoid duplicates
- Uses async SQLAlchemy for database operations

### create_test_users.py

Location: `/backend/scripts/create_test_users.py`

- Creates 11 additional test users
- Represents different teams and roles
- Includes service accounts for automation
- Shows detailed output of created users

## Password Management

### Changing the Admin Password

```python
# Via backend shell
docker compose exec backend python

# In Python shell:
import asyncio
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.password import get_password_hash
from sqlalchemy import select

async def change_password(email, new_password):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one()
        user.hashed_password = get_password_hash(new_password)
        await session.commit()
        print(f"Password changed for {email}")

asyncio.run(change_password("admin@localhost.local", "new_secure_password"))
```

### Password Requirements

- Passwords are hashed using bcrypt
- No default password complexity requirements (add via Pydantic validators if needed)
- Stored in `hashed_password` field in the database

## Resetting the User Database

If you need to start fresh:

```bash
# Stop all services
docker compose down

# Remove the postgres volume
docker volume rm docker-swarm-ctl_postgres_data

# Start services again
docker compose up -d

# Re-run initialization
docker compose exec backend python scripts/init_db.py
```

## Security Considerations

1. **Production Deployment**
   - Never use default credentials in production
   - Implement proper secret management
   - Use environment-specific configuration
   - Enable audit logging for user actions

2. **Password Policy**
   - Implement password complexity requirements
   - Add password expiration if required
   - Consider multi-factor authentication

3. **Service Accounts**
   - Use API tokens instead of passwords for automation
   - Implement token rotation
   - Limit permissions to minimum required

## Troubleshooting

### Users Not Created

If the init script reports "Database already initialized":
- Check if users already exist in the database
- Use the create_test_users.py script for additional users
- Reset the database if needed (see above)

### Login Issues

1. Verify the backend is running: `docker compose ps`
2. Check logs: `docker compose logs backend`
3. Ensure database migrations ran: Check for alembic_version table
4. Verify user exists: Use database query tools

### Email Domain Issues

The default admin uses `@localhost.local` domain which is configured to pass email validation in the development environment. This is set in the backend configuration to allow `.local` domains.