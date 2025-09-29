"""
Document Parser Service
Унифицированный парсер для документов (PDF, DOCX, TXT)
services/doc_parser.py

- PDF через pdfplumber
- DOCX через python-docx  
- TXT напрямую
- Автоматическое определение типа файла
"""

import logging
import pdfplumber
from pathlib import Path
from docx import Document as DocxDocument
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import zipfile
import tempfile
import os

logger = logging.getLogger(__name__)

@dataclass
class ParseResult:
    """Result of document parsing"""
    content: str
    file_path: str
    file_type: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class UnifiedDocumentParser:
    """
    Unified document parser that handles multiple file types and formats
    Supports PDF, DOCX, TXT files with integration capabilities
    """
    
    def __init__(self):
        self.doc_parser = DocParser()
        # Mock other parsers for compatibility
        self.smeta_parser = None
        self.xml_parser = None
        self.supported_extensions = ['pdf', 'docx', 'txt', 'md', 'xlsx', 'csv', 'xml']
        logger.info("📄 UnifiedDocumentParser инициализирован")
    
    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a document and return structured results
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Dict with success status, results, and metadata
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "results": [],
                    "source_type": "file",
                    "files_processed": 0
                }
            
            # Handle ZIP files
            if file_path.suffix.lower() == '.zip':
                return self._parse_zip_file(file_path)
            
            # Parse single file
            content = self.doc_parser.parse(str(file_path))
            
            if content:
                result = ParseResult(
                    content=content,
                    file_path=str(file_path),
                    file_type=file_path.suffix.lower(),
                    success=True,
                    metadata={"size": file_path.stat().st_size}
                )
                
                return {
                    "success": True,
                    "results": [result],
                    "source_type": "file",
                    "files_processed": 1,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to parse content from {file_path}",
                    "results": [],
                    "source_type": "file",
                    "files_processed": 0
                }
                
        except Exception as e:
            logger.error(f"❌ Error parsing document {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "source_type": "file",
                "files_processed": 0
            }
    
    def _parse_zip_file(self, zip_path: Path) -> Dict[str, Any]:
        """Parse files from a ZIP archive"""
        try:
            results = []
            files_processed = 0
            
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                with tempfile.TemporaryDirectory() as temp_dir:
                    for file_info in zip_file.infolist():
                        if file_info.is_dir():
                            continue
                            
                        # Extract file
                        extracted_path = zip_file.extract(file_info, temp_dir)
                        file_path = Path(extracted_path)
                        
                        # Parse extracted file
                        content = self.doc_parser.parse(str(file_path))
                        
                        if content:
                            result = ParseResult(
                                content=content,
                                file_path=file_info.filename,
                                file_type=file_path.suffix.lower(),
                                success=True,
                                metadata={"size": file_info.file_size, "from_zip": True}
                            )
                            results.append(result)
                            files_processed += 1
            
            return {
                "success": True,
                "results": results,
                "source_type": "zip_archive",
                "files_processed": files_processed,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing ZIP file {zip_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "source_type": "zip_archive",
                "files_processed": 0
            }
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get metadata about a file"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"error": "File not found"}
                
            return {
                "name": path.name,
                "size": path.stat().st_size,
                "extension": path.suffix.lower(),
                "supported": path.suffix.lower().lstrip('.') in self.supported_extensions
            }
        except Exception as e:
            return {"error": str(e)}


class DocParser:
    """
    Унифицированный парсер документов
    Поддерживает PDF, DOCX, TXT файлы
    """
    
    def __init__(self):
        self.czech_encodings = ['utf-8', 'cp1250', 'iso-8859-2']
        logger.info("📄 DocParser инициализирован")
    
    def parse(self, file_path: str) -> str:
        """
        Парсинг документа в текст
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Извлеченный текст или пустая строка при ошибке
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"❌ Файл не найден: {file_path}")
                return ""
            
            # Определяем тип файла по расширению
            extension = file_path.suffix.lower()
            
            if extension == '.pdf':
                return self._parse_pdf(file_path)
            elif extension == '.docx':
                return self._parse_docx(file_path)
            elif extension in ['.txt', '.md']:
                return self._parse_text(file_path)
            else:
                logger.warning(f"⚠️ Неподдерживаемый тип файла: {extension}")
                # Пытаемся читать как текст
                return self._parse_text(file_path)
                
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {file_path}: {e}")
            return ""
    
    def _parse_pdf(self, file_path: Path) -> str:
        """Парсинг PDF файла"""
        try:
            with pdfplumber.open(file_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                result = '\n'.join(text_parts)
                logger.info(f"✅ PDF обработан: {len(result)} символов")
                return result
                
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга PDF {file_path}: {e}")
            return ""
    
    def _parse_docx(self, file_path: Path) -> str:
        """Парсинг DOCX файла"""
        try:
            doc = DocxDocument(file_path)
            text_parts = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            result = '\n'.join(text_parts)
            logger.info(f"✅ DOCX обработан: {len(result)} символов")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга DOCX {file_path}: {e}")
            return ""
    
    def _parse_text(self, file_path: Path) -> str:
        """Парсинг текстового файла с поддержкой различных кодировок"""
        # Пробуем различные кодировки для чешских текстов
        for encoding in self.czech_encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    result = f.read()
                    logger.info(f"✅ Текст обработан ({encoding}): {len(result)} символов")
                    return result
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"❌ Ошибка чтения файла {file_path} с кодировкой {encoding}: {e}")
                continue
        
        logger.error(f"❌ Не удалось прочитать файл {file_path} ни с одной кодировкой")
        return ""
    
    def get_supported_extensions(self) -> list:
        """Возвращает список поддерживаемых расширений"""
        return ['.pdf', '.docx', '.txt', '.md']


# Global instance for singleton pattern
_unified_parser = None

def get_unified_document_parser() -> UnifiedDocumentParser:
    """Get singleton instance of UnifiedDocumentParser"""
    global _unified_parser
    if _unified_parser is None:
        _unified_parser = UnifiedDocumentParser()
    return _unified_parser

def parse_document(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse a document
    
    Args:
        file_path: Path to the file to parse
        
    Returns:
        Dict with success status, results, and metadata
    """
    parser = get_unified_document_parser()
    return parser.parse_document(file_path)

# MinerU integration placeholder
def extract_with_mineru_if_available(file_path: str) -> Optional[str]:
    """
    Placeholder for MinerU integration
    Returns None if MinerU is not available or fails
    """
    try:
        # MinerU integration would go here
        # For now, return None to fallback to standard parsing
        return None
    except Exception:
        return None
