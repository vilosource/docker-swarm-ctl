import pytest
import subprocess
import time
import os
import requests

@pytest.fixture(scope="session")
def setup_e2e_environment():
    print("\nSetting up E2E test environment...")

    # 1. Bring up the DinD Swarm manager
    print("Bringing up DinD Swarm manager...")
    subprocess.run(["docker", "compose", "-f", "docker-compose.test.yml", "up", "-d"], check=True)

    # 2. Get the IP address of the swarm-manager container
    print("Getting Swarm Manager IP...")
    result = subprocess.run(
        ["docker", "inspect", "-f", '{{.NetworkSettings.Networks.test_net.IPAddress}}', 
         "$(docker-compose -f docker-compose.test.yml ps -q swarm-manager)"],
        capture_output=True, text=True, check=True
    )
    swarm_manager_ip = result.stdout.strip()
    print(f"Swarm Manager IP: {swarm_manager_ip}")

    # 3. Wait for the DinD daemon to be ready
    print("Waiting for Swarm Manager Docker daemon to be ready...")
    docker_host = f"tcp://{swarm_manager_ip}:2375"
    for _ in range(60): # Max 60 seconds wait
        try:
            subprocess.run(["docker", "-H", docker_host, "info"], check=True, capture_output=True)
            break
        except subprocess.CalledProcessError:
            time.sleep(1)
    else:
        raise RuntimeError("DinD Docker daemon did not become ready in time.")
    print("Swarm Manager Docker daemon is ready.")

    # 4. Initialize the Swarm on the DinD manager
    print("Initializing Swarm on manager...")
    subprocess.run(["docker", "-H", docker_host, "swarm", "init", "--advertise-addr", swarm_manager_ip], check=True)

    # 5. Build the dsctl-server Docker image
    print("Building dsctl-server image...")
    subprocess.run(["docker", "build", "-t", "dsctl-server-test", "."], check=True)

    # 6. Deploy dsctl-server as a Swarm service
    print("Deploying dsctl-server as a service on the Swarm...")
    subprocess.run(
        ["docker", "-H", docker_host, "service", "create",
         "--name", "dsctl-server",
         "--publish", "8000:8000",
         "--mount", "type=bind,source=/var/run/docker.sock,destination=/var/run/docker.sock",
         "--env", "AUTH_METHOD=static",
         "--env", "STATIC_TOKEN_SECRET=dev-secret-token",
         "--env", "LOG_LEVEL=INFO",
         "dsctl-server-test"],
        check=True
    )

    # 7. Wait for dsctl-server service to be ready
    print("Waiting for dsctl-server service to be ready...")
    for _ in range(60): # Max 60 seconds wait
        try:
            response = requests.get("http://localhost:8000/ping")
            response.raise_for_status()
            if response.json() == {"ping": "pong"}:
                break
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError):
            time.sleep(1)
    else:
        raise RuntimeError("dsctl-server did not become ready in time.")
    print("dsctl-server is ready.")

    yield # Yield control to the tests

    # Teardown the environment
    print("\nTearing down E2E test environment...")
    subprocess.run(["docker", "compose", "-f", "docker-compose.test.yml", "down", "-v"], check=True)
