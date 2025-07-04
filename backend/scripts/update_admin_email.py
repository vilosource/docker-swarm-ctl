#!/usr/bin/env python3
"""Update admin user email to valid format."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import update
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def update_admin_email():
    async with AsyncSessionLocal() as db:
        # Update admin email
        result = await db.execute(
            update(User)
            .where(User.email == "admin@localhost")
            .values(email="admin@localhost.local")
        )
        await db.commit()
        print(f"Updated {result.rowcount} user(s)")


if __name__ == "__main__":
    asyncio.run(update_admin_email())