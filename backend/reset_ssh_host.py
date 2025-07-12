#!/usr/bin/env python3
"""
Reset SSH host circuit breaker

Quick script to reset the circuit breaker for the SSH host that was created earlier.
"""

import asyncio
import sys

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.services.circuit_breaker import get_circuit_breaker_manager


async def main():
    # The host ID from the error message
    host_id = "a6ec5de1-e617-43b4-9dd7-20fd97fd618d"
    
    # Reset circuit breaker
    manager = get_circuit_breaker_manager()
    breaker_name = f"docker-host-{host_id}"
    
    try:
        await manager.reset(breaker_name)
        print(f"✅ Circuit breaker '{breaker_name}' has been reset")
        print("\nThe SSH host can now be accessed again.")
        print("Note: SSH connections require proper credentials to work.")
    except Exception as e:
        print(f"❌ Failed to reset circuit breaker: {e}")


if __name__ == "__main__":
    asyncio.run(main())