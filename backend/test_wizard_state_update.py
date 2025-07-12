#!/usr/bin/env python3
"""
Test wizard state update directly
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import WizardInstance
from app.core.config import settings
import json

async def test_state_update():
    # Create database connection
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Get the most recent wizard
        result = await session.execute(
            select(WizardInstance).order_by(WizardInstance.created_at.desc()).limit(1)
        )
        wizard = result.scalar_one_or_none()
        
        if not wizard:
            print("No wizards found")
            return
        
        print(f"Testing with wizard: {wizard.id}")
        print(f"Current state: {wizard.state}")
        
        # Try to update the state directly
        test_state = {
            "test_key": "test_value",
            "connection_name": "Test Connection",
            "host_url": "ssh://test@example.com"
        }
        
        # Method 1: Direct assignment
        wizard.state = test_state
        
        # Commit and refresh
        await session.commit()
        await session.refresh(wizard)
        
        print(f"After update state: {wizard.state}")
        
        # Verify by re-querying
        result2 = await session.execute(
            select(WizardInstance).where(WizardInstance.id == wizard.id)
        )
        wizard2 = result2.scalar_one()
        print(f"Re-queried state: {wizard2.state}")

if __name__ == "__main__":
    asyncio.run(test_state_update())