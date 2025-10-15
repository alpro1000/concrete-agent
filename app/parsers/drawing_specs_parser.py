"""Utility to extract technical specifications from drawing PDFs.

The parser relies on :mod:`pdfplumber` – the same backend that powers the
``PDFParser`` used for cost documents – to keep the behaviour consistent across
the pipeline.  It scans each page line-by-line and looks for typical technical
markers such as concrete classes (``C30/37``), reinforcement grades (``B500B``)
and exposure classes (``XC3``, ``XF2`` …).  Whenever a line contains a marker
the parser emits a lightweight specification record that will later be used for
position enrichment.

Each specification record contains:

``file``
    Source drawing filename.
``page``
    Page number in the PDF (1-based).
``anchor``
    The strongest marker detected in the line (used for matching).
``text``
    Full line text for human inspection.
``confidence``
    Heuristic confidence score (0–1) based on the amount of technical data
    detected.
``technical_specs``
    Structured data extracted from the line (concrete class, exposures, unit …).

The module is intentionally deterministic – no ML/OCR is involved – which makes
it suitable for background processing and caching.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DrawingSpecification:
    """Parsed specification snippet coming from a drawing."""

    file: str
    page: int
    anchor: str
    text: str
    confidence: float
    technical_specs: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serialisable representation."""

        return {
            "file": self.file,
            "page": self.page,
            "anchor": self.anchor,
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "technical_specs": dict(self.technical_specs),
        }


class DrawingSpecsParser:
    """Parse PDF drawings and extract technical specification snippets."""

    # Regex snippets used as anchors.
    CONCRETE_PATTERN = re.compile(r"C\d{2}/\d{2}", re.IGNORECASE)
    REINFORCEMENT_PATTERN = re.compile(r"B\d{3}[A-Z]?", re.IGNORECASE)
    EXPOSURE_PATTERN = re.compile(r"X[ACDFMS][0-9](?:[AB])?", re.IGNORECASE)
    UNIT_PATTERN = re.compile(r"\b(m3|m2|m|kg|ks|t|m\s*3|m\s*2)\b", re.IGNORECASE)

    ADDITIONAL_MARKERS = (
        "vodostavebni",
        "vodostavební",
        "mrazuvzd",
        "beton",
        "výztuž",
        "vyztuz",
    )

    def parse_files(self, drawing_files: Iterable[Dict[str, object]]) -> Dict[str, object]:
        """Parse all provided drawing files.

        Parameters
        ----------
        drawing_files:
            Iterable of dictionaries coming from :func:`WorkflowA._resolve_uploads`.

        Returns
        -------
        dict
            Dictionary with parsed specifications and diagnostics.
        """

        specifications: List[DrawingSpecification] = []
        diagnostics = {"files_processed": 0, "specifications_found": 0, "errors": []}

        for file_meta in drawing_files:
            if not file_meta.get("exists"):
                continue

            file_path = Path(str(file_meta.get("path")))
            if file_path.suffix.lower() != ".pdf":
                logger.debug("Skipping non-PDF drawing: %s", file_path)
                continue

            try:
                specs = self._parse_single_pdf(file_path)
            except Exception as exc:  # noqa: BLE001 - logged for diagnostics
                logger.exception("Failed to parse drawing %s: %s", file_path.name, exc)
                diagnostics["errors"].append(
                    {
                        "file": file_path.name,
                        "error": str(exc),
                    }
                )
                continue

            if specs:
                specifications.extend(specs)

            diagnostics["files_processed"] += 1
            diagnostics["specifications_found"] += len(specs)

        logger.info(
            "Parsed %s drawing(s); collected %s technical specification markers",
            diagnostics["files_processed"],
            diagnostics["specifications_found"],
        )

        return {
            "specifications": [spec.to_dict() for spec in specifications],
            "diagnostics": diagnostics,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_single_pdf(self, file_path: Path) -> List[DrawingSpecification]:
        """Extract specifications from a single PDF drawing."""

        logger.info("📐 Analysing drawing %s", file_path.name)
        collected: List[DrawingSpecification] = []

        with pdfplumber.open(file_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text:
                    continue

                for line in text.splitlines():
                    line = line.strip()
                    if len(line) < 6:
                        continue

                    spec = self._line_to_spec(file_path.name, page_index, line)
                    if spec:
                        collected.append(spec)

        return collected

    def _line_to_spec(
        self, filename: str, page: int, line: str
    ) -> Optional[DrawingSpecification]:
        """Convert a single line of text into a specification if possible."""

        concrete_class = self._first_match(self.CONCRETE_PATTERN, line)
        reinforcement_grade = self._first_match(self.REINFORCEMENT_PATTERN, line)
        exposures = self._unique_matches(self.EXPOSURE_PATTERN, line)
        unit = self._first_match(self.UNIT_PATTERN, line)
        anchor_candidates = [marker for marker in [concrete_class, reinforcement_grade] if marker]

        if not anchor_candidates:
            # Check for general markers to avoid missing textual specs.
            lower_line = line.lower()
            if not any(marker in lower_line for marker in self.ADDITIONAL_MARKERS):
                return None

            anchor_candidates.append(self._derive_anchor_from_text(line))

        anchor = anchor_candidates[0]
        if not anchor:
            return None

        technical_specs: Dict[str, object] = {}
        if concrete_class:
            technical_specs["concrete_class"] = concrete_class.upper()
        if exposures:
            technical_specs["exposure"] = sorted({exposure.upper() for exposure in exposures})
        if reinforcement_grade:
            technical_specs["reinforcement"] = reinforcement_grade.upper()
        if unit:
            normalised_unit = unit.replace(" ", "").lower()
            technical_specs["unit"] = normalised_unit

        # Calculate heuristic confidence score.
        confidence = 0.55
        if concrete_class:
            confidence += 0.2
        if exposures:
            confidence += 0.15
        if reinforcement_grade:
            confidence += 0.1
        if unit:
            confidence += 0.05

        confidence = min(confidence, 0.98)

        return DrawingSpecification(
            file=filename,
            page=page,
            anchor=anchor.upper(),
            text=line,
            confidence=confidence,
            technical_specs=technical_specs,
        )

    @staticmethod
    def _first_match(pattern: re.Pattern[str], text: str) -> Optional[str]:
        match = pattern.search(text)
        return match.group(0) if match else None

    @staticmethod
    def _unique_matches(pattern: re.Pattern[str], text: str) -> List[str]:
        return list({match.group(0) for match in pattern.finditer(text)})

    @staticmethod
    def _derive_anchor_from_text(text: str) -> str:
        """Fallback anchor derived from the most salient token in the text."""

        # Pick the longest alphanumeric token as a best-effort anchor.
        tokens = re.findall(r"[A-Za-z0-9/]+", text)
        tokens.sort(key=len, reverse=True)
        return tokens[0].upper() if tokens else text[:20].upper()


__all__ = ["DrawingSpecsParser", "DrawingSpecification"]

