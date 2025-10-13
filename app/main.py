"""Dynamic entry point for the document processing pipeline."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as main_router
from app.core import position_enricher  # noqa: F401  # ensure registration
from app.core import resource_calculator  # noqa: F401  # ensure registration
from app.core.config import settings
from app.core.kb_loader import kb_loader
from app.core.registry import registry
from app.parsers import excel_parser, pdf_parser, xml_parser  # noqa: F401

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
    """Run the dynamic document processing pipeline."""
    if not kb_loader.datasets:
        kb_loader.load_all()

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

        positions = result.get("positions") or []
        if positions:
            all_positions.extend(positions)

        specifications = result.get("specifications") or []
        if name == "pdf" and specifications:
            pdf_specs.extend(specifications)

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


# --------------------------------------------------------------------------------------
# FastAPI application setup (kept for API compatibility and tests)
# --------------------------------------------------------------------------------------

app = FastAPI(
    title="Czech Building Audit System",
    description="AI-powered construction audit system for Czech market",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(main_router)

web_dir = settings.BASE_DIR / "web"
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")
    logger.info("📁 Static files mounted: %s", web_dir)


@app.on_event("startup")
async def startup_event() -> None:
    """Log startup information and warm up the knowledge base."""

    logger.info("=" * 80)
    logger.info("🚀 Czech Building Audit System Starting...")
    logger.info("=" * 80)
    logger.info("📂 Base directory: %s", settings.BASE_DIR)
    logger.info("📂 Data directory: %s", settings.DATA_DIR)
    logger.info("📚 KB directory: %s", settings.KB_DIR)
    logger.info("📝 Prompts directory: %s", settings.PROMPTS_DIR)
    logger.info("📊 Logs directory: %s", settings.LOGS_DIR)
    logger.info("-" * 80)
    logger.info("⚙️  Workflow A enabled: %s", settings.ENABLE_WORKFLOW_A)
    logger.info("⚙️  Workflow B enabled: %s", settings.ENABLE_WORKFLOW_B)
    logger.info("⚙️  KROS matching: %s", settings.ENABLE_KROS_MATCHING)
    logger.info("-" * 80)

    if not kb_loader.datasets:
        kb_loader.load_all()

    logger.info("✅ Knowledge Base loaded: %s datasets", len(kb_loader.datasets))

    for key, dataset in kb_loader.datasets.items():
        if isinstance(dataset, list):
            logger.info("   - %s: %s items", key, len(dataset))
        elif isinstance(dataset, dict):
            logger.info("   - %s: %s keys", key, len(dataset))
        else:
            logger.info("   - %s: %s", key, type(dataset).__name__)

    logger.info("=" * 80)
    logger.info("✅ System ready!")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Log application shutdown."""

    logger.info("🛑 Czech Building Audit System shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
