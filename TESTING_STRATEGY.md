# dsctl Testing Strategy

This document outlines the testing strategy for the `dsctl` project, encompassing both the `dsctl-server` (FastAPI application) and the `dsctl` CLI client. The goal is to ensure the reliability, correctness, and maintainability of the application through a layered testing approach.

## 1. Unit Tests

**Goal:** To test individual functions, methods, or classes in isolation, verifying their internal logic and behavior without external dependencies.

**Scope:**
*   Individual components of the `dsctl-server` (e.g., authentication strategies, utility functions, data models).
*   Individual functions within the `dsctl` CLI client (e.g., configuration parsing, argument handling).

**Approach:**
*   **Mocking:** External dependencies, such as the Docker API (`docker-py`), external services, or file system interactions, will be mocked using `unittest.mock` or `pytest-mock`.
*   **Focus:** Verify input validation, data transformations, error handling, and the correct construction of calls to mocked dependencies.

**Tools:**
*   `pytest` (testing framework)
*   `pytest-mock` (for easy mocking)

**Location:** `tests/unit/`

## 2. Integration Tests (API Server)

**Goal:** To test the interaction between different components of the `dsctl-server`, ensuring they work together as expected. This primarily focuses on the API endpoints.

**Scope:**
*   API endpoint handlers, including their interaction with authentication, configuration, and (mocked) Docker client logic.
*   Middleware and dependency injection.

**Approach:**
*   **FastAPI `TestClient`:** Use FastAPI's `TestClient` to simulate HTTP requests to the API endpoints. This allows testing the full request-response cycle of the API.
*   **Mocking `docker-py`:** While testing the API layer, interactions with the actual Docker daemon will still be mocked. This keeps tests fast and independent of a live Docker environment.
*   **Focus:** Verify correct routing, request parsing, response formatting, authentication enforcement, and the proper invocation of underlying (mocked) business logic.

**Tools:**
*   `pytest`
*   `fastapi.testclient.TestClient`
*   `pytest-mock`

**Location:** `tests/integration/api/`

## 3. End-to-End (E2E) Tests

**Goal:** To test the entire system, from the `dsctl` CLI client through the `dsctl-server` to a *real* Docker Swarm environment. This is critical for verifying Swarm-specific functionalities and the overall system behavior.

**Scope:**
*   Full `dsctl` CLI command execution.
*   `dsctl-server` processing requests and interacting with a live Docker Swarm.
*   Verification of changes in the Docker Swarm state.

**Approach:**
*   **Ephemeral Docker Swarm (Docker-in-Docker - DinD):**
    *   For both local development and CI/CD (GitHub Actions), an ephemeral Docker Swarm will be created using `docker:dind` containers.
    *   A dedicated `docker-compose.test.yml` will orchestrate the DinD daemon(s) and the `dsctl-server` instance, configured to connect to the DinD daemon.
    *   A setup script or `pytest` fixture will initialize the Swarm (e.g., `docker swarm init`, `docker swarm join`) within the DinD environment before tests run.
*   **CLI Execution:** The `dsctl` CLI client will be executed against the `dsctl-server` running within the ephemeral Swarm.
*   **Direct Swarm Verification:** After CLI commands are executed, `docker-py` (from the test runner, not the `dsctl-server`) will connect directly to the DinD Swarm's Docker daemon to inspect its state and assert that the CLI commands had the intended effect (e.g., a service was created, a secret was updated).
*   **Teardown:** The ephemeral Docker Swarm environment will be completely torn down after each test run or test suite to ensure isolation and clean state.

**Tools:**
*   `pytest`
*   `docker-compose` (for orchestrating the test environment)
*   `docker-py` (for programmatic interaction with the DinD Swarm for assertions)
*   `docker:dind` (Docker image for creating ephemeral Docker daemons)

**Location:** `tests/e2e/`

## General Principles

*   **Fast Feedback:** Prioritize unit and integration tests for quick feedback during development.
*   **Comprehensive Coverage:** Aim for high test coverage across all layers of the application.
*   **Reproducibility:** Ensure tests are deterministic and produce the same results every time.
*   **Maintainability:** Write clear, concise, and well-structured tests that are easy to understand and update.
*   **CI/CD Integration:** All tests will be integrated into the GitHub Actions workflow to ensure continuous validation of the codebase.
