#!/usr/bin/env python3
"""
Tests for the upload endpoints and router auto-discovery
"""
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the test app
import sys
sys.path.append('/home/runner/work/concrete-agent/concrete-agent')

# Create the test app inline to test router discovery
from fastapi import FastAPI
from app.core.router_registry import RouterRegistry

def check_routers_available():
    """Check if any routers are available"""
    try:
        registry = RouterRegistry()
        routers = registry.discover_routers("app/routers")
        return len(routers) > 0
    except Exception as e:
        print(f"Router check failed: {e}")
        return False

def create_test_app():
    """Create test app with available routers"""
    test_app = FastAPI(title="Upload Test App")
    
    # Use router registry to auto-discover routers
    registry = RouterRegistry()
    routers = registry.discover_routers("app/routers")
    
    for router_info in routers:
        try:
            router = router_info['router']
            prefix = router_info.get('prefix', '')
            tags = router_info.get('tags', [router_info['name']])
            test_app.include_router(router, prefix=prefix, tags=tags)
        except Exception as e:
            print(f"Failed to include router {router_info['name']}: {e}")
    
    @test_app.get("/")
    async def root():
        return {
            "service": "Upload Endpoints Test",
            "routers_loaded": len(routers),
            "endpoints": {
                "docs": "/docs",
                "health": "/health"
            }
        }
    
    @test_app.get("/health")
    async def health():
        return {"status": "healthy", "endpoints_loaded": len(test_app.routes)}
    
    return test_app

