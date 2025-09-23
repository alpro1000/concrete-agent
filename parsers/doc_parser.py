"""
Лёгкий универсальный парсер документов
Поддерживает PDF, DOCX, TXT БЕЗ textract (исправлено для Render)
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DocParser:
    """Парсер для различных форматов документов БЕЗ textract"""

    def __init__(self):
        pass

    def parse(self, file_path: str) -> str:
        """
        Определяет тип документа и вызывает нужный парсер
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".pdf":
                return self._parse_pdf(file_path)
            elif ext in [".docx", ".doc"]:
                return self._parse_docx(file_path)
            elif ext in (".txt", ".log", ".md"):
                return self._parse_txt(file_path)
            else:
                logger.warning(f"⚠️ Неизвестный формат {ext}, пробую как текстовый файл...")
                return self._parse_txt(file_path)

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {file_path}: {e}")
            return ""

    def _parse_pdf(self, file_path: str) -> str:
        """Извлечение текста из PDF через pdfplumber"""
        try:
            import pdfplumber
            text = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
            return "\n".join(text).strip()
        except ImportError:
            logger.error("pdfplumber не установлен! Добавьте в requirements.txt")
            return ""
        except Exception as e:
            logger.error(f"Ошибка парсинга PDF {file_path}: {e}")
            return ""

    def _parse_docx(self, file_path: str) -> str:
        """Извлечение текста из DOCX через python-docx"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = []
            
            # Извлекаем текст из параграфов
            for para in doc.paragraphs:
                if para.text.strip():
                    text.append(para.text.strip())
            
            # Извлекаем текст из таблиц
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text.append(" | ".join(row_text))
            
            return "\n".join(text)
            
        except ImportError:
            logger.error("python-docx не установлен! Добавьте в requirements.txt")
            return ""
        except Exception as e:
            logger.error(f"Ошибка парсинга DOCX {file_path}: {e}")
            return ""

    def _parse_txt(self, file_path: str) -> str:
        """Извлечение текста из TXT/MD с определением кодировки"""
        encodings = ['utf-8', 'cp1251', 'windows-1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Ошибка чтения файла {file_path} с кодировкой {encoding}: {e}")
                continue
        
        # Если ни одна кодировка не сработала
        logger.error(f"Не удалось определить кодировку для {file_path}")
        return ""

    def get_supported_formats(self) -> list[str]:
        """Возвращает список поддерживаемых форматов"""
        return ['.pdf', '.docx', '.doc', '.txt', '.md', '.log']

    def check_dependencies(self) -> dict[str, bool]:
        """Проверка доступности библиотек"""
        deps = {
            'pdfplumber': False,
            'python-docx': False
        }
        
        try:
            import pdfplumber
            deps['pdfplumber'] = True
        except ImportError:
            pass
            
        try:
            from docx import Document
            deps['python-docx'] = True
        except ImportError:
            pass
            
        return deps
