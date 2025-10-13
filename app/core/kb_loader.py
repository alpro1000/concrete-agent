"""Knowledge base loader utilities."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """Load JSON knowledge base files recursively."""

    def __init__(self, kb_root: Path) -> None:
        self.kb_root = Path(kb_root)
        self.datasets: Dict[str, Any] = {}

    def load_all(self) -> None:
        """Load every JSON file under the knowledge base root."""
        if not self.kb_root.exists():
            logger.warning("Knowledge base directory does not exist: %s", self.kb_root)
            return

        for json_file in self.kb_root.rglob("*.json"):
            key = json_file.relative_to(self.kb_root).with_suffix("").as_posix()
            try:
                with json_file.open(encoding="utf-8") as handle:
                    self.datasets[key] = json.load(handle)
                logger.info("✅ Loaded KB: %s", key)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("❌ Failed to load KB %s: %s", key, exc, exc_info=True)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Return dataset by key if it exists."""
        return self.datasets.get(key, default)


kb_loader: KnowledgeBaseLoader = KnowledgeBaseLoader(Path(settings.KB_DIR))


def init_kb_loader(kb_root: Optional[Path] = None) -> KnowledgeBaseLoader:
    """Initialise the global knowledge base loader and populate datasets."""
    global kb_loader

    if kb_root is not None and kb_loader.kb_root != Path(kb_root):
        kb_loader = KnowledgeBaseLoader(Path(kb_root))

    if not kb_loader.datasets:
        kb_loader.load_all()

    return kb_loader


__all__ = ["KnowledgeBaseLoader", "kb_loader", "init_kb_loader"]
