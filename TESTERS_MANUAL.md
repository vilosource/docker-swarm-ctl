# dsctl Testers Manual

This manual provides instructions for setting up and running tests for the `dsctl` project. It covers unit, integration, and end-to-end (E2E) testing, with a focus on interacting with the simulated Docker Swarm environment.

## Prerequisites

Before running tests, ensure you have the following installed:

*   **Docker Desktop** (or Docker Engine and Docker Compose) - Required for running the `dsctl-server` and for E2E testing.
*   **Python 3.12+**
*   **Poetry** (Python package manager)

## Project Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/vilosource/docker-swarm-ctl.git
    cd docker-swarm-ctl
    ```

2.  **Install Python dependencies:**
    ```bash
    poetry install
    ```

3.  **Prepare local CLI configuration:**
    The CLI expects a configuration file at `~/.dsctl/config.yml`. A sample is provided in `sample-config.yml`.
    ```bash
    mkdir -p ~/.dsctl
    cp sample-config.yml ~/.dsctl/config.yml
    ```

## Running Tests

All tests are run using `pytest`.

### Running All Tests

To run all unit, integration, and E2E tests:

```bash
poetry run pytest
```

### Running Specific Test Suites

*   **Unit Tests:**
    ```bash
    poetry run pytest tests/unit/
    ```

*   **Integration Tests (API Server):**
    ```bash
    poetry run pytest tests/integration/api/
    ```

*   **End-to-End (E2E) Tests:**
    These tests will automatically set up and tear down an ephemeral Docker Swarm environment using Docker-in-Docker (DinD).
    ```bash
    poetry run pytest tests/e2e/
    ```

    **Note:** The first time you run E2E tests, Docker will need to download the `docker:dind` image and build the `dsctl-server-test` image, which may take some time.

## Interacting with the E2E Test Environment

When running E2E tests, an isolated Docker Swarm is created. You can interact with this environment for debugging or manual verification.

### Accessing the `dsctl-server` API (Swagger UI / ReDoc)

While the E2E tests are running, the `dsctl-server` API will be accessible on your local machine:

*   **Swagger UI:** `http://localhost:8000/docs`
*   **ReDoc:** `http://localhost:8000/redoc`

You can use these interfaces to manually send requests to the API and observe responses. For protected endpoints, use the `dev-secret-token` as the Bearer token.

### Inspecting the Simulated Docker Swarm

To inspect the Docker Swarm running within the DinD container, you can use standard Docker commands. You'll need to identify the `swarm-manager` container first.

1.  **List running containers:**
    ```bash
    docker ps
    ```
    Look for a container named `docker-swarm-ctl-swarm-manager-1` (or similar, depending on the compose project name).

2.  **Get the IP address of the `swarm-manager`:**
    ```bash
    docker inspect -f '{{.NetworkSettings.Networks.test_net.IPAddress}}' <swarm-manager-container-id-or-name>
    ```
    Let's say the IP is `172.18.0.2`.

3.  **Interact with the DinD Docker daemon:**
    You can now use `docker -H tcp://<swarm-manager-ip>:2375` to run Docker commands against the simulated Swarm.

    *   **List Swarm nodes:**
        ```bash
        docker -H tcp://172.18.0.2:2375 node ls
        ```

    *   **List Swarm services:**
        ```bash
        docker -H tcp://172.18.0.2:2375 service ls
        ```

    *   **View `dsctl-server` service logs:**
        ```bash
        docker -H tcp://172.18.0.2:2375 service logs dsctl-server
        ```

### Debugging E2E Test Failures

If an E2E test fails, the `setup_e2e_environment` fixture will automatically tear down the environment. To debug, you might want to temporarily modify `tests/e2e/conftest.py` to comment out the `subprocess.run(["docker", "compose", "-f", "docker-compose.test.yml", "down", "-v"], check=True)` line in the `teardown` section. This will leave the environment running after a test failure, allowing for manual inspection.

Remember to revert this change after debugging to ensure clean test runs.
