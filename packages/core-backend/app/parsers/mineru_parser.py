"""
MinerU PDF parser — production-ready version.

Fixes:
- Windows diacritics bug: slugify input filename before passing to MinerU
- UTF-8 read: explicit encoding when reading output .md file
- Async execution: subprocess via asyncio to avoid blocking the event loop
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MinerUParseResult:
    """Immutable result of a MinerU parse operation."""
    source_path: Path
    markdown_content: str
    output_dir: Path
    page_count: int
    table_count: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def is_successful(self) -> bool:
        return bool(self.markdown_content) and not self.errors


@dataclass(frozen=True)
class MinerUParseError:
    """Structured error from MinerU parser."""
    source_path: Path
    error_code: str
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify_filename(original_name: str) -> str:
    """
    Convert a filename with diacritics to ASCII-safe slug.

    Example:
        'IV MM-Ceník2026.pdf'  →  'IV_MM-Cenik2026.pdf'
    """
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix

    # Normalize Unicode → decompose diacritics → drop combining marks
    normalized = unicodedata.normalize("NFKD", stem)
    ascii_stem = normalized.encode("ascii", "ignore").decode("ascii")

    # Replace spaces and unsafe chars with underscores
    safe_stem = re.sub(r"[^\w\-]", "_", ascii_stem)
    safe_stem = re.sub(r"_+", "_", safe_stem).strip("_")

    return f"{safe_stem}{suffix}"


def _count_tables_in_markdown(markdown_content: str) -> int:
    return markdown_content.count("<table>")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class MinerUParser:
    """
    Async wrapper around the MinerU CLI.

    Responsibilities (SRP):
    - Copy input PDF to a temp dir with ASCII-safe filename
    - Run `mineru` CLI as async subprocess
    - Read result .md with explicit UTF-8 encoding
    - Return structured MinerUParseResult

    Does NOT handle: indexing, storage, LLM extraction (separate services).
    """

    def __init__(
        self,
        backend: str = "pipeline",
        device: str = "cpu",
        mineru_executable: str = "mineru",
    ) -> None:
        self._backend = backend
        self._device = device
        self._mineru_executable = mineru_executable

    async def parse_document(
        self,
        source_pdf_path: Path,
        output_base_dir: Path,
    ) -> MinerUParseResult | MinerUParseError:
        """
        Parse a PDF file using MinerU CLI asynchronously.

        Args:
            source_pdf_path: Original PDF path (may contain diacritics).
            output_base_dir: Directory where MinerU writes its output.

        Returns:
            MinerUParseResult on success, MinerUParseError on failure.
        """
        if not source_pdf_path.exists():
            return MinerUParseError(
                source_path=source_pdf_path,
                error_code="FILE_NOT_FOUND",
                message=f"Source PDF not found: {source_pdf_path}",
            )

        with tempfile.TemporaryDirectory(prefix="mineru_input_") as tmp_dir:
            safe_filename = _slugify_filename(source_pdf_path.name)
            safe_input_path = Path(tmp_dir) / safe_filename

            shutil.copy2(source_pdf_path, safe_input_path)
            logger.info(
                "Copied '%s' → '%s' (slugified)",
                source_pdf_path.name,
                safe_filename,
            )

            output_dir = output_base_dir / safe_input_path.stem / "auto"
            output_dir.mkdir(parents=True, exist_ok=True)

            parse_result = await self._run_mineru_subprocess(
                input_path=safe_input_path,
                output_dir=output_base_dir,
            )

            if isinstance(parse_result, MinerUParseError):
                return parse_result

            return self._read_mineru_output(
                source_path=source_pdf_path,
                output_dir=output_dir,
                stem=safe_input_path.stem,
            )

    async def _run_mineru_subprocess(
        self,
        input_path: Path,
        output_dir: Path,
    ) -> None | MinerUParseError:
        """Run MinerU CLI as async subprocess, stream stderr to logger."""
        cmd = [
            self._mineru_executable,
            "-p", str(input_path),
            "-o", str(output_dir),
            "-b", self._backend,
            "-d", self._device,
        ]

        logger.info("Running MinerU: %s", " ".join(cmd))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_message = stderr.decode("utf-8", errors="replace")
                logger.error(
                    "MinerU failed (exit %d): %s",
                    process.returncode,
                    error_message,
                )
                return MinerUParseError(
                    source_path=input_path,
                    error_code="MINERU_PROCESS_FAILED",
                    message=error_message[:500],
                )

            logger.info(
                "MinerU completed successfully for '%s'",
                input_path.name,
            )
            return None

        except FileNotFoundError:
            return MinerUParseError(
                source_path=input_path,
                error_code="MINERU_NOT_INSTALLED",
                message=(
                    f"'{self._mineru_executable}' not found in PATH. "
                    "Install with: pip install mineru"
                ),
            )
        except Exception as exc:
            logger.error(
                "Unexpected error running MinerU for '%s': %s",
                input_path.name,
                exc,
                exc_info=True,
            )
            return MinerUParseError(
                source_path=input_path,
                error_code="UNEXPECTED_ERROR",
                message=str(exc),
            )

    def _read_mineru_output(
        self,
        source_path: Path,
        output_dir: Path,
        stem: str,
    ) -> MinerUParseResult | MinerUParseError:
        """
        Read MinerU .md output with explicit UTF-8 encoding.

        MinerU always writes UTF-8. PowerShell default (cp1252) causes
        mojibake — we must specify encoding explicitly here.
        """
        md_path = output_dir / f"{stem}.md"

        if not md_path.exists():
            logger.error("Expected MinerU output not found: %s", md_path)
            return MinerUParseError(
                source_path=source_path,
                error_code="OUTPUT_NOT_FOUND",
                message=f"MinerU output .md not found at: {md_path}",
            )

        try:
            markdown_content = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            logger.warning(
                "UTF-8 decode failed for '%s', retrying with errors='replace': %s",
                md_path,
                exc,
            )
            markdown_content = md_path.read_text(encoding="utf-8", errors="replace")

        table_count = _count_tables_in_markdown(markdown_content)
        page_count = markdown_content.count("\n---\n") + 1

        logger.info(
            "Parsed '%s': %d chars, %d tables, ~%d pages",
            source_path.name,
            len(markdown_content),
            table_count,
            page_count,
        )

        return MinerUParseResult(
            source_path=source_path,
            markdown_content=markdown_content,
            output_dir=output_dir,
            page_count=page_count,
            table_count=table_count,
        )
