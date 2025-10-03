"""
Contract tests for upload endpoint
These tests verify the API contract between frontend and backend
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client with lifespan context"""
    with TestClient(app) as c:
        yield c


def test_upload_accepts_three_fields(client):
    """Contract test: /api/v1/analysis/unified accepts three fields with correct names"""
    
    # Create test files with the exact field names used by frontend
    files = [
        ("project_documentation", ("test.pdf", b"PDF content", "application/pdf")),
        ("budget_estimate", ("test.xlsx", b"Excel content", "application/vnd.ms-excel")),
        ("drawings", ("test.dwg", b"DWG content", "application/acad")),
    ]
    
    response = client.post("/api/v1/analysis/unified", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["success", "partial"]
    assert data["summary"]["total"] == 3
    assert "files" in data
    assert len(data["files"]) == 3
    
    # Verify categories
    categories = [f["category"] for f in data["files"]]
    assert "project_documentation" in categories
    assert "budget_estimate" in categories
    assert "drawings" in categories


def test_upload_rejects_invalid_extension(client):
    """Test that invalid file types are rejected"""
    
    files = [("project_documentation", ("test.exe", b"exe", "application/x-msdownload"))]
    
    response = client.post("/api/v1/analysis/unified", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["failed"] == 1
    assert "Invalid extension" in data["files"][0]["error"]


def test_upload_rejects_large_files(client):
    """Test that files > 50MB are rejected"""
    
    large_content = b"x" * (51 * 1024 * 1024)  # 51 MB
    files = [("project_documentation", ("test.pdf", large_content, "application/pdf"))]
    
    response = client.post("/api/v1/analysis/unified", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["failed"] == 1
    assert "too large" in data["files"][0]["error"].lower()


def test_upload_accepts_valid_extensions(client):
    """Test that all valid extensions are accepted"""
    
    valid_extensions = [
        ('.pdf', 'application/pdf'),
        ('.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        ('.txt', 'text/plain'),
        ('.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
        ('.xls', 'application/vnd.ms-excel'),
        ('.xml', 'application/xml'),
    ]
    
    for ext, mime in valid_extensions:
        files = [("project_documentation", (f"test{ext}", b"content", mime))]
        response = client.post("/api/v1/analysis/unified", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["successful"] >= 0, f"Failed for extension {ext}"


def test_upload_no_files_returns_error(client):
    """Test that uploading no files returns an error"""
    
    response = client.post("/api/v1/analysis/unified")
    
    assert response.status_code == 400
    assert "No files uploaded" in response.json()["detail"]


def test_upload_multiple_files_same_category(client):
    """Test uploading multiple files in the same category"""
    
    files = [
        ("project_documentation", ("test1.pdf", b"content1", "application/pdf")),
        ("project_documentation", ("test2.pdf", b"content2", "application/pdf")),
        ("project_documentation", ("test3.pdf", b"content3", "application/pdf")),
    ]
    
    response = client.post("/api/v1/analysis/unified", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total"] == 3
    
    # All should be in project_documentation category
    categories = [f["category"] for f in data["files"]]
    assert all(cat == "project_documentation" for cat in categories)


def test_upload_response_structure(client):
    """Test that response has the expected structure"""
    
    files = [("project_documentation", ("test.pdf", b"content", "application/pdf"))]
    
    response = client.post("/api/v1/analysis/unified", files=files)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check top-level structure
    assert "status" in data
    assert "message" in data
    assert "files" in data
    assert "summary" in data
    
    # Check summary structure
    assert "total" in data["summary"]
    assert "successful" in data["summary"]
    assert "failed" in data["summary"]
    
    # Check file structure
    file_obj = data["files"][0]
    assert "name" in file_obj
    assert "type" in file_obj
    assert "category" in file_obj
    assert "success" in file_obj
    assert "error" in file_obj


def test_upload_mixed_valid_invalid_files(client):
    """Test uploading a mix of valid and invalid files"""
    
    files = [
        ("project_documentation", ("valid.pdf", b"content", "application/pdf")),
        ("project_documentation", ("invalid.exe", b"content", "application/x-msdownload")),
        ("budget_estimate", ("valid.xlsx", b"content", "application/vnd.ms-excel")),
    ]
    
    response = client.post("/api/v1/analysis/unified", files=files)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have partial success
    assert data["status"] == "partial"
    assert data["summary"]["total"] == 3
    assert data["summary"]["successful"] >= 1
    assert data["summary"]["failed"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
