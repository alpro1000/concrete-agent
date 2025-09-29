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
from typing import Optional

logger = logging.getLogger(__name__)

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
