"""
Tests for TZD Reader Agent System
Tests the complete TZD Reader workflow including security, LLM integration, and API endpoints
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from io import BytesIO

# Test imports
try:
    from agents.tzd_reader.agent import tzd_reader, SecureAIAnalyzer
    from agents.tzd_reader.security import FileSecurityValidator, SecurityError
    from routers.tzd_router import router
    TZD_AVAILABLE = True
except ImportError:
    TZD_AVAILABLE = False

def create_test_pdf():
    """Create a simple test PDF file"""
    from fpdf import FPDF
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(40, 10, 'Техническое задание')
    pdf.ln(20)
    pdf.set_font('Arial', '', 12)
    pdf.cell(40, 10, 'Объект: Жилой дом')
    pdf.ln(10)
    pdf.cell(40, 10, 'Требования: Бетон B25, ГОСТ 26633')
    pdf.ln(10)
    pdf.cell(40, 10, 'Ограничения: Срок 6 месяцев')
    
    return pdf.output(dest='S').encode('latin-1')

def create_test_txt():
    """Create a simple test TXT file"""
    return """
Техническое задание на строительство

Объект строительства: Многоэтажный жилой дом
Требования:
- Бетон марки B25
- Арматура A500C
- Соответствие ČSN EN 206+A2

Ограничения:
- Бюджет: 50 млн крон
- Срок: 12 месяцев

Условия эксплуатации: Климатическая зона умеренная
Функции: Жилые помещения, коммерческие площади
""".encode('utf-8')

class TestFileSecurityValidator:
    """Test file security validation"""
    
    def test_valid_extensions(self):
        """Test validation of allowed file extensions"""
        validator = FileSecurityValidator()
        
        # Valid extensions
        assert validator.validate_file_extension("test.pdf") == True
        assert validator.validate_file_extension("test.docx") == True  
        assert validator.validate_file_extension("test.txt") == True
        
    def test_invalid_extensions(self):
        """Test rejection of disallowed extensions"""
        validator = FileSecurityValidator()
        
        # Invalid extensions should raise SecurityError
        with pytest.raises(SecurityError):
            validator.validate_file_extension("test.exe")
            
        with pytest.raises(SecurityError):
            validator.validate_file_extension("test.js")
            
    def test_file_size_validation(self):
        """Test file size validation"""
        validator = FileSecurityValidator()
        
        # Create test files
        with tempfile.NamedTemporaryFile(delete=False) as small_file:
            small_file.write(b"small content")
            small_file_path = small_file.name
            
        with tempfile.NamedTemporaryFile(delete=False) as large_file:
            large_file.write(b"x" * (11 * 1024 * 1024))  # 11MB - over limit
            large_file_path = large_file.name
            
        try:
            # Small file should pass
            assert validator.validate_file_size(small_file_path) == True
            
            # Large file should raise SecurityError
            with pytest.raises(SecurityError):
                validator.validate_file_size(large_file_path)
        finally:
            os.unlink(small_file_path)
            os.unlink(large_file_path)
            
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks"""
        validator = FileSecurityValidator()
        
        # Create base directory
        with tempfile.TemporaryDirectory() as base_dir:
            # Valid path within base directory
            valid_path = os.path.join(base_dir, "test.pdf")
            assert validator.validate_file_path(valid_path, base_dir) == True
            
            # Invalid paths with traversal attempts
            invalid_paths = [
                "../../../etc/passwd",
                os.path.join(base_dir, "../outside.pdf"),
                "/tmp/outside.pdf"
            ]
            
            for invalid_path in invalid_paths:
                with pytest.raises(SecurityError):
                    validator.validate_file_path(invalid_path, base_dir)

@pytest.mark.skipif(not TZD_AVAILABLE, reason="TZD Reader not available")
class TestTZDReaderAgent:
    """Test TZD Reader Agent functionality"""
    
    @patch('agents.tzd_reader.agent.SecureAIAnalyzer')
    def test_tzd_reader_basic_flow(self, mock_analyzer):
        """Test basic TZD reader flow"""
        # Mock analyzer response
        mock_instance = Mock()
        mock_instance.analyze_with_gpt.return_value = {
            "project_object": "Жилой дом",
            "requirements": ["Бетон B25"],
            "norms": ["ČSN EN 206+A2"],
            "constraints": ["6 месяцев"],
            "environment": "Умеренный климат",
            "functions": ["Жилье"]
        }
        mock_analyzer.return_value = mock_instance
        
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as test_file:
            test_file.write(create_test_txt())
            test_file_path = test_file.name
            
        try:
            result = tzd_reader([test_file_path], engine="gpt")
            
            # Verify basic structure
            assert isinstance(result, dict)
            assert "project_object" in result
            assert "requirements" in result
            assert "processing_metadata" in result
            
        finally:
            os.unlink(test_file_path)
            
    def test_empty_file_list_error(self):
        """Test error handling for empty file list"""
        with pytest.raises(ValueError, match="File list cannot be empty"):
            tzd_reader([])
            
    def test_too_many_files_error(self):
        """Test error handling for too many files"""
        many_files = [f"file_{i}.txt" for i in range(25)]
        with pytest.raises(ValueError, match="Too many files"):
            tzd_reader(many_files)

