#!/usr/bin/env python3
"""
Test how Docker service logs work
"""
import docker

client = docker.from_env()

# Find nginx service
services = client.services.list()
nginx_service = None

for service in services:
    if service.name == "nginx-web":
        nginx_service = service
        break

if nginx_service:
    print(f"Found service: {nginx_service.name} ({nginx_service.id})")
    print("\nTesting service.logs() parameters...")
    
    # Test what parameters are accepted
    try:
        # Get logs without follow
        logs = nginx_service.logs(tail=10, timestamps=True, stdout=True, stderr=True)
        print(f"✓ Got logs (no follow): {type(logs)}")
        if isinstance(logs, bytes):
            print(f"  First 200 chars: {logs[:200]}")
    except Exception as e:
        print(f"✗ Error without follow: {e}")
    
    try:
        # Get logs with follow
        logs_gen = nginx_service.logs(follow=True, tail=10, timestamps=True, stdout=True, stderr=True)
        print(f"✓ Got logs (with follow): {type(logs_gen)}")
        
        # Try to read first few lines
        count = 0
        for line in logs_gen:
            print(f"  Line {count+1}: {line[:50]}...")
            count += 1
            if count >= 3:
                break
    except Exception as e:
        print(f"✗ Error with follow: {e}")
else:
    print("nginx-web service not found")