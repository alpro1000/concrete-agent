"""Asynchronous entry point for the document processing pipeline."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List

from app.core.config import settings
from app.core.kb_loader import init_kb_loader
from app.core.registry import registry

# Import components so they register themselves via the registry.
from app.core import position_enricher  # noqa: F401  pylint: disable=unused-import
from app.core import resource_calculator  # noqa: F401  pylint: disable=unused-import
from app.parsers import excel_parser  # noqa: F401  pylint: disable=unused-import
from app.parsers import pdf_parser  # noqa: F401  pylint: disable=unused-import

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

PARSER_PATTERNS: Dict[str, Iterable[str]] = {
    "excel": ("*.xlsx", "*.xls"),
    "pdf": ("*.pdf",),
    "xml": ("*.xml",),
}


def input_file_for(parser_name: str) -> Path:
    """Resolve an input file for the given parser name."""
    data_dir = Path(settings.DATA_DIR)

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    patterns = PARSER_PATTERNS.get(parser_name)
    if not patterns:
        raise FileNotFoundError(f"No file patterns configured for parser '{parser_name}'")

    for pattern in patterns:
        matches = sorted(data_dir.rglob(pattern))
        if matches:
            return matches[0]

    raise FileNotFoundError(
        f"No input files found for parser '{parser_name}' in {data_dir}"
    )


def save_reports(reports: Dict[str, Dict[str, object]]) -> None:
    """Persist pipeline reports to the results directory."""
    results_dir = Path(settings.DATA_DIR) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    output_path = results_dir / "pipeline_reports.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(reports, handle, ensure_ascii=False, indent=2)

    logger.info("Saved pipeline reports to %s", output_path)


async def main() -> None:
    """Run the document processing pipeline."""
    kb = init_kb_loader()
    logger.info("Knowledge base datasets loaded: %s", len(kb.datasets))

    all_positions: List[Dict[str, object]] = []
    pdf_specs: List[Dict[str, object]] = []

    for name, parser in registry.parsers.items():
        try:
            source = input_file_for(name)
        except FileNotFoundError as exc:
            logger.warning("Skipping parser '%s': %s", name, exc)
            continue

        logger.info("Parsing %s with '%s' parser", source.name, name)
        result = parser.parse(source)

        positions = result.get("positions", [])
        if positions:
            all_positions.extend(positions)

        specs = result.get("specifications") or []
        if specs:
            pdf_specs.extend(specs)

    enriched_positions = list(all_positions)

    for name, enricher in registry.enrichers.items():
        logger.info("Running enricher '%s'", name)
        enriched_positions = await enricher.enrich_positions(
            enriched_positions, pdf_specs
        )

    reports: Dict[str, Dict[str, object]] = {}
    for name, calculator in registry.calculators.items():
        logger.info("Running calculator '%s'", name)
        reports[name] = calculator.calculate(enriched_positions)

    save_reports(reports)


if __name__ == "__main__":
    asyncio.run(main())
