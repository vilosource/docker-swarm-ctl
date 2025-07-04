#!/usr/bin/env python3
"""Clean up duplicate refresh tokens from the database."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.refresh_token import RefreshToken


async def cleanup_tokens():
    async with AsyncSessionLocal() as db:
        # Delete all refresh tokens to start fresh
        result = await db.execute(delete(RefreshToken))
        await db.commit()
        print(f"Deleted {result.rowcount} refresh tokens")


if __name__ == "__main__":
    asyncio.run(cleanup_tokens())