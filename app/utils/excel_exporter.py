"""
Excel Exporter for Enriched Audit Results
Экспорт обогащенных результатов аудита в Excel с форматированием
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.core.config import settings

logger = logging.getLogger(__name__)


class EnrichedExcelExporter:
    """
    Export enriched audit results to formatted Excel file
    
    Creates workbook with multiple sheets:
    - Summary: Overall statistics
    - All Positions: Complete list with enrichment data
    - GREEN: Positions that passed
    - AMBER: Positions needing attention
    - RED: Positions with critical issues
    - Drawing Specs: All specifications found in drawings
    """
    
    # Colors for different classifications
    COLORS = {
        'GREEN': 'C6EFCE',
        'AMBER': 'FFEB9C',
        'RED': 'FFC7CE',
        'HEADER': '4472C4',
        'SUBHEADER': 'B4C7E7'
    }
    
    def __init__(self):
        self.workbook = None
        self.styles = self._create_styles()
    
    def _create_styles(self) -> Dict[str, Any]:
        """Create reusable styles"""
        return {
            'header': Font(bold=True, color='FFFFFF', size=12),
            'header_fill': PatternFill(start_color=self.COLORS['HEADER'], end_color=self.COLORS['HEADER'], fill_type='solid'),
            'subheader': Font(bold=True, size=11),
            'subheader_fill': PatternFill(start_color=self.COLORS['SUBHEADER'], end_color=self.COLORS['SUBHEADER'], fill_type='solid'),
            'green_fill': PatternFill(start_color=self.COLORS['GREEN'], end_color=self.COLORS['GREEN'], fill_type='solid'),
            'amber_fill': PatternFill(start_color=self.COLORS['AMBER'], end_color=self.COLORS['AMBER'], fill_type='solid'),
            'red_fill': PatternFill(start_color=self.COLORS['RED'], end_color=self.COLORS['RED'], fill_type='solid'),
            'border': Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            ),
            'center': Alignment(horizontal='center', vertical='center'),
            'wrap': Alignment(wrap_text=True, vertical='top')
        }
    
    async def export(
        self,
        project: Dict[str, Any],
        output_path: Path = None
    ) -> Path:
        """
        Export project results to Excel
        
        Args:
            project: Project dict with audit_results
            output_path: Optional output path
            
        Returns:
            Path to generated Excel file
        """
        logger.info(f"Exporting project {project['project_id']} to Excel...")
        
        # Create workbook
        self.workbook = openpyxl.Workbook()
        self.workbook.remove(self.workbook.active)  # Remove default sheet
        
        audit_results = _normalise_audit_results(project)
        
        # Create sheets
        self._create_summary_sheet(project, audit_results)
        self._create_all_positions_sheet(audit_results)
        self._create_classification_sheets(audit_results)
        
        # If enrichment was enabled, add drawing specs sheet
        if project.get('enable_enrichment'):
            self._create_drawing_specs_sheet(audit_results)
        
        # Determine output path
        if output_path is None:
            output_dir = settings.DATA_DIR / "exports" / project['project_id']
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{project['project_name']}_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Save workbook
        self.workbook.save(output_path)
        logger.info(f"✅ Excel exported to: {output_path}")
        
        return output_path

    def _create_summary_sheet(
        self,
        project: Dict[str, Any],
        audit_results: Dict[str, Any]
    ):
        """Create summary sheet with statistics"""
        sheet = self.workbook.create_sheet("Summary", 0)
        
        # Title
        sheet['A1'] = "AUDIT SUMMARY"
        sheet['A1'].font = Font(bold=True, size=16, color='FFFFFF')
        sheet['A1'].fill = self.styles['header_fill']
        sheet.merge_cells('A1:D1')
        
        row = 3
        
        # Project info
        sheet[f'A{row}'] = "Project Information"
        sheet[f'A{row}'].font = self.styles['subheader']
        sheet[f'A{row}'].fill = self.styles['subheader_fill']
        sheet.merge_cells(f'A{row}:D{row}')
        row += 1
        
        info_data = [
            ("Project ID:", project['project_id']),
            ("Project Name:", project['project_name']),
            ("Workflow:", project['workflow']),
            ("Completed:", project.get('completed_at', 'N/A')),
            ("Enrichment:", "Enabled" if project.get('enable_enrichment') else "Disabled")
        ]
        
        for label, value in info_data:
            sheet[f'A{row}'] = label
            sheet[f'B{row}'] = value
            sheet[f'A{row}'].font = Font(bold=True)
            row += 1
        
        row += 1
        
        # Classification statistics
        sheet[f'A{row}'] = "Classification"
        sheet[f'A{row}'].font = self.styles['subheader']
        sheet[f'A{row}'].fill = self.styles['subheader_fill']
        sheet.merge_cells(f'A{row}:D{row}')
        row += 1
        
        total = audit_results.get('total_positions', 0)
        green = audit_results.get('green', 0)
        amber = audit_results.get('amber', 0)
        red = audit_results.get('red', 0)
        
        classification_data = [
            ("Total Positions:", total, None),
            ("GREEN (All Good):", green, self.styles['green_fill']),
            ("AMBER (Needs Attention):", amber, self.styles['amber_fill']),
            ("RED (Critical Issues):", red, self.styles['red_fill'])
        ]

        for label, value, fill in classification_data:
            sheet[f'A{row}'] = label
            sheet[f'B{row}'] = value
            if total > 0:
                sheet[f'C{row}'] = f"{value / total * 100:.1f}%"
            sheet[f'A{row}'].font = Font(bold=True)
            if fill:
                sheet[f'B{row}'].fill = fill
                sheet[f'C{row}'].fill = fill
            row += 1

        row += 1

        schema_stats = audit_results.get('schema_validation') or {}
        if schema_stats:
            sheet[f'A{row}'] = "Schema Validation"
            sheet[f'A{row}'].font = self.styles['subheader']
            sheet[f'A{row}'].fill = self.styles['subheader_fill']
            sheet.merge_cells(f'A{row}:D{row}')
            row += 1

            schema_rows = [
                ("Input positions:", schema_stats.get('input_total', 0)),
                ("Valid after schema:", schema_stats.get('validated_total', 0)),
                ("Duplicates removed:", schema_stats.get('duplicates_removed', 0)),
                ("Invalid entries:", schema_stats.get('invalid_total', 0)),
            ]

            for label, value in schema_rows:
                sheet[f'A{row}'] = label
                sheet[f'B{row}'] = value
                sheet[f'A{row}'].font = Font(bold=True)
                row += 1

            row += 1

        # Enrichment statistics (if enabled)
        if project.get('enable_enrichment'):
            enrichment_stats = audit_results.get('enrichment_stats', {})
            
            sheet[f'A{row}'] = "Drawing Enrichment"
            sheet[f'A{row}'].font = self.styles['subheader']
            sheet[f'A{row}'].fill = self.styles['subheader_fill']
            sheet.merge_cells(f'A{row}:D{row}')
            row += 1
            
            matched = enrichment_stats.get('matched', 0)
            partial = enrichment_stats.get('partial', 0)
            unmatched = enrichment_stats.get('unmatched', 0)
            
            enrichment_data = [
                ("Matched:", matched, self.styles['green_fill']),
                ("Partial Match:", partial, self.styles['amber_fill']),
                ("Unmatched:", unmatched, self.styles['red_fill'])
            ]
            
            for label, value, fill in enrichment_data:
                sheet[f'A{row}'] = label
                sheet[f'B{row}'] = value
                if total > 0:
                    sheet[f'C{row}'] = f"{value / total * 100:.1f}%"
                sheet[f'A{row}'].font = Font(bold=True)
                sheet[f'B{row}'].fill = fill
                sheet[f'C{row}'].fill = fill
                row += 1
            
            row += 1
            
            # Validation statistics
            validation_stats = audit_results.get('validation_stats', {})
            
            sheet[f'A{row}'] = "Standards Validation (ČSN)"
            sheet[f'A{row}'].font = self.styles['subheader']
            sheet[f'A{row}'].fill = self.styles['subheader_fill']
            sheet.merge_cells(f'A{row}:D{row}')
            row += 1
            
            passed = validation_stats.get('passed', 0)
            warning = validation_stats.get('warning', 0)
            failed = validation_stats.get('failed', 0)
            no_specs = validation_stats.get('no_specs', 0)
            
            validation_data = [
                ("Passed:", passed, self.styles['green_fill']),
                ("Warnings:", warning, self.styles['amber_fill']),
                ("Failed:", failed, self.styles['red_fill']),
                ("No Specs:", no_specs, None)
            ]
            
            for label, value, fill in validation_data:
                sheet[f'A{row}'] = label
                sheet[f'B{row}'] = value
                if total > 0:
                    sheet[f'C{row}'] = f"{value / total * 100:.1f}%"
                sheet[f'A{row}'].font = Font(bold=True)
                if fill:
                    sheet[f'B{row}'].fill = fill
                    sheet[f'C{row}'].fill = fill
                row += 1
        
        # Auto-size columns
        for col in ['A', 'B', 'C', 'D']:
            sheet.column_dimensions[col].width = 25
    
    def _create_all_positions_sheet(self, audit_results: Dict[str, Any]):
        """Create sheet with all positions"""
        sheet = self.workbook.create_sheet("All Positions")
        
        # Headers
        headers = [
            "№", "Description", "Quantity", "Unit", "Code",
            "Classification", "Enrichment", "Validation",
            "Technical Specs", "Drawing Source", "Issues"
        ]
        
        for col_idx, header in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.styles['header']
            cell.fill = self.styles['header_fill']
            cell.alignment = self.styles['center']
            cell.border = self.styles['border']
        
        # Data rows
        positions = audit_results.get('positions', [])
        
        for row_idx, position in enumerate(positions, start=2):
            # Basic info
            sheet.cell(row=row_idx, column=1).value = position.get('position_number', '')
            sheet.cell(row=row_idx, column=2).value = position.get('description', '')
            sheet.cell(row=row_idx, column=3).value = position.get('quantity', 0)
            sheet.cell(row=row_idx, column=4).value = position.get('unit', '')
            sheet.cell(row=row_idx, column=5).value = position.get('code', '')
            
            # Classification
            classification = position.get('classification', '')
            cell = sheet.cell(row=row_idx, column=6)
            cell.value = classification
            if classification == 'GREEN':
                cell.fill = self.styles['green_fill']
            elif classification == 'AMBER':
                cell.fill = self.styles['amber_fill']
            elif classification == 'RED':
                cell.fill = self.styles['red_fill']
            
            # Enrichment status
            enrichment = position.get('enrichment_status', 'N/A')
            sheet.cell(row=row_idx, column=7).value = enrichment
            
            # Validation status
            validation = position.get('validation_status', 'N/A')
            sheet.cell(row=row_idx, column=8).value = validation
            
            # Technical specs (simplified)
            tech_specs = position.get('technical_specs', {})
            if tech_specs:
                specs_str = f"Class: {tech_specs.get('concrete_class', 'N/A')}"
                if tech_specs.get('exposure_classes'):
                    specs_str += f"\nExposure: {', '.join(tech_specs['exposure_classes'])}"
                if tech_specs.get('concrete_cover_mm'):
                    specs_str += f"\nCover: {tech_specs['concrete_cover_mm']}mm"
                sheet.cell(row=row_idx, column=9).value = specs_str
                sheet.cell(row=row_idx, column=9).alignment = self.styles['wrap']
            
            # Drawing source
            drawing_source = position.get('drawing_source', {})
            if drawing_source:
                source_str = f"{drawing_source.get('drawing', '')}\nPage {drawing_source.get('page', '')}"
                sheet.cell(row=row_idx, column=10).value = source_str
                sheet.cell(row=row_idx, column=10).alignment = self.styles['wrap']
            
            # Issues
            issues = position.get('issues', [])
            if issues:
                sheet.cell(row=row_idx, column=11).value = '\n'.join(issues)
                sheet.cell(row=row_idx, column=11).alignment = self.styles['wrap']
            
            # Borders
            for col_idx in range(1, 12):
                sheet.cell(row=row_idx, column=col_idx).border = self.styles['border']
        
        # Auto-size columns
        column_widths = [8, 40, 10, 8, 15, 15, 15, 15, 30, 20, 40]
        for col_idx, width in enumerate(column_widths, start=1):
            sheet.column_dimensions[get_column_letter(col_idx)].width = width
        
        # Freeze top row
        sheet.freeze_panes = 'A2'
    
    def _create_classification_sheets(self, audit_results: Dict[str, Any]):
        """Create separate sheets for each classification"""
        positions = audit_results.get('positions', [])
        
        for classification in ['GREEN', 'AMBER', 'RED']:
            filtered_positions = [
                p for p in positions
                if p.get('classification') == classification
            ]
            
            if not filtered_positions:
                continue
            
            self._create_filtered_positions_sheet(
                classification,
                filtered_positions
            )
    
    def _create_filtered_positions_sheet(
        self,
        sheet_name: str,
        positions: List[Dict[str, Any]]
    ):
        """Create sheet with filtered positions"""
        sheet = self.workbook.create_sheet(sheet_name)
        
        # Same structure as All Positions but filtered
        headers = [
            "№", "Description", "Quantity", "Unit", "Code",
            "Enrichment", "Technical Specs", "Issues", "Recommendations"
        ]
        
        for col_idx, header in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.styles['header']
            cell.fill = self.styles['header_fill']
            cell.alignment = self.styles['center']
            cell.border = self.styles['border']
        
        for row_idx, position in enumerate(positions, start=2):
            sheet.cell(row=row_idx, column=1).value = position.get('position_number', '')
            sheet.cell(row=row_idx, column=2).value = position.get('description', '')
            sheet.cell(row=row_idx, column=3).value = position.get('quantity', 0)
            sheet.cell(row=row_idx, column=4).value = position.get('unit', '')
            sheet.cell(row=row_idx, column=5).value = position.get('code', '')
            sheet.cell(row=row_idx, column=6).value = position.get('enrichment_status', 'N/A')
            
            # Technical specs
            tech_specs = position.get('technical_specs', {})
            if tech_specs:
                specs_str = '\n'.join([f"{k}: {v}" for k, v in tech_specs.items()])
                sheet.cell(row=row_idx, column=7).value = specs_str
                sheet.cell(row=row_idx, column=7).alignment = self.styles['wrap']
            
            # Issues
            issues = position.get('issues', [])
            if issues:
                sheet.cell(row=row_idx, column=8).value = '\n'.join(issues)
                sheet.cell(row=row_idx, column=8).alignment = self.styles['wrap']
            
            # Recommendations
            recommendations = position.get('recommendations', [])
            if recommendations:
                sheet.cell(row=row_idx, column=9).value = '\n'.join(recommendations)
                sheet.cell(row=row_idx, column=9).alignment = self.styles['wrap']
            
            # Borders
            for col_idx in range(1, 10):
                sheet.cell(row=row_idx, column=col_idx).border = self.styles['border']
        
        # Auto-size
        column_widths = [8, 40, 10, 8, 15, 15, 30, 40, 40]
        for col_idx, width in enumerate(column_widths, start=1):
            sheet.column_dimensions[get_column_letter(col_idx)].width = width
        
        sheet.freeze_panes = 'A2'
    
    def _create_drawing_specs_sheet(self, audit_results: Dict[str, Any]):
        """Create sheet with all drawing specifications"""
        sheet = self.workbook.create_sheet("Drawing Specs")
        
        # This would require access to original drawing specs
        # For now, create placeholder
        sheet['A1'] = "Drawing Specifications"
        sheet['A1'].font = self.styles['header']
        sheet['A1'].fill = self.styles['header_fill']
        
        sheet['A3'] = "This sheet contains all specifications extracted from drawings"


# ==============================================================================
# CONVENIENCE FUNCTION
# ==============================================================================


def _resolve_cache_path(project: Dict[str, Any]) -> Path | None:
    """Return project cache path if it exists on disk."""

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
    """Load classified positions from the project cache if present."""

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

    return [dict(item) for item in positions if isinstance(item, dict)]


def _normalise_audit_results(project: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure audit results follow the exporter contract."""

    raw_results = project.get("audit_results") or {}
    payload = dict(raw_results)

    if "enrichment_stats" not in payload and isinstance(payload.get("enrichment"), dict):
        payload["enrichment_stats"] = payload.get("enrichment", {})
    if "validation_stats" not in payload and isinstance(payload.get("validation"), dict):
        payload["validation_stats"] = payload.get("validation", {})
    if "schema_validation" not in payload:
        schema_stats = (project.get("diagnostics") or {}).get("schema_validation")
        if isinstance(schema_stats, dict):
            payload["schema_validation"] = schema_stats

    positions = payload.get("positions")
    if not isinstance(positions, list) or not positions:
        positions = _load_positions_from_cache(project)
        if positions:
            payload["positions"] = positions

    normalised_positions: List[Dict[str, Any]] = []
    for position in positions or []:
        if not isinstance(position, dict):
            continue
        entry = dict(position)
        classification = str(
            entry.get("classification") or entry.get("audit") or ""
        ).upper()
        if not classification:
            classification = "GREEN"
        entry["classification"] = classification
        normalised_positions.append(entry)

    payload["positions"] = normalised_positions

    total = payload.get("total_positions")
    if total is None:
        total = len(normalised_positions)

    green = payload.get("green")
    amber = payload.get("amber")
    red = payload.get("red")
    if any(value is None for value in (green, amber, red)):
        green = sum(1 for item in normalised_positions if item.get("classification") == "GREEN")
        amber = sum(1 for item in normalised_positions if item.get("classification") == "AMBER")
        red = sum(1 for item in normalised_positions if item.get("classification") == "RED")

    payload["total_positions"] = total
    payload["green"] = green or 0
    payload["amber"] = amber or 0
    payload["red"] = red or 0
    payload.setdefault("positions_preview", normalised_positions[:100])

    if not isinstance(payload.get("audit"), dict):
        payload["audit"] = {
            "green": payload["green"],
            "amber": payload["amber"],
            "red": payload["red"],
        }

    payload.setdefault("enrichment_stats", {})
    payload.setdefault("validation_stats", {})
    payload.setdefault("schema_validation", {})

    return payload


async def export_enriched_results(project: Dict[str, Any]) -> Path:
    """
    Convenience function to export enriched results
    
    Args:
        project: Project dict with audit results
        
    Returns:
        Path to generated Excel file
    """
    exporter = EnrichedExcelExporter()
    return await exporter.export(project)
