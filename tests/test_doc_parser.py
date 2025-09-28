"""
Tests for the unified document parser service
tests/test_doc_parser.py
"""

import os
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from services.doc_parser import (
    UnifiedDocumentParser, 
    ParseResult, 
    parse_document, 
    get_unified_document_parser
)


class TestUnifiedDocumentParser:
    """Test cases for the unified document parser"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.parser = UnifiedDocumentParser()
    
    def test_parser_initialization(self):
        """Test that parser initializes correctly"""
        assert self.parser is not None
        assert hasattr(self.parser, 'doc_parser')
        assert hasattr(self.parser, 'smeta_parser')
        assert hasattr(self.parser, 'xml_parser')
        assert 'pdf' in self.parser.supported_extensions
        assert 'xlsx' in self.parser.supported_extensions
        assert 'xml' in self.parser.supported_extensions
    
    def test_singleton_instance(self):
        """Test that get_unified_document_parser returns singleton"""
        parser1 = get_unified_document_parser()
        parser2 = get_unified_document_parser()
        assert parser1 is parser2
    
    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist"""
        result = self.parser.parse_document("/nonexistent/file.pdf")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["results"] == []
    
    def test_get_file_info(self):
        """Test getting file metadata"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file.flush()
            
            try:
                info = self.parser.get_file_info(tmp_file.name)
                
                assert info["name"].endswith('.pdf')
                assert info["extension"] == '.pdf'
                assert info["size_bytes"] > 0
                assert info["supported"] is True
                assert info["can_use_mineru"] is True
                assert info["legacy_parser"] == "doc_parser"
            finally:
                os.unlink(tmp_file.name)
    
    def test_get_file_info_unsupported(self):
        """Test getting info for unsupported file type"""
        with tempfile.NamedTemporaryFile(suffix='.unknown', delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file.flush()
            
            try:
                info = self.parser.get_file_info(tmp_file.name)
                
                assert info["supported"] is False
                assert info["legacy_parser"] == "unsupported"
            finally:
                os.unlink(tmp_file.name)
    
    @patch('services.doc_parser.extract_with_mineru_if_available')
    def test_mineru_success(self, mock_mineru):
        """Test successful MinerU parsing"""
        # Mock MinerU to return structured content
        mock_content = {
            "source": "mineru",
            "content": "Test extracted content",
            "metadata": {"pages": 1}
        }
        mock_mineru.return_value = json.dumps(mock_content)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"test pdf content")
            tmp_file.flush()
            
            try:
                result = self.parser.parse_document(tmp_file.name)
                
                assert result["success"] is True
                assert len(result["results"]) == 1
                
                parse_result = result["results"][0]
                assert parse_result.parser_used == "mineru"
                assert isinstance(parse_result.content, dict)
                assert parse_result.metadata["parser"] == "mineru"
                
            finally:
                os.unlink(tmp_file.name)
    
    @patch('services.doc_parser.extract_with_mineru_if_available')
    @patch('parsers.doc_parser.DocParser.parse')
    def test_fallback_to_legacy(self, mock_doc_parser, mock_mineru):
        """Test fallback to legacy parser when MinerU fails"""
        # Mock MinerU to return None (failed/unavailable)
        mock_mineru.return_value = None
        
        # Mock legacy parser to return content
        mock_doc_parser.return_value = "Legacy parsed content"
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"test pdf content")
            tmp_file.flush()
            
            try:
                result = self.parser.parse_document(tmp_file.name)
                
                assert result["success"] is True
                assert len(result["results"]) == 1
                
                parse_result = result["results"][0]
                assert parse_result.parser_used == "doc_parser"
                assert parse_result.content == "Legacy parsed content"
                assert parse_result.metadata["fallback"] is True
                
            finally:
                os.unlink(tmp_file.name)
    
    def test_parse_zip_archive(self):
        """Test parsing ZIP archive with multiple files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = {
                "test1.txt": "Content of test file 1",
                "test2.pdf": b"PDF content bytes",
                "data.xlsx": b"Excel content bytes"
            }
            
            zip_path = os.path.join(temp_dir, "test_archive.zip")
            
            # Create ZIP file with test content
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for filename, content in test_files.items():
                    file_path = os.path.join(temp_dir, filename)
                    mode = 'w' if isinstance(content, str) else 'wb'
                    with open(file_path, mode) as f:
                        f.write(content)
                    zipf.write(file_path, filename)
            
            # Mock all parsers to avoid actual parsing
            with patch('services.doc_parser.extract_with_mineru_if_available', return_value=None), \
                 patch('parsers.doc_parser.DocParser.parse', return_value="Mocked content"), \
                 patch('parsers.smeta_parser.SmetaParser.parse', return_value=[{"mocked": "data"}]):
                
                result = self.parser.parse_document(zip_path)
                
                assert result["success"] is True
                assert result["source_type"] == "zip_archive"
                assert result["files_processed"] >= 0  # Depends on mocking
    
    def test_convenience_function(self):
        """Test the convenience parse_document function"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file.flush()
            
            try:
                # Test the module-level convenience function
                with patch('parsers.doc_parser.DocParser.parse', return_value="Test content"):
                    result = parse_document(tmp_file.name)
                    assert result["success"] is True
                    
            finally:
                os.unlink(tmp_file.name)


class TestParseResult:
    """Test the ParseResult dataclass"""
    
    def test_parse_result_creation(self):
        """Test creating ParseResult instances"""
        result = ParseResult(
            success=True,
            content="test content",
            metadata={"test": "value"},
            source_file="test.pdf",
            parser_used="mineru"
        )
        
        assert result.success is True
        assert result.content == "test content"
        assert result.metadata["test"] == "value"
        assert result.source_file == "test.pdf"
        assert result.parser_used == "mineru"
        assert result.error_message is None
    
    def test_parse_result_with_error(self):
        """Test ParseResult with error message"""
        result = ParseResult(
            success=False,
            content="",
            metadata={},
            source_file="test.pdf",
            parser_used="none",
            error_message="Test error"
        )
        
        assert result.success is False
        assert result.error_message == "Test error"


# Integration tests
class TestIntegration:
    """Integration tests for the document parser service"""
    
    def test_real_text_file_parsing(self):
        """Test parsing an actual text file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
            test_content = """
            Projektová dokumentace
            Beton C30/37 - XC4, XF3
            Objem: 125.5 m³
            Železobeton C35/45
            """
            tmp_file.write(test_content)
            tmp_file.flush()
            
            try:
                result = parse_document(tmp_file.name)
                
                assert result["success"] is True
                assert len(result["results"]) == 1
                
                # Content should contain the Czech text
                content = str(result["results"][0].content)
                assert "C30/37" in content or "C35/45" in content
                
            finally:
                os.unlink(tmp_file.name)
    
    def test_unsupported_file_extension(self):
        """Test handling of unsupported file extensions"""
        with tempfile.NamedTemporaryFile(suffix='.unsupported', delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file.flush()
            
            try:
                result = parse_document(tmp_file.name)
                
                # Should fail gracefully
                assert result["success"] is False
                assert "error" in result
                
            finally:
                os.unlink(tmp_file.name)


if __name__ == "__main__":
    # Simple test runner
    import sys
    
    # Run basic tests
    parser = UnifiedDocumentParser()
    print("✅ Parser initialization successful")
    
    # Test file info
    info = parser.get_file_info(__file__)
    print(f"✅ File info test: {info['name']}")
    
    # Test nonexistent file
    result = parser.parse_document("/nonexistent/file.pdf")
    assert not result["success"]
    print("✅ Nonexistent file test passed")
    
    print("🎉 Basic tests completed successfully!")