import pytest
import requests

def test_e2e_ping(setup_e2e_environment):
    # The setup_e2e_environment fixture ensures the server is running
    # and the Swarm is initialized.
    response = requests.get("http://localhost:8000/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}

def test_e2e_version(setup_e2e_environment):
    response = requests.get("http://localhost:8000/version")
    assert response.status_code == 200
    assert "server_version" in response.json()
    assert "docker_version" in response.json()

def test_e2e_cluster_info(setup_e2e_environment):
    headers = {"Authorization": "Bearer dev-secret-token"}
    response = requests.get("http://localhost:8000/cluster/info", headers=headers)
    assert response.status_code == 200
    assert "ID" in response.json() # Check for a key expected in Docker info
