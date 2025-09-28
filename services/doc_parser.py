"""
Unified Document Parser Service with MinerU Integration
services/doc_parser.py

This service provides a unified interface for document parsing that:
1. Uses MinerU as the primary parser for all document types
2. Falls back to legacy parsers if MinerU fails or is unavailable
3. Handles single files and ZIP archives
4. Returns structured JSON results
5. Maintains backward compatibility with existing agents
"""

import os
import json
import logging
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict

# Import existing parsers for fallback
from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser  
from parsers.xml_smeta_parser import parse_xml_smeta

# Import MinerU integration
from utils.mineru_client import extract_with_mineru_if_available

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Structured result from document parsing"""
    success: bool
    content: Union[str, Dict[str, Any], List[Dict[str, Any]]]
    metadata: Dict[str, Any]
    source_file: str
    parser_used: str
    error_message: Optional[str] = None


class UnifiedDocumentParser:
    """
    Unified document parser that uses MinerU as primary with fallback to legacy parsers
    """
    
    def __init__(self):
        """Initialize the unified parser with all fallback parsers"""
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        # Note: xml_smeta_parser is a function, not a class
        
        # Track supported file extensions
        self.supported_extensions = {
            'pdf', 'docx', 'doc', 'txt', 'xls', 'xlsx', 'xml', 'zip'
        }
        
        logger.info("🔧 UnifiedDocumentParser initialized with MinerU integration")

    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        Main entry point for document parsing
        
        Args:
            file_path: Path to file or ZIP archive
            
        Returns:
            Unified JSON structure with parsed content
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "results": []
            }
        
        file_path_obj = Path(file_path)
        
        # Handle ZIP files by extracting and parsing each file
        if file_path_obj.suffix.lower() == '.zip':
            return self._parse_zip_archive(file_path)
        
        # Handle single files
        return self._parse_single_file(file_path)

    def _parse_zip_archive(self, zip_path: str) -> Dict[str, Any]:
        """
        Extract and parse all files from ZIP archive
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            Combined results from all files in ZIP
        """
        results = []
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Parse each extracted file
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_ext = Path(file).suffix.lower().lstrip('.')
                        
                        if file_ext in self.supported_extensions:
                            result = self._parse_single_file(file_path)
                            if result["success"]:
                                results.extend(result["results"])
                        else:
                            logger.warning(f"Skipping unsupported file: {file}")
            
            return {
                "success": True,
                "source_type": "zip_archive",
                "source_file": zip_path,
                "files_processed": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing ZIP archive {zip_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "source_file": zip_path,
                "results": []
            }

    def _parse_single_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a single file using MinerU with fallback to legacy parsers
        
        Args:
            file_path: Path to single file
            
        Returns:
            Parse result with unified structure
        """
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()
        
        logger.info(f"🔍 Parsing file: {file_path_obj.name}")
        
        # Try MinerU first
        mineru_result = self._try_mineru_parsing([file_path])
        if mineru_result:
            return {
                "success": True,
                "source_file": file_path,
                "results": [mineru_result]
            }
        
        # Fallback to legacy parsers
        try:
            legacy_result = self._parse_with_legacy_parsers(file_path, file_ext)
            return {
                "success": True,
                "source_file": file_path,
                "results": [legacy_result]
            }
            
        except Exception as e:
            logger.error(f"❌ All parsing methods failed for {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "source_file": file_path,
                "results": []
            }

    def _try_mineru_parsing(self, file_paths: List[str]) -> Optional[ParseResult]:
        """
        Attempt to parse files using MinerU
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            ParseResult if successful, None if failed/unavailable
        """
        try:
            mineru_content = extract_with_mineru_if_available(file_paths)
            
            if mineru_content:
                # Try to parse as JSON first, fallback to plain text
                try:
                    content_json = json.loads(mineru_content)
                    content = content_json
                except json.JSONDecodeError:
                    content = mineru_content
                
                return ParseResult(
                    success=True,
                    content=content,
                    metadata={
                        "parser": "mineru",
                        "files_processed": len(file_paths),
                        "content_type": "json" if isinstance(content, dict) else "text",
                        "content_length": len(str(content))
                    },
                    source_file=file_paths[0] if file_paths else "unknown",
                    parser_used="mineru"
                )
            
        except Exception as e:
            logger.debug(f"MinerU parsing failed: {e}")
        
        return None

    def _parse_with_legacy_parsers(self, file_path: str, file_ext: str) -> ParseResult:
        """
        Parse file using legacy parsers based on file extension
        
        Args:
            file_path: Path to file
            file_ext: File extension (with dot)
            
        Returns:
            ParseResult from legacy parser
        """
        content = None
        parser_used = None
        
        try:
            if file_ext == '.pdf' or file_ext in ['.docx', '.doc', '.txt']:
                # Use DocParser for PDF, DOCX, DOC, TXT
                content = self.doc_parser.parse(file_path)
                parser_used = "doc_parser"
                
            elif file_ext in ['.xls', '.xlsx']:
                # Use SmetaParser for Excel files
                content = self.smeta_parser.parse(file_path)
                parser_used = "smeta_parser"
                
            elif file_ext == '.xml':
                # Use xml_smeta_parser function for XML files  
                content = parse_xml_smeta(file_path)
                parser_used = "xml_parser"
                
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            return ParseResult(
                success=True,
                content=content,
                metadata={
                    "parser": parser_used,
                    "file_extension": file_ext,
                    "content_type": "structured" if isinstance(content, (dict, list)) else "text",
                    "content_length": len(str(content)) if content else 0,
                    "fallback": True
                },
                source_file=file_path,
                parser_used=parser_used
            )
            
        except Exception as e:
            logger.error(f"❌ Legacy parser {parser_used} failed for {file_path}: {e}")
            raise

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata about a file without parsing it
        
        Args:
            file_path: Path to file
            
        Returns:
            File metadata dictionary
        """
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        file_path_obj = Path(file_path)
        file_stat = os.stat(file_path)
        
        return {
            "name": file_path_obj.name,
            "extension": file_path_obj.suffix.lower(),
            "size_bytes": file_stat.st_size,
            "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "path": str(file_path_obj.absolute()),
            "supported": file_path_obj.suffix.lower().lstrip('.') in self.supported_extensions,
            "can_use_mineru": file_path_obj.suffix.lower() in ['.pdf', '.docx', '.xlsx', '.xml'],
            "legacy_parser": self._get_legacy_parser_for_extension(file_path_obj.suffix.lower())
        }

    def _get_legacy_parser_for_extension(self, ext: str) -> str:
        """Get the legacy parser name for a file extension"""
        if ext in ['.pdf', '.docx', '.doc', '.txt']:
            return "doc_parser"
        elif ext in ['.xls', '.xlsx']:
            return "smeta_parser"
        elif ext == '.xml':
            return "xml_parser"
        else:
            return "unsupported"


# Singleton instance for global use
_unified_parser_instance = None


def get_unified_document_parser() -> UnifiedDocumentParser:
    """Get singleton instance of UnifiedDocumentParser"""
    global _unified_parser_instance
    if _unified_parser_instance is None:
        _unified_parser_instance = UnifiedDocumentParser()
    return _unified_parser_instance


def parse_document(file_path: str) -> Dict[str, Any]:
    """
    Convenience function for document parsing
    
    Args:
        file_path: Path to document or ZIP archive
        
    Returns:
        Unified JSON structure with parsed content
    """
    parser = get_unified_document_parser()
    return parser.parse_document(file_path)


# Export main functions
__all__ = [
    'UnifiedDocumentParser', 
    'ParseResult', 
    'parse_document', 
    'get_unified_document_parser'
]