import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.password import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.config import settings
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db():
    """Initialize database with required data"""
    async with AsyncSessionLocal() as session:
        # Check if admin user exists
        result = await session.execute(
            select(User).where(User.email == settings.admin_email)
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            # Create admin user
            admin_user = User(
                email=settings.admin_email,
                username="admin",
                full_name="System Administrator",
                role="admin",
                is_active=True,
                hashed_password=get_password_hash(settings.admin_password)
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
            print(f"  Email: {settings.admin_email}")
            print(f"  Password: {settings.admin_password}")
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


if __name__ == "__main__":
    asyncio.run(init_db())