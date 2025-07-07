#!/usr/bin/env python3
"""
Test rate limiting on authentication endpoints
"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"


async def test_login_rate_limit():
    """Test rate limiting on login endpoint"""
    print("Testing login rate limit (5/minute)...")
    
    async with aiohttp.ClientSession() as session:
        # Try to login 7 times rapidly
        for i in range(7):
            data = {
                "username": f"test{i}@example.com",
                "password": "wrongpassword"
            }
            
            try:
                async with session.post(
                    f"{BASE_URL}/auth/login",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as resp:
                    status = resp.status
                    headers = resp.headers
                    body = await resp.text()
                    
                    print(f"\nAttempt {i+1}:")
                    print(f"  Status: {status}")
                    
                    # Check rate limit headers
                    if "X-RateLimit-Limit" in headers:
                        print(f"  Rate Limit: {headers['X-RateLimit-Limit']}")
                        print(f"  Remaining: {headers.get('X-RateLimit-Remaining', 'N/A')}")
                        print(f"  Reset: {headers.get('X-RateLimit-Reset', 'N/A')}")
                    
                    if status == 429:
                        print(f"  ❌ Rate limit exceeded!")
                        response_data = json.loads(body)
                        print(f"  Message: {response_data.get('detail', 'N/A')}")
                    elif status == 401:
                        print(f"  ✅ Normal auth failure (rate limit not hit)")
                    
            except Exception as e:
                print(f"  Error: {str(e)}")
            
            await asyncio.sleep(0.1)  # Small delay between requests


async def test_authenticated_rate_limit():
    """Test rate limiting on authenticated endpoints"""
    print("\n\nTesting authenticated endpoint rate limit...")
    
    # Wait a bit to avoid hitting the login rate limit from previous test
    await asyncio.sleep(2)
    
    # First, login to get a token
    async with aiohttp.ClientSession() as session:
        data = {
            "username": "admin@localhost",
            "password": "changeme123"
        }
        
        async with session.post(
            f"{BASE_URL}/auth/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        ) as resp:
            if resp.status == 200:
                tokens = await resp.json()
                access_token = tokens["access_token"]
                print("✅ Successfully logged in")
            else:
                print("❌ Failed to login")
                return
        
        # Now test container listing with rate limit
        print("\nTesting container list endpoint (100/minute default)...")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Make 5 rapid requests (should all succeed)
        for i in range(5):
            async with session.get(
                f"{BASE_URL}/containers/",
                headers=headers
            ) as resp:
                print(f"\nRequest {i+1}:")
                print(f"  Status: {resp.status}")
                if "X-RateLimit-Limit" in resp.headers:
                    print(f"  Rate Limit: {resp.headers['X-RateLimit-Limit']}")
                    print(f"  Remaining: {resp.headers.get('X-RateLimit-Remaining', 'N/A')}")


async def main():
    """Run all rate limit tests"""
    print("=" * 60)
    print("RATE LIMITING TESTS")
    print("=" * 60)
    
    await test_login_rate_limit()
    await test_authenticated_rate_limit()
    
    print("\n" + "=" * 60)
    print("Tests completed!")


if __name__ == "__main__":
    asyncio.run(main())