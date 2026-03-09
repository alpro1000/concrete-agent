"""
Parsers package.

Главный класс для использования в routes и сервисах:
    from app.parsers import SmartPdfParser

Прямой доступ к отдельным парсерам (для тестов):
    from app.parsers import PDFParser, PdfVisionParser, MinerUParser
"""
from app.parsers.pdf_parser import PDFParser
from app.parsers.pdf_vision_parser import PdfVisionParser
from app.parsers.mineru_parser import MinerUParser
from app.parsers.smart_pdf_parser import SmartPdfParser
from app.parsers.excel_parser import ExcelParser

__all__ = [
    "SmartPdfParser",   # ← использовать в продакшне
    "PDFParser",         # pdfplumber
    "PdfVisionParser",   # Claude Vision
    "MinerUParser",      # MinerU 2.x (тяжёлый)
    "ExcelParser",
]
