#!/usr/bin/env python3
"""
Generate Docker events for testing the events streaming
"""

import docker
import time
import random

def main():
    client = docker.from_env()
    
    print("Generating Docker events...")
    print("You can watch these events in the web UI at http://localhost/events")
    print("-" * 60)
    
    # Pull a small image
    print("1. Pulling alpine:latest image...")
    client.images.pull("alpine:latest")
    time.sleep(1)
    
    # Create a container
    print("2. Creating test container...")
    container = client.containers.create(
        "alpine:latest",
        command="sleep 300",
        name=f"test-events-{random.randint(1000, 9999)}",
        labels={"test": "events"}
    )
    print(f"   Created container: {container.name}")
    time.sleep(1)
    
    # Start the container
    print("3. Starting container...")
    container.start()
    time.sleep(2)
    
    # Create a network
    print("4. Creating test network...")
    network = client.networks.create(
        name=f"test-network-{random.randint(1000, 9999)}",
        labels={"test": "events"}
    )
    print(f"   Created network: {network.name}")
    time.sleep(1)
    
    # Connect container to network
    print("5. Connecting container to network...")
    network.connect(container)
    time.sleep(1)
    
    # Create a volume
    print("6. Creating test volume...")
    volume = client.volumes.create(
        name=f"test-volume-{random.randint(1000, 9999)}",
        labels={"test": "events"}
    )
    print(f"   Created volume: {volume.name}")
    time.sleep(1)
    
    # Stop the container
    print("7. Stopping container...")
    container.stop()
    time.sleep(1)
    
    # Remove everything
    print("8. Cleaning up...")
    print("   Removing container...")
    container.remove()
    time.sleep(1)
    
    print("   Removing network...")
    network.remove()
    time.sleep(1)
    
    print("   Removing volume...")
    volume.remove()
    
    print("\nDone! Check the events page to see all the generated events.")


if __name__ == "__main__":
    main()