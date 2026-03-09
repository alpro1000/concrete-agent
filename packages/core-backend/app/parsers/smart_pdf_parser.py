"""
SmartPdfParser — главный оркестратор PDF парсинга.

Стратегия (waterfall):
  1. PDFParser (pdfplumber)         — цифровые PDF, смета с таблицами
      ↓ если 0 позиций
  2. PdfVisionParser (Claude Vision) — сканы, чертежи, сложные макеты
      ↓ если ENABLE_MINERU=true
  3. MinerUParser                   — тяжёлый fallback (нужен 2GB RAM)

Входная точка для всей системы — используй только этот класс.
Не импортируй PDFParser/PdfVisionParser напрямую в routes.
"""
from pathlib import Path
from typing import Any

from loguru import logger

from app.parsers.pdf_parser import PDFParser
from app.parsers.pdf_vision_parser import PdfVisionParser
from app.parsers.mineru_parser import MinerUParser


class SmartPdfParser:
    """
    Единая точка входа для парсинга любых PDF документов.

    Примеры использования:

        parser = SmartPdfParser()

        # Смета (цифровая или скан — определит автоматически)
        result = parser.parse(Path('smeta.pdf'), doc_type='smeta')

        # Чертёж — сразу Vision
        result = parser.parse(Path('plan.pdf'), doc_type='drawing')

        # Техзадание
        result = parser.parse(Path('tz.pdf'), doc_type='tz')
    """

    # Минимум позиций после pdfplumber чтобы считать успехом
    MIN_POSITIONS_THRESHOLD = 1

    def __init__(
        self,
        pdf_parser: PDFParser | None = None,
        vision_parser: PdfVisionParser | None = None,
        mineru_parser: MinerUParser | None = None,
    ):
        # Dependency Injection — можно передать моки для тестов
        self._pdf_parser = pdf_parser or PDFParser()
        self._vision_parser = vision_parser or PdfVisionParser()
        self._mineru_parser = mineru_parser or MinerUParser()

    def parse(
        self,
        file_path: Path,
        doc_type: str = "smeta",
        force_vision: bool = False,
        force_mineru: bool = False,
    ) -> dict[str, Any]:
        """
        Парсит PDF с автоматическим выбором стратегии.

        Args:
            file_path:    Путь к PDF файлу
            doc_type:     'smeta' | 'drawing' | 'tz'
            force_vision: Принудительно использовать Claude Vision
            force_mineru: Принудительно использовать MinerU

        Returns:
            Унифицированный результат:
            {
                'document_info': {...},
                'positions': [...],
                'diagnostics': {
                    'strategy_used': 'pdfplumber|claude_vision|mineru',
                    ...
                }
            }
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return self._error_result(file_path, "File not found")

        logger.info(
            f"SmartPdfParser: {file_path.name}, "
            f"doc_type={doc_type}, "
            f"force_vision={force_vision}, "
            f"force_mineru={force_mineru}"
        )

        # Чертежи → сразу Vision (pdfplumber бесполезен для чертежей)
        if doc_type == "drawing" or force_vision:
            return self._try_vision(file_path, doc_type)

        # MinerU принудительно
        if force_mineru:
            result = self._try_mineru(file_path)
            if result:
                return result
            # MinerU недоступен — fallback на Vision
            logger.warning("MinerU unavailable, falling back to Vision")
            return self._try_vision(file_path, doc_type)

        # === Стандартный waterfall ===

        # Шаг 1: pdfplumber
        result = self._try_pdfplumber(file_path)
        positions_count = len(result.get("positions", []))

        if positions_count >= self.MIN_POSITIONS_THRESHOLD:
            logger.info(
                f"Strategy: pdfplumber SUCCESS "
                f"({positions_count} positions)"
            )
            result["diagnostics"]["strategy_used"] = "pdfplumber"
            return result

        logger.info(
            f"pdfplumber got {positions_count} positions — "
            f"trying Vision fallback"
        )

        # Шаг 2: Claude Vision fallback
        vision_result = self._try_vision(file_path, doc_type)
        vision_positions = len(vision_result.get("positions", []))

        if vision_positions > 0:
            logger.info(
                f"Strategy: claude_vision SUCCESS "
                f"({vision_positions} positions)"
            )
            vision_result["diagnostics"]["strategy_used"] = "claude_vision"
            return vision_result

        # Шаг 3: MinerU (если доступен)
        if self._mineru_parser.is_available:
            logger.info("Vision got 0 positions — trying MinerU")
            mineru_result = self._try_mineru(file_path)
            if mineru_result:
                mineru_result["diagnostics"]["strategy_used"] = "mineru"
                return mineru_result

        # Все методы исчерпаны — возвращаем лучший результат
        logger.warning(
            f"All parsers returned 0 positions for {file_path.name}"
        )
        vision_result["diagnostics"]["strategy_used"] = "claude_vision_empty"
        return vision_result

    def _try_pdfplumber(self, file_path: Path) -> dict:
        """Попытка через pdfplumber."""
        try:
            result = self._pdf_parser.parse(file_path)
            if "diagnostics" not in result:
                result["diagnostics"] = {}
            return result
        except Exception as e:
            logger.error(f"pdfplumber failed for {file_path.name}: {e}")
            return {"positions": [], "diagnostics": {"pdfplumber_error": str(e)}}

    def _try_vision(self, file_path: Path, doc_type: str) -> dict:
        """Попытка через Claude Vision."""
        try:
            return self._vision_parser.parse(file_path, doc_type=doc_type)
        except Exception as e:
            logger.error(f"Vision parser failed for {file_path.name}: {e}")
            return self._error_result(file_path, f"Vision error: {e}")

    def _try_mineru(self, file_path: Path) -> dict | None:
        """Попытка через MinerU. Возвращает None если недоступен."""
        try:
            return self._mineru_parser.parse(file_path)
        except Exception as e:
            logger.error(f"MinerU failed for {file_path.name}: {e}")
            return None

    @staticmethod
    def _error_result(file_path: Path, error: str) -> dict:
        return {
            "document_info": {
                "filename": file_path.name,
                "format": "pdf",
                "error": error,
            },
            "positions": [],
            "diagnostics": {
                "raw_total": 0,
                "normalized_total": 0,
                "skipped_total": 0,
                "pages_processed": 0,
                "strategy_used": "error",
            },
        }
