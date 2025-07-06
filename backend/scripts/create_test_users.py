import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.password import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_test_users():
    """Create additional test users for different scenarios"""
    
    test_users = [
        # DevOps Team Members
        {
            "email": "sarah.chen@example.com",
            "username": "schen",
            "full_name": "Sarah Chen",
            "role": "admin",
            "password": "devops2024",
            "description": "DevOps Team Lead"
        },
        {
            "email": "mike.johnson@example.com",
            "username": "mjohnson",
            "full_name": "Mike Johnson",
            "role": "operator",
            "password": "docker2024",
            "description": "Senior DevOps Engineer"
        },
        {
            "email": "emily.williams@example.com",
            "username": "ewilliams",
            "full_name": "Emily Williams",
            "role": "operator",
            "password": "container2024",
            "description": "DevOps Engineer"
        },
        
        # Development Team
        {
            "email": "alex.kumar@example.com",
            "username": "akumar",
            "full_name": "Alex Kumar",
            "role": "viewer",
            "password": "dev2024",
            "description": "Senior Developer"
        },
        {
            "email": "lisa.park@example.com",
            "username": "lpark",
            "full_name": "Lisa Park",
            "role": "viewer",
            "password": "code2024",
            "description": "Full Stack Developer"
        },
        
        # QA Team
        {
            "email": "james.martinez@example.com",
            "username": "jmartinez",
            "full_name": "James Martinez",
            "role": "operator",
            "password": "qa2024",
            "description": "QA Lead"
        },
        {
            "email": "nina.patel@example.com",
            "username": "npatel",
            "full_name": "Nina Patel",
            "role": "viewer",
            "password": "test2024",
            "description": "QA Engineer"
        },
        
        # Management
        {
            "email": "robert.taylor@example.com",
            "username": "rtaylor",
            "full_name": "Robert Taylor",
            "role": "viewer",
            "password": "manager2024",
            "description": "Engineering Manager"
        },
        
        # External Contractors
        {
            "email": "contractor1@external.com",
            "username": "contractor1",
            "full_name": "External Contractor 1",
            "role": "viewer",
            "password": "external2024",
            "description": "External Consultant"
        },
        
        # Service Accounts (for automation)
        {
            "email": "ci.automation@example.com",
            "username": "ci_bot",
            "full_name": "CI/CD Automation",
            "role": "operator",
            "password": "ci_token_2024",
            "description": "Automated CI/CD Pipeline"
        },
        {
            "email": "monitoring@example.com",
            "username": "monitor_bot",
            "full_name": "Monitoring Service",
            "role": "viewer",
            "password": "monitor_token_2024",
            "description": "Monitoring and Alerting Service"
        }
    ]
    
    async with AsyncSessionLocal() as session:
        created_users = []
        skipped_users = []
        
        for user_data in test_users:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                skipped_users.append(user_data["email"])
                continue
            
            # Create new user
            new_user = User(
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=True,
                hashed_password=get_password_hash(user_data["password"])
            )
            session.add(new_user)
            created_users.append(user_data)
        
        await session.commit()
        
        # Print results
        print("=" * 80)
        print("TEST USERS CREATION RESULTS")
        print("=" * 80)
        
        if created_users:
            print("\n✅ CREATED USERS:")
            print("-" * 80)
            print(f"{'Email':<35} {'Username':<15} {'Role':<10} {'Password':<15} {'Description'}")
            print("-" * 80)
            for user in created_users:
                print(f"{user['email']:<35} {user['username']:<15} {user['role']:<10} {user['password']:<15} {user['description']}")
        
        if skipped_users:
            print("\n⚠️  SKIPPED (already exist):")
            for email in skipped_users:
                print(f"  - {email}")
        
        print("\n" + "=" * 80)
        print("USER ROLE PERMISSIONS:")
        print("=" * 80)
        print("🔐 Admin: Full system access, user management, all Docker operations")
        print("🔧 Operator: Container/image/volume/network management, execute commands")
        print("👁️  Viewer: Read-only access to containers, images, and system info")
        print("=" * 80)
        
        # Show total user count
        result = await session.execute(select(User))
        all_users = result.scalars().all()
        print(f"\nTotal users in database: {len(all_users)}")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(create_test_users())