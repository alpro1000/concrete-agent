"""
Contract tests for unified endpoint with multipart/form-data
These tests verify the new API contract with MIME validation and dual field names
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
import json


@pytest.fixture
def client():
    """Create test client with lifespan context"""
    with TestClient(app) as c:
        yield c


def test_unified_new_field_names(client):
    """Test that new field names (technical_files, quantities_files, drawings_files) work"""
    
    files = [
        ("technical_files", ("test.pdf", b"PDF content", "application/pdf")),
        ("quantities_files", ("test.xlsx", b"Excel content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("drawings_files", ("test.dwg", b"DWG content", "application/acad")),
    ]
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert data["status"] == "processing"
    assert "files" in data
    assert "technical_files" in data["files"]
    assert "quantities_files" in data["files"]
    assert "drawings_files" in data["files"]
    assert len(data["files"]["technical_files"]) == 1
    assert len(data["files"]["quantities_files"]) == 1
    assert len(data["files"]["drawings_files"]) == 1


def test_unified_old_field_names(client):
    """Test that old field names (project_documentation, budget_estimate, drawings) still work"""
    
    files = [
        ("project_documentation", ("test.pdf", b"PDF content", "application/pdf")),
        ("budget_estimate", ("test.xlsx", b"Excel content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("drawings", ("test.dwg", b"DWG content", "application/acad")),
    ]
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert data["status"] == "processing"
    assert "files" in data
    # Response uses new field names even when old names are used in request
    assert "technical_files" in data["files"]
    assert "quantities_files" in data["files"]
    assert "drawings_files" in data["files"]


def test_unified_rejects_invalid_mime_type(client):
    """Test that invalid MIME types are rejected with 400 error"""
    
    files = [
        ("technical_files", ("test.exe", b"exe content", "application/octet-stream"))
    ]
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
    
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_unified_rejects_large_files(client):
    """Test that files > 50MB are rejected with 400 error"""
    
    large_content = b"x" * (51 * 1024 * 1024)  # 51 MB
    files = [
        ("technical_files", ("test.txt", large_content, "text/plain"))
    ]
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
    
    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


def test_unified_technical_files_mime_types(client):
    """Test that technical_files accepts correct MIME types"""
    
    valid_mimes = [
        ("test.pdf", "application/pdf"),
        ("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("test.txt", "text/plain"),
    ]
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    for filename, mime in valid_mimes:
        files = [("technical_files", (filename, b"content", mime))]
        response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
        
        assert response.status_code == 200, f"Failed for {filename} with MIME {mime}"
        data = response.json()
        assert data["status"] == "processing"


def test_unified_quantities_files_mime_types(client):
    """Test that quantities_files accepts correct MIME types"""
    
    valid_mimes = [
        ("test.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("test.xls", "application/vnd.ms-excel"),
        ("test.pdf", "application/pdf"),
        ("test.xml", "application/xml"),
    ]
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    for filename, mime in valid_mimes:
        files = [("quantities_files", (filename, b"content", mime))]
        response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
        
        assert response.status_code == 200, f"Failed for {filename} with MIME {mime}"
        data = response.json()
        assert data["status"] == "processing"


def test_unified_drawings_files_mime_types(client):
    """Test that drawings_files accepts correct MIME types"""
    
    valid_mimes = [
        ("test.pdf", "application/pdf"),
        ("test.jpg", "image/jpeg"),
        ("test.png", "image/png"),
        ("test.gif", "image/gif"),
        ("test.dwg", "application/acad"),
    ]
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    for filename, mime in valid_mimes:
        files = [("drawings_files", (filename, b"content", mime))]
        response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
        
        assert response.status_code == 200, f"Failed for {filename} with MIME {mime}"
        data = response.json()
        assert data["status"] == "processing"


def test_unified_no_files_error(client):
    """Test that uploading no files returns 400 error"""
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    response = client.post("/api/v1/analysis/unified", headers=headers)
    
    assert response.status_code == 400
    assert "No files uploaded" in response.json()["detail"]


def test_unified_multiple_files_same_field(client):
    """Test uploading multiple files in the same field"""
    
    files = [
        ("technical_files", ("test1.pdf", b"content1", "application/pdf")),
        ("technical_files", ("test2.pdf", b"content2", "application/pdf")),
        ("technical_files", ("test3.txt", b"content3", "text/plain")),
    ]
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]["technical_files"]) == 3


def test_unified_response_structure(client):
    """Test that response has the expected structure"""
    
    files = [("technical_files", ("test.pdf", b"content", "application/pdf"))]
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check top-level structure
    assert "analysis_id" in data
    assert "status" in data
    assert data["status"] == "processing"
    assert "files" in data
    
    # Check files structure
    assert "technical_files" in data["files"]
    assert "quantities_files" in data["files"]
    assert "drawings_files" in data["files"]
    
    # Check file object structure
    if len(data["files"]["technical_files"]) > 0:
        file_obj = data["files"]["technical_files"][0]
        assert "filename" in file_obj
        assert "original_filename" in file_obj
        assert "size" in file_obj


def test_unified_authentication_with_valid_token(client):
    """Test that valid Bearer token results in user_id=1"""
    
    files = [("technical_files", ("test.txt", b"content", "text/plain"))]
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
    
    assert response.status_code == 200
    # File should be saved to storage/1/uploads/{analysis_id}/
    # (cannot directly check from response, but endpoint should work)


def test_unified_authentication_without_token(client):
    """Test that no token results in user_id=0"""
    
    files = [("technical_files", ("test.txt", b"content", "text/plain"))]
    
    response = client.post("/api/v1/analysis/unified", files=files)
    
    assert response.status_code == 200
    # File should be saved to storage/0/uploads/{analysis_id}/
    # (cannot directly check from response, but endpoint should work)


def test_unified_cross_field_mime_rejection(client):
    """Test that MIME types from one field are rejected in another field"""
    
    # Try to upload Excel file (quantities type) to technical_files field
    files = [
        ("technical_files", ("test.xlsx", b"content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
    ]
    
    headers = {"Authorization": "Bearer mock_jwt_token_12345"}
    
    response = client.post("/api/v1/analysis/unified", files=files, headers=headers)
    
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
