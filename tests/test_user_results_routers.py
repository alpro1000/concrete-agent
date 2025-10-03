"""
Tests for user_router and results_router endpoints
These tests verify the API contract for user and results endpoints
"""

import pytest

# Check if FastAPI is available
try:
    from fastapi.testclient import TestClient
    from app.main import app
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    TestClient = None
    app = None


@pytest.fixture
def client():
    """Create test client with lifespan context"""
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not installed")
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_user_login_endpoint(client):
    """Test GET /api/v1/user/login endpoint"""
    response = client.get("/api/v1/user/login")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "user_id" in data
    assert "token" in data
    assert "username" in data


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_user_history_endpoint(client):
    """Test GET /api/v1/user/history endpoint"""
    response = client.get("/api/v1/user/history")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "history" in data
    assert "total" in data
    assert isinstance(data["history"], list)


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_delete_analysis_endpoint(client):
    """Test DELETE /api/v1/user/history/{id} endpoint"""
    test_id = "test-analysis-123"
    response = client.delete(f"/api/v1/user/history/{test_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_get_results_endpoint(client):
    """Test GET /api/v1/results/{id} endpoint"""
    test_id = "test-analysis-123"
    response = client.get(f"/api/v1/results/{test_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert "status" in data
    assert "files" in data
    assert "summary" in data


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
@pytest.mark.parametrize("format", ["pdf", "docx", "xlsx"])
def test_export_results_endpoint(client, format):
    """Test GET /api/v1/results/{id}/export endpoint with different formats"""
    test_id = "test-analysis-123"
    response = client.get(f"/api/v1/results/{test_id}/export?format={format}")
    
    assert response.status_code == 200
    
    # Should return either file content or JSON status
    content_type = response.headers.get("content-type", "")
    
    if "application/json" in content_type:
        # JSON response (not yet implemented fully)
        data = response.json()
        assert "status" in data
        assert "format" in data
        assert data["format"] == format
    else:
        # Binary file response
        assert len(response.content) > 0


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_export_invalid_format(client):
    """Test export with invalid format returns error"""
    test_id = "test-analysis-123"
    response = client.get(f"/api/v1/results/{test_id}/export?format=invalid")
    
    # FastAPI should return 422 for invalid enum value
    assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
