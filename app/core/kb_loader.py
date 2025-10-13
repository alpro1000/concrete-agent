"""Utility for loading structured knowledge base datasets."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict
from xml.etree import ElementTree

from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """Load JSON and XML datasets from the knowledge base directory."""

    def __init__(self, kb_root: Path) -> None:
        self.kb_root = Path(kb_root)
        self.datasets: Dict[str, Any] = {}

    def load_all(self) -> None:
        """Load all supported knowledge base files into memory."""
        if not self.kb_root.exists():
            logger.warning("Knowledge base directory does not exist: %s", self.kb_root)
            return

        for path in self.kb_root.rglob("*"):
            if not path.is_file():
                continue

            key = path.relative_to(self.kb_root).with_suffix("").as_posix()

            try:
                suffix = path.suffix.lower()
                if suffix == ".json":
                    with path.open(encoding="utf-8") as handle:
                        self.datasets[key] = json.load(handle)
                elif suffix == ".xml":
                    self.datasets[key] = self._load_xml_dataset(path)
                else:
                    continue

                logger.info("✅ Loaded KB: %s", key)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error(
                    "❌ Failed to load KB %s: %s", key, exc, exc_info=True
                )

    def get(self, key: str) -> Any:
        """Return dataset for the specified key if it exists."""
        return self.datasets.get(key)

    @staticmethod
    def _load_xml_dataset(path: Path) -> list[dict[str, Any]]:
        """Parse XML files storing <Polozka> elements into dictionaries."""
        tree = ElementTree.parse(path)
        root = tree.getroot()

        items: list[dict[str, Any]] = []
        for element in root.findall(".//Polozka"):
            item: dict[str, Any] = {}
            for child in element:
                text = child.text.strip() if child.text else None
                if child.tag == "jedn_cena" and text:
                    try:
                        text = float(text.replace(",", "."))
                    except ValueError:
                        logger.debug(
                            "Cannot convert jedn_cena value '%s' in %s", text, path
                        )
                item[child.tag] = text
            if item:
                items.append(item)
        return items


kb_loader = KnowledgeBaseLoader(Path(settings.KB_DIR))


__all__ = ["KnowledgeBaseLoader", "kb_loader"]