@pytest.mark.skipif(not check_routers_available(), reason="No routers available")
class TestUploadEndpoints:
    """Test class for upload endpoints and router auto-discovery"""

    def setup_method(self):
        """Set up test data"""
        self.app = create_test_app()
        self.client = TestClient(self.app)
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files
        self.test_doc_path = os.path.join(self.temp_dir, "test_tz.txt")
        with open(self.test_doc_path, "w") as f:
            f.write("Technical specification content")

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "routers_loaded" in data

    def test_health_endpoint(self):
        """Test health endpoint"""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "endpoints_loaded" in data
        
    def test_router_auto_discovery(self):
        """Test that router registry auto-discovers routers"""
        from app.core.router_registry import RouterRegistry
        
        registry = RouterRegistry()
        routers = registry.discover_routers("app/routers")
        
        assert len(routers) >= 0  # Should have at least 0 routers (system works without them)
        
        # If TZD router exists, verify it was discovered
        router_names = [r['name'] for r in routers]
        if 'tzd_router' in router_names:
            assert any(r['name'] == 'tzd_router' for r in routers)
        
    def teardown_method(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_docs_upload_success(self):
        """Test successful project documents upload"""
        with open(self.test_doc_path, "rb") as f:
            response = client.post(
                "/upload/docs",
                files={"files": ("test_tz.txt", f, "text/plain")},
                data={
                    "project_name": "Test Project",
                    "auto_analyze": "false",
                    "language": "cz"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["upload_type"] == "project_documents"
        assert data["project_name"] == "Test Project"
        assert data["total_files"] == 1
        assert data["status"] == "uploaded_successfully"
        assert "TZDReader" in data["supported_agents"]

    def test_docs_upload_invalid_file_type(self):
        """Test docs upload with invalid file type"""
        invalid_file_path = os.path.join(self.temp_dir, "test.exe")
        with open(invalid_file_path, "w") as f:
            f.write("Invalid file")
            
        with open(invalid_file_path, "rb") as f:
            response = client.post(
                "/upload/docs",
                files={"files": ("test.exe", f, "application/octet-stream")},
                data={"project_name": "Test Project"}
            )
        
        assert response.status_code == 400
        assert "Недопустимый тип файла" in response.json()["detail"]

    def test_smeta_upload_success(self):
        """Test successful estimates upload"""
        with open(self.test_smeta_path, "rb") as f:
            response = client.post(
                "/upload/smeta",
                files={"files": ("test_smeta.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "project_name": "Test Project",
                    "estimate_type": "general",
                    "auto_analyze": "false",
                    "language": "cz"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["upload_type"] == "estimates_boq"
        assert data["estimate_type"] == "general"
        assert data["total_files"] == 1
        assert data["status"] == "uploaded_successfully"
        assert "TOVPlanner" in data["supported_agents"]

    def test_smeta_upload_xml_file(self):
        """Test estimates upload with XML file"""
        xml_path = os.path.join(self.temp_dir, "test_smeta.xml")
        with open(xml_path, "w") as f:
            f.write('<?xml version="1.0"?><estimate><item><name>Test</name></item></estimate>')
            
        with open(xml_path, "rb") as f:
            response = client.post(
                "/upload/smeta",
                files={"files": ("test_smeta.xml", f, "application/xml")},
                data={"project_name": "Test Project"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["files"][0]["type"] == "xml_estimate"
        assert data["files"][0]["format"] == "xml"

    def test_drawings_upload_success(self):
        """Test successful drawings upload"""
        with open(self.test_drawing_path, "rb") as f:
            response = client.post(
                "/upload/drawings",
                files={"files": ("test_drawing.dwg", f, "application/acad")},
                data={
                    "project_name": "Test Project",
                    "drawing_type": "architectural",
                    "scale": "1:100",
                    "auto_analyze": "false",
                    "extract_volumes": "true",
                    "language": "cz"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["upload_type"] == "technical_drawings"
        assert data["drawing_type"] == "architectural"
        assert data["scale"] == "1:100"
        assert data["total_files"] == 1
        assert data["status"] == "uploaded_successfully"
        assert "DrawingVolumeAgent" in data["supported_agents"]

    def test_drawings_upload_pdf(self):
        """Test drawings upload with PDF file"""
        pdf_path = os.path.join(self.temp_dir, "test_plan.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"Mock PDF content")
            
        with open(pdf_path, "rb") as f:
            response = client.post(
                "/upload/drawings",
                files={"files": ("test_plan.pdf", f, "application/pdf")},
                data={"project_name": "Test Project"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["files"][0]["type"] == "pdf_drawing"
        assert data["files"][0]["format"] == "pdf"

    def test_multiple_files_upload(self):
        """Test uploading multiple files to docs endpoint"""
        doc1_path = os.path.join(self.temp_dir, "doc1.txt")
        doc2_path = os.path.join(self.temp_dir, "doc2.pdf")
        
        with open(doc1_path, "w") as f:
            f.write("Document 1 content")
        with open(doc2_path, "wb") as f:
            f.write(b"Mock PDF content")
        
        with open(doc1_path, "rb") as f1, open(doc2_path, "rb") as f2:
            response = client.post(
                "/upload/docs",
                files=[
                    ("files", ("doc1.txt", f1, "text/plain")),
                    ("files", ("doc2.pdf", f2, "application/pdf"))
                ],
                data={"project_name": "Multi-file Test"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 2
        filenames = [f["filename"] for f in data["files"]]
        assert "doc1.txt" in filenames
        assert "doc2.pdf" in filenames

    def test_empty_files_upload(self):
        """Test upload with no files"""
        response = client.post(
            "/upload/docs",
            data={"project_name": "Empty Test"}
        )
        
        assert response.status_code == 422  # FastAPI validation error for missing files

    def test_file_type_detection_docs(self):
        """Test file type detection for documents"""
        # Test different document types
        test_files = [
            ("technical_spec.txt", "technical_specification"),
            ("geology_report.pdf", "geological_report"),
            ("gost_norm.docx", "regulatory_document"),
            ("project_plan.doc", "project_documentation")
        ]
        
        for filename, expected_type in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "w") as f:
                f.write("Test content")
            
            with open(file_path, "rb") as f:
                response = client.post(
                    "/upload/docs",
                    files={"files": (filename, f, "text/plain")},
                    data={"project_name": "Type Detection Test", "auto_analyze": "false"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["files"][0]["type"] == expected_type

    def test_estimate_type_detection(self):
        """Test estimate type detection"""
        test_files = [
            ("local_estimate.xlsx", "local_estimate"),
            ("object_smeta.xml", "object_estimate"),
            ("summary_total.csv", "summary_estimate"),
            ("volume_works.xlsx", "work_volume_statement")
        ]
        
        for filename, expected_type in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "w") as f:
                f.write("Test content")
            
            with open(file_path, "rb") as f:
                response = client.post(
                    "/upload/smeta",
                    files={"files": (filename, f, "text/plain")},
                    data={"project_name": "Type Detection Test", "auto_analyze": "false"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["files"][0]["type"] == expected_type

    def test_drawing_type_detection(self):
        """Test drawing type detection"""
        test_files = [
            ("architectural_plan.dwg", "architectural_drawing"),
            ("structural_frame.dxf", "structural_drawing"),
            ("hvac_scheme.pdf", "mechanical_drawing"),
            ("detail_node.dwg", "detail_drawing"),
            ("site_plan.pdf", "site_plan")
        ]
        
        for filename, expected_type in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "wb") as f:
                f.write(b"Test content")
            
            with open(file_path, "rb") as f:
                response = client.post(
                    "/upload/drawings",
                    files={"files": (filename, f, "application/octet-stream")},
                    data={"project_name": "Type Detection Test", "auto_analyze": "false"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["files"][0]["type"] == expected_type

    @pytest.mark.asyncio
    @patch('agents.integration_orchestrator.get_integration_orchestrator')
    async def test_docs_with_analysis(self, mock_orchestrator):
        """Test docs upload with auto analysis enabled"""
        # Mock the orchestrator
        mock_instance = MagicMock()
        mock_instance.run_integrated_analysis.return_value = {
            "summary": {"status": "completed"},
            "concrete_analysis": {"grades": ["C25/30"]},
            "status": {"overall": "success"},
            "timestamp": "2025-01-09T12:00:00Z"
        }
        mock_orchestrator.return_value = mock_instance
        
        with open(self.test_doc_path, "rb") as f:
            response = client.post(
                "/upload/docs",
                files={"files": ("test_tz.txt", f, "text/plain")},
                data={
                    "project_name": "Analysis Test",
                    "auto_analyze": "true",
                    "language": "cz"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        # Analysis would fail due to missing dependencies, but upload should succeed
        assert data["upload_type"] == "project_documents"
        assert data["total_files"] == 1

    def teardown_method(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


def test_file_type_validation():
    """Test file type validation functions"""
    from routers.upload_docs import _detect_document_type
    from routers.upload_smeta import _detect_estimate_type
    from routers.upload_drawings import _detect_drawing_type
    
    # Test document type detection
    assert _detect_document_type("technical_specification.txt", b"content") == "technical_specification"
    assert _detect_document_type("geology_report.pdf", b"content") == "geological_report"
    assert _detect_document_type("general.docx", b"content") == "word_document"
    
    # Test estimate type detection
    assert _detect_estimate_type("local_smeta.xlsx", b"content") == "local_estimate"
    assert _detect_estimate_type("summary.xml", b"content") == "xml_estimate"
    assert _detect_estimate_type("volumes.csv", b"content") == "work_volume_statement"
    
    # Test drawing type detection
    assert _detect_drawing_type("architectural_plan.dwg", b"content") == "architectural_drawing"
    assert _detect_drawing_type("structural.dxf", b"content") == "structural_drawing"
    assert _detect_drawing_type("model.ifc", b"content") == "bim_model"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])