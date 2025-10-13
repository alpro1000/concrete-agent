"""Component registry for document processing pipeline.

The registry keeps instantiated parser, enricher and calculator components
so that the document processing workflow can dynamically iterate over
available capabilities without touching the orchestrator code.
"""
from __future__ import annotations

from typing import Any, Dict


class ComponentRegistry:
    """Runtime registry of processing components."""

    def __init__(self) -> None:
        self.parsers: Dict[str, Any] = {}
        self.enrichers: Dict[str, Any] = {}
        self.calculators: Dict[str, Any] = {}

    def register_parser(self, name: str, cls: type[Any]) -> None:
        """Register a parser implementation under a unique name."""
        self.parsers[name] = cls()

    def register_enricher(self, name: str, cls: type[Any]) -> None:
        """Register an enricher implementation under a unique name."""
        self.enrichers[name] = cls()

    def register_calculator(self, name: str, cls: type[Any]) -> None:
        """Register a calculator implementation under a unique name."""
        self.calculators[name] = cls()


registry = ComponentRegistry()

__all__ = ["registry", "ComponentRegistry"]
