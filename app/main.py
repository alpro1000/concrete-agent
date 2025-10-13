import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as main_router
from app.core.config import settings
from app.parsers.xml_parser import XMLParser
from app.parsers.excel_parser import ExcelParser
from app.parsers.pdf_parser import PDFParser
from app.core.position_enricher import PositionEnricher
from app.core.resource_calculator import ResourceCalculator


def _find_input_file(patterns: List[str]) -> Optional[Path]:
    raw_dir = Path(settings.DATA_DIR) / "raw"
    for pattern in patterns:
        matches = sorted(raw_dir.rglob(pattern))
        if matches:
            return matches[0]
    return None


def save_reports(resources: Dict[str, Any]) -> None:
    results_dir = Path(settings.DATA_DIR) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / "resources.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(resources, handle, ensure_ascii=False, indent=2)


async def main() -> None:
    xml_file = _find_input_file(["*.xml"])
    excel_file = _find_input_file(["*.xlsx", "*.xls"])
    pdf_file = _find_input_file(["*.pdf"])

    xml_positions = XMLParser().parse(xml_file) if xml_file else []
    excel_positions = ExcelParser().parse(excel_file) if excel_file else []
    pdf_specs = PDFParser().parse(pdf_file) if pdf_file else []

    all_positions = xml_positions + excel_positions
    enricher = PositionEnricher()
    enriched = await enricher.enrich_positions(all_positions, pdf_specs)
    resources = ResourceCalculator().calculate(enriched)
    save_reports(resources)


app = FastAPI(title="Czech Building Audit System")
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


if __name__ == "__main__":
    asyncio.run(main())
