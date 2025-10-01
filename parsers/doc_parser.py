"""
Document Parser - Simple implementation for parsing various document formats
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DocParser:
    """
    Simple document parser supporting PDF, DOCX, and TXT files
    """
    
    def __init__(self):
        """Initialize parser"""
        self.supported_formats = ['.pdf', '.docx', '.doc', '.txt']
    
    def parse(self, file_path: str) -> str:
        """
        Parse a document and extract text.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Extracted text content
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        try:
            if extension == '.txt':
                return self._parse_txt(file_path)
            elif extension == '.pdf':
                return self._parse_pdf(file_path)
            elif extension in ['.docx', '.doc']:
                return self._parse_docx(file_path)
            else:
                logger.warning(f"Unsupported file format: {extension}")
                return ""
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return ""
    
    def _parse_txt(self, file_path: Path) -> str:
        """Parse plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading TXT file: {e}")
            return ""
    
    def _parse_pdf(self, file_path: Path) -> str:
        """Parse PDF file using pdfplumber"""
        try:
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            
            return '\n\n'.join(text_parts)
        except ImportError:
            logger.warning("pdfplumber not available, cannot parse PDF")
            return ""
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return ""
    
    def _parse_docx(self, file_path: Path) -> str:
        """Parse DOCX file using python-docx"""
        try:
            from docx import Document
            
            doc = Document(file_path)
            text_parts = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            return '\n\n'.join(text_parts)
        except ImportError:
            logger.warning("python-docx not available, cannot parse DOCX")
            return ""
        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}")
            return ""
