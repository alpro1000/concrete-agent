"""
API endpoint tests for Concrete Agent system.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["name"] == "Concrete Agent API"


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data


def test_status_endpoint():
    """Test system status endpoint."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "agents" in data
    assert "components" in data
    assert isinstance(data["agents"], list)


def test_list_agents_endpoint():
    """Test listing available agents."""
    response = client.get("/api/agents/agents")
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)
    # Agents list may be empty if not discovered yet in test environment
    # In production, agents are discovered on startup


def test_metrics_endpoint():
    """Test metrics endpoint."""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "executions" in data
    assert "agents" in data


def test_config_endpoint():
    """Test configuration endpoint."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "environment" in data
    assert "llm_primary_provider" in data


def test_openapi_docs():
    """Test OpenAPI documentation is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data
