"""
MinerU Parser — тяжёлый парсер для сложных PDF (MinerU 2.x).

Активируется ТОЛЬКО если:
  1. ENABLE_MINERU=true в .env
  2. Переменная USE_MINERU=true в запросе (явный выбор)

На Render Free (512MB) — ОТКЛЮЧЁН по умолчанию.
Для включения нужен сервис с 2GB+ RAM.

Если mineru не установлен — логирует предупреждение и возвращает None,
чтобы SmartPdfParser мог переключиться на fallback.
"""
import os
from pathlib import Path
from typing import Any

from loguru import logger

# Флаг: загружен ли mineru в текущем окружении
_MINERU_AVAILABLE: bool = False
_MINERU_IMPORT_ERROR: str = ""

try:
    if os.getenv("ENABLE_MINERU", "false").lower() == "true":
        from mineru.cli.common import do_parse  # type: ignore
        _MINERU_AVAILABLE = True
        logger.info("MinerU 2.x loaded successfully")
    else:
        logger.info("MinerU disabled (ENABLE_MINERU != true), skipping import")
except ImportError as e:
    _MINERU_IMPORT_ERROR = str(e)
    logger.warning(
        f"MinerU not available: {e}. "
        "Install with: pip install mineru[pipeline]"
    )
except Exception as e:
    _MINERU_IMPORT_ERROR = str(e)
    logger.error(f"MinerU import failed unexpectedly: {e}")


class MinerUParser:
    """
    Обёртка над MinerU 2.x pipeline.

    Условие использования:
    - ENABLE_MINERU=true в .env
    - Сервис с 2GB+ RAM
    - Установлен пакет: pip install mineru[pipeline]

    Возвращает None если MinerU недоступен — SmartPdfParser
    автоматически переключится на PdfVisionParser.
    """

    def __init__(self, output_dir: str = "/tmp/mineru_output"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_available(self) -> bool:
        return _MINERU_AVAILABLE

    def parse(
        self,
        file_path: Path,
        method: str = "auto",
    ) -> dict[str, Any] | None:
        """
        Парсит PDF через MinerU 2.x.

        Args:
            file_path: Путь к PDF
            method:    'auto' | 'ocr' | 'txt'
                       auto — MinerU сам определяет
                       ocr  — принудительный OCR (для сканов)
                       txt  — только текстовый слой (быстро)

        Returns:
            dict с ключами positions/markdown/tables
            или None если MinerU недоступен
        """
        if not _MINERU_AVAILABLE:
            logger.warning(
                f"MinerU unavailable, cannot parse {file_path.name}. "
                f"Error: {_MINERU_IMPORT_ERROR}"
            )
            return None

        logger.info(f"MinerU parsing: {file_path.name}, method={method}")

        output_path = self._output_dir / file_path.stem
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            # MinerU 2.x API
            from mineru.cli.common import do_parse  # type: ignore

            do_parse(
                source=str(file_path),
                output_dir=str(output_path),
                method=method,
                backend="pipeline",   # pipeline = без VLM сервера
                lang="cs",            # чешский по умолчанию
            )

            # Читаем результаты из output директории
            md_files = list(output_path.glob("**/*.md"))
            json_files = list(output_path.glob("**/*.json"))

            markdown_content = ""
            if md_files:
                markdown_content = md_files[0].read_text(encoding="utf-8")

            tables = []
            if json_files:
                import json
                raw_json = json.loads(json_files[0].read_text(encoding="utf-8"))
                tables = raw_json.get("tables", [])

            logger.info(
                f"MinerU done: {file_path.name}, "
                f"md_chars={len(markdown_content)}, tables={len(tables)}"
            )

            return {
                "document_info": {
                    "filename": file_path.name,
                    "format": "pdf_mineru",
                    "method_used": method,
                },
                "positions": [],   # MinerU даёт markdown, не positions напрямую
                "markdown": markdown_content,
                "tables": tables,
                "diagnostics": {
                    "source": "mineru",
                    "method": method,
                    "md_chars": len(markdown_content),
                    "tables_found": len(tables),
                },
            }

        except Exception as e:
            logger.error(
                f"MinerU parse error for {file_path.name}: {e}", exc_info=True
            )
            return None
