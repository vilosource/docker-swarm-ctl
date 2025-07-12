#!/usr/bin/env python3
"""
Debug wizard state persistence issue
"""

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import WizardInstance
import json

# Use database URL from environment or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/docker_control")

async def check_wizard_state():
    # Create database connection
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Get all wizards ordered by created_at desc
        result = await session.execute(
            select(WizardInstance).order_by(WizardInstance.created_at.desc()).limit(5)
        )
        wizards = result.scalars().all()
        
        print("=== Recent Wizards ===")
        for wizard in wizards:
            print(f"\nWizard ID: {wizard.id}")
            print(f"  Type: {wizard.wizard_type}")
            print(f"  Status: {wizard.status}")
            print(f"  Current Step: {wizard.current_step}/{wizard.total_steps}")
            print(f"  Created: {wizard.created_at}")
            print(f"  Updated: {wizard.updated_at}")
            print(f"  State Keys: {list(wizard.state.keys()) if wizard.state else 'Empty'}")
            
            if wizard.state:
                # Show state content (hiding sensitive data)
                safe_state = {}
                for key, value in wizard.state.items():
                    if key in ['private_key', 'public_key', 'password', 'key_passphrase']:
                        safe_state[key] = "***HIDDEN***" if value else None
                    else:
                        safe_state[key] = value
                print(f"  State: {json.dumps(safe_state, indent=4)}")
            else:
                print(f"  State: Empty")
            
            print(f"  Metadata: {wizard.wizard_metadata}")

if __name__ == "__main__":
    asyncio.run(check_wizard_state())