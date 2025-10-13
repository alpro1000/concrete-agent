"""Generic XML parser for bill of quantities data."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List
from xml.etree import ElementTree

from app.core.registry import registry
from app.utils.position_normalizer import normalize_positions

logger = logging.getLogger(__name__)


class XMLParser:
    """Parse XML documents containing <Polozka> elements."""

    def parse(self, file_path: Path) -> Dict[str, Any]:
        logger.info("🧾 Parsing XML: %s", file_path.name)

        try:
            positions = self._extract_positions(file_path)
            normalized, stats = normalize_positions(positions, return_stats=True)

            logger.info(
                "✅ XML parsed: %s valid positions (raw=%s, skipped=%s)",
                stats["normalized_total"],
                stats["raw_total"],
                stats["skipped_total"],
            )

            return {
                "document_info": {
                    "filename": file_path.name,
                    "format": "xml",
                },
                "positions": normalized,
                "diagnostics": stats,
            }
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("❌ XML parsing failed: %s", exc, exc_info=True)
            return {
                "document_info": {
                    "filename": file_path.name,
                    "format": "xml",
                    "error": str(exc),
                },
                "positions": [],
                "diagnostics": {
                    "raw_total": 0,
                    "normalized_total": 0,
                    "skipped_total": 0,
                },
            }

    @staticmethod
    def _extract_positions(file_path: Path) -> List[Dict[str, Any]]:
        tree = ElementTree.parse(file_path)
        root = tree.getroot()

        positions: List[Dict[str, Any]] = []

        for element in root.findall(".//Polozka"):
            position: Dict[str, Any] = {}
            for child in element:
                value = child.text.strip() if child.text else None
                position[child.tag] = value

            if position:
                positions.append(position)

        return positions


registry.register_parser("xml", XMLParser)


__all__ = ["XMLParser"]
