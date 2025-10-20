from __future__ import annotations

"""PDF extraction reasoner wiring for configurable system prompts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.core.claude_client import ClaudeClient

try:
    from app.prompts.pdf_extraction_system_prompt_v2_1 import (
        PDF_EXTRACTION_SYSTEM_PROMPT_V2_1_COMPLETE,
    )
except ImportError:  # pragma: no cover - generated module may not exist during packaging
    PDF_EXTRACTION_SYSTEM_PROMPT_V2_1_COMPLETE = ""

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "pdf_extractor_config.yaml"
)
LEGACY_SYSTEM_PROMPT = "Legacy PDF extraction prompt v1"

__all__ = ["PDFExtractionReasonerV2_1", "load_prompt_version"]


@dataclass
class PDFExtractionReasonerV2_1:
    """Reasoner wrapper that injects the appropriate system prompt."""

    claude_client: ClaudeClient
    config_path: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.config_path is None:
            self.config_path = DEFAULT_CONFIG_PATH
        else:
            self.config_path = Path(self.config_path)
        self._cached_prompt_version: Optional[str] = None

    def run(self, document_payload: str, *, temperature: float = 0.2) -> Any:
        """Call Claude with the configured system prompt."""

        system_prompt = self._resolve_system_prompt()
        return self.claude_client.call(
            document_payload,
            system_prompt=system_prompt,
            temperature=temperature,
        )

    def _resolve_system_prompt(self) -> str:
        version = self._get_prompt_version()
        if version == "v2.1" and PDF_EXTRACTION_SYSTEM_PROMPT_V2_1_COMPLETE:
            return PDF_EXTRACTION_SYSTEM_PROMPT_V2_1_COMPLETE
        return LEGACY_SYSTEM_PROMPT

    def _get_prompt_version(self) -> str:
        if self._cached_prompt_version is not None:
            return self._cached_prompt_version
        version = load_prompt_version(self.config_path)
        self._cached_prompt_version = version
        return version


def load_prompt_version(config_path: Path) -> str:
    """Extract the ``prompt_version`` value from the YAML configuration."""

    try:
        raw = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "legacy"

    lines = raw.splitlines()
    in_section = False
    section_indent: Optional[int] = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if not in_section:
            if stripped == "pdf_extractor_p1:":
                in_section = True
                section_indent = indent
            continue

        if section_indent is not None and indent <= section_indent:
            break

        if stripped.startswith("prompt_version:"):
            _, value = stripped.split(":", 1)
            value = value.strip()
            if value and value[0] in {'"', "'"} and value[-1] == value[0]:
                value = value[1:-1]
            return value or "legacy"

    return "legacy"
