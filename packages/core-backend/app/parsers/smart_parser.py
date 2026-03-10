"""
Smart Parser — automatic selection of the optimal parsing strategy.

Strategy matrix:
  Excel / XML  → pandas / KROS / streaming (by file size)
  PDF (small)  → pdfplumber  →  fallback: MinerU (async)
  PDF (large)  → MinerU directly (async)

MinerU is always called asynchronously to avoid blocking the FastAPI
event loop during the 20-40 min CPU inference run.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.parsers.excel_parser import ExcelParser
from app.parsers.kros_parser import KROSParser
from app.parsers.memory_efficient import (
    MemoryEfficientExcelParser,
    MemoryEfficientPDFParser,
    MemoryEfficientXMLParser,
)
from app.parsers.mineru_parser import MinerUParser, MinerUParseError
from app.parsers.pdf_parser import PDFParser

logger = logging.getLogger(__name__)

# Threshold for switching to streaming / MinerU (MB)
_SIZE_THRESHOLD_MB = 20

# Shared MinerU instance (stateless — safe to reuse)
_mineru_parser = MinerUParser(backend="pipeline", device="cpu")


class SmartParser:
    """
    Automatic parser dispatcher.

    Single Responsibility: decides WHICH parser to use.
    Does NOT implement parsing logic itself.
    """

    def __init__(self) -> None:
        self._excel_parser = ExcelParser()
        self._pdf_parser = PDFParser()
        self._kros_parser = KROSParser()
        self._streaming_excel = MemoryEfficientExcelParser()
        self._streaming_pdf = MemoryEfficientPDFParser()
        self._streaming_xml = MemoryEfficientXMLParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, file_path: Path, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous entry point — dispatches by extension."""
        suffix = file_path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            return self.parse_excel(file_path, project_id=project_id)
        elif suffix == ".pdf":
            # Run async parse in a new event loop if called from sync context
            return asyncio.run(self.parse_pdf_async(file_path, project_id=project_id))
        elif suffix == ".xml":
            return self.parse_xml(file_path, project_id=project_id)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    async def parse_async(
        self, file_path: Path, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Async entry point — preferred when called from FastAPI routes."""
        suffix = file_path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            return self.parse_excel(file_path, project_id=project_id)
        elif suffix == ".pdf":
            return await self.parse_pdf_async(file_path, project_id=project_id)
        elif suffix == ".xml":
            return self.parse_xml(file_path, project_id=project_id)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    # ------------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------------

    def parse_excel(
        self, file_path: Path, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        size_mb = _get_file_size_mb(file_path)
        log_prefix = _build_log_prefix(project_id)
        logger.info("%s📊 Excel: %s (%.1f MB)", log_prefix, file_path.name, size_mb)

        if size_mb < _SIZE_THRESHOLD_MB:
            try:
                return self._excel_parser.parse(file_path, project_id=project_id)
            except Exception as exc:
                logger.warning("%sStandard Excel parser failed: %s — using streaming", log_prefix, exc)
                return self._streaming_excel.parse(file_path)
        return self._streaming_excel.parse(file_path)

    # ------------------------------------------------------------------
    # PDF  (async — MinerU for complex table-heavy PDFs)
    # ------------------------------------------------------------------

    async def parse_pdf_async(
        self,
        file_path: Path,
        project_id: Optional[str] = None,
        output_base_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Parse PDF asynchronously.

        Strategy:
          1. size < 20 MB → try pdfplumber first (fast, no GPU needed)
          2. pdfplumber fails OR size >= 20 MB → MinerU (async subprocess)
          3. MinerU fails → streaming pdfplumber fallback
        """
        size_mb = _get_file_size_mb(file_path)
        log_prefix = _build_log_prefix(project_id)
        logger.info("%s📄 PDF: %s (%.1f MB)", log_prefix, file_path.name, size_mb)

        output_dir = output_base_dir or file_path.parent / "mineru_output"

        if size_mb < _SIZE_THRESHOLD_MB:
            try:
                result = self._pdf_parser.parse(file_path)
                # pdfplumber returns empty content for image-only PDFs
                if _is_parse_result_empty(result):
                    raise ValueError("pdfplumber returned empty content — likely image PDF")
                logger.info("%s✅ pdfplumber succeeded", log_prefix)
                return result
            except Exception as exc:
                logger.warning(
                    "%spdfplumber failed or empty (%s) — switching to MinerU",
                    log_prefix,
                    exc,
                )

        # MinerU path (async)
        logger.info("%s🔄 Starting MinerU async parse for '%s'", log_prefix, file_path.name)
        mineru_result = await _mineru_parser.parse_document(
            source_pdf_path=file_path,
            output_base_dir=output_dir,
        )

        if isinstance(mineru_result, MinerUParseError):
            logger.error(
                "%sMinerU failed [%s]: %s — streaming fallback",
                log_prefix,
                mineru_result.error_code,
                mineru_result.message,
            )
            return self._streaming_pdf.parse(file_path, max_pages=100)

        logger.info(
            "%s✅ MinerU OK: %d tables, ~%d pages",
            log_prefix,
            mineru_result.table_count,
            mineru_result.page_count,
        )
        return {
            "format": "pdf",
            "parser": "mineru",
            "content": mineru_result.markdown_content,
            "table_count": mineru_result.table_count,
            "page_count": mineru_result.page_count,
            "source": str(mineru_result.source_path),
        }

    # ------------------------------------------------------------------
    # XML
    # ------------------------------------------------------------------

    def parse_xml(
        self, file_path: Path, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        size_mb = _get_file_size_mb(file_path)
        log_prefix = _build_log_prefix(project_id)
        logger.info("%s📝 XML: %s (%.1f MB)", log_prefix, file_path.name, size_mb)

        if size_mb < _SIZE_THRESHOLD_MB:
            try:
                return self._kros_parser.parse(file_path, project_id=project_id)
            except Exception as exc:
                logger.warning("%sKROS parser failed: %s — streaming fallback", log_prefix, exc)
                return self._streaming_xml.parse(file_path)
        return self._streaming_xml.parse(file_path)

    # ------------------------------------------------------------------
    # Info (no parsing)
    # ------------------------------------------------------------------

    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        size_mb = _get_file_size_mb(file_path)
        return {
            "filename": file_path.name,
            "format": file_path.suffix.lower(),
            "size_bytes": file_path.stat().st_size,
            "size_mb": round(size_mb, 2),
            "will_use_streaming": size_mb >= _SIZE_THRESHOLD_MB,
            "recommended_parser": "streaming" if size_mb >= _SIZE_THRESHOLD_MB else "standard",
        }


# ---------------------------------------------------------------------------
# Private helpers (module-level — testable without instantiation)
# ---------------------------------------------------------------------------

def _get_file_size_mb(file_path: Path) -> float:
    return file_path.stat().st_size / (1024 * 1024)


def _build_log_prefix(project_id: Optional[str]) -> str:
    return f"[project={project_id}] " if project_id else ""


def _is_parse_result_empty(result: Dict[str, Any]) -> bool:
    """Return True if pdfplumber produced no usable content."""
    content = result.get("content", "")
    return not content or len(str(content).strip()) < 50