class TestSecureAIAnalyzer:
    """Test AI analyzer security and functionality"""
    
    def test_analyzer_basic_initialization(self):
        """Test basic analyzer initialization"""
        analyzer = SecureAIAnalyzer()
        # Just test that it initializes without errors
        assert analyzer is not None
        
    def test_json_extraction(self):
        """Test JSON extraction from AI responses"""
        analyzer = SecureAIAnalyzer()
        
        # Test cases for JSON extraction
        test_cases = [
            ('```json\n{"key": "value"}\n```', '{"key": "value"}'),
            ('Some text {"key": "value"} more text', '{"key": "value"}'),
            ('{"key": "value"}', '{"key": "value"}')
        ]
        
        for input_text, expected in test_cases:
            result = analyzer._extract_json_from_response(input_text)
            assert result == expected
            
    def test_empty_result_structure(self):
        """Test empty result structure matches expected format"""
        analyzer = SecureAIAnalyzer()
        empty_result = analyzer._get_empty_result()
        
        required_fields = [
            "project_object", "requirements", "norms", 
            "constraints", "environment", "functions"
        ]
        
        for field in required_fields:
            assert field in empty_result

@pytest.mark.skipif(not TZD_AVAILABLE, reason="TZD Reader not available")
class TestTZDRouter:
    """Test TZD Router API endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        from fastapi import FastAPI
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/api/v1/tzd/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "service" in data
        assert data["service"] == "TZD Reader"
        assert "status" in data
        assert "security" in data
        
    @patch('routers.tzd_router.tzd_reader')
    def test_analyze_endpoint_success(self, mock_tzd_reader):
        """Test successful analysis endpoint"""
        # Mock successful analysis
        mock_tzd_reader.return_value = {
            "project_object": "Test Project",
            "requirements": ["Test requirement"],
            "norms": ["Test norm"],
            "constraints": ["Test constraint"],
            "environment": "Test environment",
            "functions": ["Test function"],
            "processing_metadata": {"files": 1}
        }
        
        # Create test file data
        test_file = BytesIO(create_test_txt())
        
        response = self.client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("test.txt", test_file, "text/plain")},
            data={"ai_engine": "gpt"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "analysis_id" in data
        assert data["project_object"] == "Test Project"
        
    def test_analyze_endpoint_invalid_file(self):
        """Test analysis with invalid file extension"""
        test_file = BytesIO(b"malicious content")
        
        response = self.client.post(
            "/api/v1/tzd/analyze",
            files={"files": ("malware.exe", test_file, "application/octet-stream")},
            data={"ai_engine": "gpt"}
        )
        
        assert response.status_code == 400
        assert "Недопустимое расширение файла" in response.json()["detail"]
        
    def test_analyze_endpoint_large_file(self):
        """Test analysis with oversized file"""
        # Create 11MB file (over 10MB limit)
        large_content = b"x" * (11 * 1024 * 1024)
        test_file = BytesIO(large_content)
        
        response = self.client.post(
            "/api/v1/tzd/analyze", 
            files={"files": ("large.txt", test_file, "text/plain")},
            data={"ai_engine": "gpt"}
        )
        
        assert response.status_code == 400
        assert "превышает лимит 10MB" in response.json()["detail"]
        
    def test_analyze_endpoint_no_files(self):
        """Test analysis with no files"""
        response = self.client.post(
            "/api/v1/tzd/analyze",
            data={"ai_engine": "gpt"}
        )
        
        assert response.status_code == 422  # Validation error for missing files

@pytest.mark.integration
class TestTZDIntegration:
    """Integration tests for complete TZD workflow"""
    
    @pytest.mark.skipif(not TZD_AVAILABLE, reason="TZD Reader not available")
    def test_end_to_end_txt_analysis(self):
        """Test complete workflow with TXT file"""
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='wb') as test_file:
            test_file.write(create_test_txt())
            test_file_path = test_file.name
            
        try:
            # Mock the LLM service to avoid actual API calls
            with patch('agents.tzd_reader.agent.SecureAIAnalyzer') as mock_analyzer:
                mock_instance = Mock()
                mock_instance.use_new_service = False
                mock_instance.analyze_with_gpt.return_value = {
                    "project_object": "Многоэтажный жилой дом",
                    "requirements": ["Бетон марки B25", "Арматура A500C"],
                    "norms": ["ČSN EN 206+A2"],
                    "constraints": ["Бюджет: 50 млн крон", "Срок: 12 месяцев"],
                    "environment": "Климатическая зона умеренная",
                    "functions": ["Жилые помещения", "коммерческие площади"]
                }
                mock_analyzer.return_value = mock_instance
                
                result = tzd_reader([test_file_path], engine="gpt")
                
                # Verify result structure
                assert result["project_object"] == "Многоэтажный жилой дом"
                assert "Бетон марки B25" in result["requirements"]
                assert "ČSN EN 206+A2" in result["norms"]
                assert len(result["constraints"]) == 2
                
        finally:
            os.unlink(test_file_path)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])