"""
Лёгкий универсальный парсер документов
Поддерживает PDF, DOCX, TXT и fallback через textract
"""

import os
import logging
import pdfplumber
import textract
from docx import Document

logger = logging.getLogger(__name__)

class DocParser:
    """Парсер для различных форматов документов"""

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
            elif ext == ".docx":
                return self._parse_docx(file_path)
            elif ext in (".txt", ".log", ".md"):
                return self._parse_txt(file_path)
            else:
                logger.warning(f"⚠️ Неизвестный формат {ext}, пробую через textract...")
                return self._parse_textract(file_path)

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {file_path}: {e}")
            return ""

    def _parse_pdf(self, file_path: str) -> str:
        """Извлечение текста из PDF"""
        text = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text.append(page.extract_text() or "")
        except Exception as e:
            logger.error(f"Ошибка парсинга PDF {file_path}: {e}")
            return self._parse_textract(file_path)

        return "\n".join(text).strip()

    def _parse_docx(self, file_path: str) -> str:
        """Извлечение текста из DOCX"""
        try:
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error(f"Ошибка парсинга DOCX {file_path}: {e}")
            return self._parse_textract(file_path)

    def _parse_txt(self, file_path: str) -> str:
        """Извлечение текста из TXT/MD"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Ошибка чтения TXT {file_path}: {e}")
            return ""

    def _parse_textract(self, file_path: str) -> str:
        """Fallback через textract (поддерживает doc, rtf, ppt и др.)"""
        try:
            text = textract.process(file_path)
            return text.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Textract не смог обработать {file_path}: {e}")
            return ""
