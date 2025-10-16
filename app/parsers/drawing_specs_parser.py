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

import json
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
    STEEL_PATTERN = re.compile(r"S\d{3}", re.IGNORECASE)
    EXPOSURE_PATTERN = re.compile(r"X[ACDFS][0-9](?:[AB])?", re.IGNORECASE)
    UNIT_PATTERN = re.compile(r"\b(m3|m2|m|kg|ks|t|m\s*3|m\s*2)\b", re.IGNORECASE)
    MESH_PATTERN = re.compile(
        r"(?:Ø|⌀)\s*\d{1,2}\s*@?\s*\d{2,3}|\b\d{1,2}\s*@\s*\d{2,3}\b",
        re.IGNORECASE,
    )
    RADIUS_PATTERN = re.compile(r"R\s*=\s*\d+(?:[.,]\d+)?", re.IGNORECASE)
    RADIUS_COMPACT_PATTERN = re.compile(r"R\s*\d+(?:[.,]\d+)?", re.IGNORECASE)
    COVER_PATTERN = re.compile(r"kryt[íi]\s*\d{1,3}\s*mm", re.IGNORECASE)
    COMPOSITE_PATTERN = re.compile(r"\b(\d{3})[-\s\/]{0,2}(\d{2})[-\s\/]{0,2}(\d{3})\b")

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
        pattern_hits = {
            "concrete": 0,
            "exposure": 0,
            "steel": 0,
            "mesh": 0,
            "cover": 0,
            "radii": 0,
            "composite": 0,
        }

        for file_meta in drawing_files:
            if not file_meta.get("exists"):
                continue

            file_path = Path(str(file_meta.get("path")))
            if file_path.suffix.lower() != ".pdf":
                logger.debug("Skipping non-PDF drawing: %s", file_path)
                continue

            try:
                specs = self._parse_single_pdf(file_path, pattern_hits)
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

        logger.debug("patterns_hit=%s", json.dumps(pattern_hits, ensure_ascii=False))

        return {
            "specifications": [spec.to_dict() for spec in specifications],
            "diagnostics": diagnostics,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_single_pdf(
        self, file_path: Path, pattern_hits: Dict[str, int]
    ) -> List[DrawingSpecification]:
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

                    spec = self._line_to_spec(file_path.name, page_index, line, pattern_hits)
                    if spec:
                        collected.append(spec)

        return collected

    def _line_to_spec(
        self, filename: str, page: int, line: str, pattern_hits: Dict[str, int]
    ) -> Optional[DrawingSpecification]:
        """Convert a single line of text into a specification if possible."""

        concrete_matches = [match.upper() for match in self._unique_matches(self.CONCRETE_PATTERN, line)]
        reinforcement_matches = [
            match.upper() for match in self._unique_matches(self.REINFORCEMENT_PATTERN, line)
        ]
        steel_matches = [match.upper() for match in self._unique_matches(self.STEEL_PATTERN, line)]
        exposure_matches = [
            match.upper() for match in self._unique_matches(self.EXPOSURE_PATTERN, line)
        ]
        mesh_matches = self._collect_mesh(line)
        radii_matches = self._collect_radii(line)
        cover_matches = self._collect_cover(line)
        composite_matches = self._collect_composite_codes(line)
        unit = self._first_match(self.UNIT_PATTERN, line)

        if concrete_matches:
            pattern_hits["concrete"] += len(concrete_matches)
        if exposure_matches:
            pattern_hits["exposure"] += len(exposure_matches)
        steel_total = len(reinforcement_matches) + len(steel_matches)
        if steel_total:
            pattern_hits["steel"] += steel_total
        if mesh_matches:
            pattern_hits["mesh"] += len(mesh_matches)
        if cover_matches:
            pattern_hits["cover"] += len(cover_matches)
        if radii_matches:
            pattern_hits["radii"] += len(radii_matches)
        if composite_matches:
            pattern_hits["composite"] += len(composite_matches)

        anchor_candidates: List[str] = []
        anchor_candidates.extend(concrete_matches)
        anchor_candidates.extend(reinforcement_matches)
        anchor_candidates.extend(steel_matches)
        anchor_candidates.extend(mesh_matches)
        anchor_candidates.extend(exposure_matches)
        anchor_candidates.extend(composite_matches)

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
        if concrete_matches:
            concrete_unique = sorted(dict.fromkeys(concrete_matches))
            technical_specs["concrete_class"] = concrete_unique[0]
            if len(concrete_unique) > 1:
                technical_specs["concrete_classes"] = concrete_unique
        if exposure_matches:
            technical_specs["exposure"] = sorted(dict.fromkeys(exposure_matches))
        if reinforcement_matches:
            reinforcement_unique = sorted(dict.fromkeys(reinforcement_matches))
            technical_specs["reinforcement"] = reinforcement_unique[0]
            if len(reinforcement_unique) > 1:
                technical_specs["reinforcement_options"] = reinforcement_unique
        if steel_matches:
            steel_unique = sorted(dict.fromkeys(steel_matches))
            technical_specs["steel_grade"] = steel_unique[0]
            if len(steel_unique) > 1:
                technical_specs["steel_grade_options"] = steel_unique
        if mesh_matches:
            technical_specs["reinforcement_mesh"] = mesh_matches
        if radii_matches:
            technical_specs["radii"] = radii_matches
        if cover_matches:
            technical_specs["concrete_cover"] = cover_matches
        if composite_matches:
            technical_specs["composite_codes"] = composite_matches
        if unit:
            normalised_unit = unit.replace(" ", "").lower()
            technical_specs["unit"] = normalised_unit

        # Calculate heuristic confidence score.
        confidence = 0.55
        if concrete_matches:
            confidence += 0.2
        if exposure_matches:
            confidence += 0.15
        if reinforcement_matches or steel_matches:
            confidence += 0.1
        if mesh_matches or radii_matches:
            confidence += 0.05
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

    @classmethod
    def _collect_mesh(cls, text: str) -> List[str]:
        values: Dict[str, str] = {}
        for match in cls.MESH_PATTERN.finditer(text):
            normalised = cls._normalise_mesh(match.group(0))
            if normalised:
                values.setdefault(normalised, normalised)
        return sorted(values.values())

    @staticmethod
    def _normalise_mesh(value: str) -> str:
        cleaned = value.upper().replace(" ", "")
        cleaned = cleaned.replace("⌀", "Ø")
        digits = re.findall(r"\d{1,3}", cleaned)
        if len(digits) < 2:
            return ""
        diameter, spacing = digits[0], digits[1]
        return f"Ø{diameter}@{spacing}"

    @classmethod
    def _collect_radii(cls, text: str) -> List[str]:
        values: Dict[str, str] = {}
        for pattern in (cls.RADIUS_PATTERN, cls.RADIUS_COMPACT_PATTERN):
            for match in pattern.finditer(text):
                digits = re.search(r"\d+(?:[.,]\d+)?", match.group(0))
                if not digits:
                    continue
                normalised = digits.group(0).replace(",", ".")
                values.setdefault(normalised, f"R={normalised}")
        return sorted(values.values())

    @classmethod
    def _collect_cover(cls, text: str) -> List[Dict[str, str]]:
        covers: Dict[str, Dict[str, str]] = {}
        for match in cls.COVER_PATTERN.finditer(text):
            raw_value = match.group(0).strip()
            digits = re.search(r"\d{1,3}", raw_value)
            if not digits:
                continue
            number = digits.group(0)
            normalised = f"kryti {number} mm"
            covers.setdefault(
                number,
                {
                    "raw": raw_value,
                    "normalized": normalised,
                },
            )
        return list(covers.values())

    @classmethod
    def _collect_composite_codes(cls, text: str) -> List[str]:
        codes: Dict[str, str] = {}
        for match in cls.COMPOSITE_PATTERN.finditer(text):
            parts = match.groups()
            if not parts:
                continue
            leading, middle, trailing = parts
            canonical = f"{leading}/{middle}-{trailing}"
            codes.setdefault(canonical, canonical)
        return sorted(codes.values())

    @staticmethod
    def _derive_anchor_from_text(text: str) -> str:
        """Fallback anchor derived from the most salient token in the text."""

        # Pick the longest alphanumeric token as a best-effort anchor.
        tokens = re.findall(r"[A-Za-z0-9/]+", text)
        tokens.sort(key=len, reverse=True)
        return tokens[0].upper() if tokens else text[:20].upper()


__all__ = ["DrawingSpecsParser", "DrawingSpecification"]

