import subprocess
import time
import requests
import os
import json

def start_environment():
    print("\nSetting up E2E test environment for manual browsing...")

    # 1. Bring up the DinD Swarm manager
    print("Bringing up DinD Swarm manager...")
    subprocess.run(["docker", "compose", "-f", "docker-compose.test.yml", "up", "-d"], check=True)

    # 2. Get the IP address of the swarm-manager container
    print("Getting Swarm Manager IP...")
    swarm_manager_container_id = ""
    for _ in range(60): # Wait for container to be running
        result = subprocess.run(
            "docker ps -q --filter \"name=docker-swarm-ctl-swarm-manager-1\"",
            capture_output=True, text=True, shell=True
        )
        if result.stdout.strip():
            swarm_manager_container_id = result.stdout.strip()
            break
        time.sleep(1)
    else:
        raise RuntimeError("swarm-manager container did not start in time.")

    print(f"Swarm Manager Container ID: {swarm_manager_container_id}")

    # Get the Docker Compose project name
    project_name_result = subprocess.run(
        "docker compose -f docker-compose.test.yml config --format json | jq -r .name",
        capture_output=True, text=True, check=True, shell=True
    )
    project_name = project_name_result.stdout.strip()
    full_network_name = f"{project_name}_test_net"
    print(f"Full network name: {full_network_name}")

    result = subprocess.run(
        f"docker inspect {swarm_manager_container_id}",
        capture_output=True, text=True, check=True, shell=True
    )
    inspect_output = json.loads(result.stdout.strip())[0]
    swarm_manager_ip = inspect_output["NetworkSettings"]["Networks"][full_network_name]["IPAddress"]
    print(f"Swarm Manager IP: {swarm_manager_ip}")

    # 3. Wait for the DinD daemon to be ready
    print("Waiting for Swarm Manager Docker daemon to be ready...")
    docker_host = f"tcp://{swarm_manager_ip}:2375"
    for _ in range(120): # Increased timeout to 120 seconds
        try:
            subprocess.run(["docker", "-H", docker_host, "info"], check=True, capture_output=True)
            break
        except subprocess.CalledProcessError as e:
            print(f"DinD daemon not ready yet: {e.stderr.strip()}")
            time.sleep(1)
    else:
        raise RuntimeError("DinD Docker daemon did not become ready in time.")
    print("Swarm Manager Docker daemon is ready.")

    # Ensure the DinD node is not already part of a swarm
    print("Ensuring DinD node is not part of a swarm...")
    subprocess.run(["docker", "-H", docker_host, "swarm", "leave", "--force"], check=False, capture_output=True)

    # 4. Initialize the Swarm on the DinD manager
    print("Initializing Swarm on manager...")
    subprocess.run(["docker", "-H", docker_host, "swarm", "init", "--advertise-addr", swarm_manager_ip], check=True)

    # Get the GID of docker.sock inside the DinD container
    print("Getting docker.sock GID from DinD...")
    docker_sock_gid_result = subprocess.run(
        ["docker", "-H", docker_host, "run", "--rm", "-v", "/var/run/docker.sock:/var/run/docker.sock", "alpine", "stat", "-c", "%g", "/var/run/docker.sock"],
        capture_output=True, text=True, check=True
    )
    docker_sock_gid = docker_sock_gid_result.stdout.strip()
    print(f"Docker.sock GID in DinD: {docker_sock_gid}")

    # 5. Build the dsctl-server Docker image on the DinD daemon
    print("Building dsctl-server image on DinD daemon...")
    subprocess.run(["docker", "-H", docker_host, "build", "-t", "dsctl-server-test", "."], check=True)

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
         "--user", f"1000:{docker_sock_gid}", # Use dynamic GID
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

    print("\nE2E test environment is running. You can now browse the API:")
    print("  Swagger UI: http://localhost:8000/docs")
    print("  ReDoc:      http://localhost:8000/redoc")
    print("\nPress Enter to tear down the environment...")
    input()

    # Teardown the environment
    print("\nTearing down E2E test environment...")
    subprocess.run(["docker", "compose", "-f", "docker-compose.test.yml", "down", "-v"], check=True)

if __name__ == "__main__":
    try:
        start_environment()
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Attempting to tear down any running test environment...")
        subprocess.run(["docker", "compose", "-f", "docker-compose.test.yml", "down", "-v"], check=False)
