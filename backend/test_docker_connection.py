#!/usr/bin/env python3
"""Test Docker connection"""

import docker

# Test different connection methods
connections = [
    ("host.docker.internal:2375", "tcp://host.docker.internal:2375"),
    ("localhost:2375", "tcp://localhost:2375"),
    ("127.0.0.1:2375", "tcp://127.0.0.1:2375"),
]

for name, url in connections:
    try:
        client = docker.DockerClient(base_url=url)
        version = client.version()
        print(f"✓ {name}: Connected successfully")
        print(f"  Docker version: {version['Version']}")
    except Exception as e:
        print(f"✗ {name}: {str(e)}")