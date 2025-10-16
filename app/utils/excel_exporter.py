"""Excel exporter for audit results."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.config import settings
from app.utils.audit_contracts import ensure_audit_contract

logger = logging.getLogger(__name__)


class AuditExcelExporter:
    """Create a workbook with audit summary and full position listing."""

    SUMMARY_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    HEADER_FILL = PatternFill(start_color="B4C7E7", end_color="B4C7E7", fill_type="solid")
    CLASS_COLORS = {
        "GREEN": PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
        "AMBER": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
        "RED": PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
    }

    def __init__(self) -> None:
        self.workbook = openpyxl.Workbook()
        # Remove default sheet to control ordering explicitly
        default_sheet = self.workbook.active
        self.workbook.remove(default_sheet)

    async def export(self, project: Dict[str, Any], output_path: Path | None = None) -> Path:
        audit_results, source = _resolve_audit_results(project)

        self._create_summary_sheet(project, audit_results)
        self._create_positions_sheet(audit_results)

        if output_path is None:
            export_dir = settings.DATA_DIR / "exports" / project["project_id"]
            export_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{project['project_name']}_audit_{timestamp}.xlsx"
            output_path = export_dir / filename

        self.workbook.save(output_path)

        logger.info(
            "excel_export: positions=%s totals={g:%s,a:%s,r:%s} source=%s",
            audit_results.get("total_positions", 0),
            audit_results.get("green", 0),
            audit_results.get("amber", 0),
            audit_results.get("red", 0),
            source,
        )

        return output_path

    # ------------------------------------------------------------------
    # Sheet builders
    # ------------------------------------------------------------------

    def _create_summary_sheet(self, project: Dict[str, Any], audit_results: Dict[str, Any]) -> None:
        sheet = self.workbook.create_sheet("Summary", 0)
        sheet["A1"] = "AUDIT SUMMARY"
        sheet["A1"].font = Font(bold=True, color="FFFFFF", size=15)
        sheet["A1"].fill = self.SUMMARY_FILL
        sheet.merge_cells("A1:D1")

        info_rows = [
            ("Project ID", project.get("project_id")),
            ("Project Name", project.get("project_name")),
            ("Workflow", project.get("workflow")),
            ("Generated", datetime.now().isoformat(timespec="seconds")),
            ("Enrichment", "Enabled" if project.get("enable_enrichment") else "Disabled"),
        ]

        row = 3
        for label, value in info_rows:
            sheet[f"A{row}"] = label
            sheet[f"A{row}"].font = Font(bold=True)
            sheet[f"B{row}"] = value
            row += 1

        row += 1
        sheet[f"A{row}"] = "Totals"
        sheet[f"A{row}"].font = Font(bold=True)
        sheet[f"A{row}"].fill = self.HEADER_FILL
        sheet.merge_cells(f"A{row}:D{row}")
        row += 1

        totals = [
            ("Total positions", audit_results.get("total_positions", 0), None),
            ("GREEN", audit_results.get("green", 0), self.CLASS_COLORS["GREEN"]),
            ("AMBER", audit_results.get("amber", 0), self.CLASS_COLORS["AMBER"]),
            ("RED", audit_results.get("red", 0), self.CLASS_COLORS["RED"]),
        ]

        total_positions = audit_results.get("total_positions", 0) or 1
        for label, value, fill in totals:
            sheet[f"A{row}"] = label
            sheet[f"A{row}"].font = Font(bold=True)
            sheet[f"B{row}"] = value
            if fill:
                sheet[f"B{row}"].fill = fill
            percentage = (value / total_positions) * 100 if total_positions else 0
            sheet[f"C{row}"] = f"{percentage:.1f}%"
            row += 1

        for col in ("A", "B", "C", "D"):
            sheet.column_dimensions[col].width = 24

    def _create_positions_sheet(self, audit_results: Dict[str, Any]) -> None:
        sheet = self.workbook.create_sheet("Positions")
        headers = [
            "Position ID",
            "Code",
            "Description",
            "Unit",
            "Quantity",
            "Section",
            "Classification",
            "Notes",
            "Match",
            "Score",
            "Evidence",
        ]

        for column, title in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=column)
            cell.value = title
            cell.font = Font(bold=True, color="000000")
            cell.fill = self.HEADER_FILL
            cell.alignment = Alignment(horizontal="center")

        for row_index, position in enumerate(audit_results.get("positions", []), start=2):
            sheet.cell(row=row_index, column=1).value = position.get("position_id")
            sheet.cell(row=row_index, column=2).value = position.get("code")
            sheet.cell(row=row_index, column=3).value = position.get("description")
            sheet.cell(row=row_index, column=4).value = position.get("unit")
            sheet.cell(row=row_index, column=5).value = position.get("quantity")
            sheet.cell(row=row_index, column=6).value = position.get("section")

            classification = (position.get("classification") or "").upper()
            class_cell = sheet.cell(row=row_index, column=7)
            class_cell.value = classification
            class_cell.fill = self.CLASS_COLORS.get(classification, PatternFill())

            sheet.cell(row=row_index, column=8).value = position.get("notes")
            sheet.cell(row=row_index, column=8).alignment = Alignment(wrap_text=True, vertical="top")

            enrichment = position.get("enrichment") or {}
            match = enrichment.get("match", "none")
            sheet.cell(row=row_index, column=9).value = match
            sheet.cell(row=row_index, column=10).value = enrichment.get("score", 0.0)

            evidence_text = _format_evidence(enrichment.get("evidence") or [])
            evidence_cell = sheet.cell(row=row_index, column=11)
            evidence_cell.value = evidence_text
            evidence_cell.alignment = Alignment(wrap_text=True, vertical="top")

        column_widths = [18, 14, 50, 10, 12, 18, 14, 40, 12, 10, 60]
        for index, width in enumerate(column_widths, start=1):
            sheet.column_dimensions[get_column_letter(index)].width = width

        sheet.freeze_panes = "A2"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _format_evidence(evidence: List[Dict[str, Any]]) -> str:
    formatted: List[str] = []
    for item in evidence[: settings.ENRICH_MAX_EVIDENCE]:
        if not isinstance(item, dict):
            continue
        parts: List[str] = []
        source = item.get("source")
        if source:
            parts.append(str(source))
        reason = item.get("reason")
        if reason:
            parts.append(str(reason))
        snippet = item.get("snippet")
        if snippet:
            snippet_text = str(snippet).strip()
            if snippet_text:
                parts.append(f'"{snippet_text[:160]}"')
        if parts:
            formatted.append(" | ".join(parts))
    return "\n".join(formatted)


def _resolve_audit_results(project: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    raw_results = project.get("audit_results") or {}
    fallback = (
        raw_results.get("positions")
        or project.get("positions")
        or project.get("positions_preview")
        or []
    )

    normalised, changed = ensure_audit_contract(raw_results, fallback)
    source = "migrated" if changed else "normalized"

    if not normalised.get("positions"):
        cached_positions = _load_positions_from_cache(project)
        if cached_positions:
            updated_payload = dict(normalised)
            updated_payload["positions"] = cached_positions
            normalised, _ = ensure_audit_contract(updated_payload, cached_positions)
            source = "migrated"

    return normalised, source


def _resolve_cache_path(project: Dict[str, Any]) -> Path | None:
    raw_path = project.get("cache_path") or project.get("cache")
    if not raw_path:
        return None

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = settings.DATA_DIR / candidate

    if candidate.exists():
        return candidate

    fallback = settings.DATA_DIR / "projects" / candidate.name
    if fallback.exists():
        return fallback

    return None


def _load_positions_from_cache(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    cache_path = _resolve_cache_path(project)
    if not cache_path:
        return []

    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        logger.warning("Unable to read project cache at %s", cache_path)
        return []

    positions = (
        payload.get("audit_results", {}).get("positions")
        or payload.get("positions")
        or []
    )

    normalised, _ = ensure_audit_contract({"positions": positions}, positions)
    return normalised.get("positions", [])


async def export_enriched_results(project: Dict[str, Any]) -> Path:
    exporter = AuditExcelExporter()
    return await exporter.export(project)
