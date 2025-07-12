#!/usr/bin/env python3
"""
Simple script to reset a specific circuit breaker
"""

import asyncio
import sys

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.services.circuit_breaker import get_circuit_breaker_manager


async def reset_circuit_breaker(host_id: str):
    """Reset circuit breaker for a specific host"""
    manager = get_circuit_breaker_manager()
    breaker_name = f"docker-host-{host_id}"
    
    try:
        await manager.reset(breaker_name)
        print(f"✓ Circuit breaker '{breaker_name}' has been reset")
    except Exception as e:
        print(f"✗ Failed to reset circuit breaker: {e}")


async def main():
    # The host ID from the error message
    host_id = "46bcfe68-af69-43b6-a500-f137d3a299c8"
    await reset_circuit_breaker(host_id)


if __name__ == "__main__":
    asyncio.run(main())