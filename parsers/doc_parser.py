"""
Document Parser - Minimal implementation for TZD Reader
Supports PDF, DOCX, and TXT files
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DocParser:
    """
    Simple document parser for PDF, DOCX, and TXT files
    """
    
    def __init__(self):
        self.supported_extensions = {'.pdf', '.docx', '.txt'}
    
    def parse(self, file_path: str) -> str:
        """
        Parse document and extract text
        
        Args:
            file_path: Path to document file
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file does not exist
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        extension = path.suffix.lower()
        
        if extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file format: {extension}")
        
        try:
            if extension == '.pdf':
                return self._parse_pdf(file_path)
            elif extension == '.docx':
                return self._parse_docx(file_path)
            elif extension == '.txt':
                return self._parse_txt(file_path)
            else:
                raise ValueError(f"Unsupported extension: {extension}")
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            raise
    
    def _parse_pdf(self, file_path: str) -> str:
        """Parse PDF file using pdfplumber"""
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed")
            raise ImportError("pdfplumber is required for PDF parsing. Install it with: pip install pdfplumber")
        
        text_parts = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return '\n'.join(text_parts)
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            raise
    
    def _parse_docx(self, file_path: str) -> str:
        """Parse DOCX file using python-docx"""
        try:
            from docx import Document
        except ImportError:
            logger.error("python-docx not installed")
            raise ImportError("python-docx is required for DOCX parsing. Install it with: pip install python-docx")
        
        try:
            doc = Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return '\n'.join(paragraphs)
        except Exception as e:
            logger.error(f"DOCX parsing error: {e}")
            raise
    
    def _parse_txt(self, file_path: str) -> str:
        """Parse plain text file"""
        try:
            # Try UTF-8 first, then fall back to other encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as binary and decode with errors='ignore'
            with open(file_path, 'rb') as f:
                return f.read().decode('utf-8', errors='ignore')
                
        except Exception as e:
            logger.error(f"TXT parsing error: {e}")
            raise
