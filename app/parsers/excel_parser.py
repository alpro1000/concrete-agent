"""
Excel Parser - ИСПРАВЛЕНО
Теперь использует универсальный нормализатор для всех форматов
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
import re
import unicodedata

from app.utils.position_normalizer import normalize_positions

logger = logging.getLogger(__name__)


class ExcelParser:
    """Parse construction estimates from Excel files"""
    
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse Excel file and extract positions
        
        Args:
            file_path: Path to Excel file (.xlsx, .xls)
            
        Returns:
            {
                "document_info": {...},
                "positions": [...]
            }
        """
        logger.info(f"📊 Parsing Excel: {file_path.name}")
        
        try:
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            
            logger.info(f"Excel has {len(workbook.sheetnames)} sheets: {workbook.sheetnames}")
            
            all_positions = []
            sheet_summaries: List[Dict[str, Any]] = []
            
            # Process each sheet
            for sheet_name in workbook.sheetnames:
                logger.info(f"Processing sheet: {sheet_name}")
                
                sheet = workbook[sheet_name]
                sheet_positions, sheet_diag = self._parse_sheet(sheet, sheet_name)

                raw_count = len(sheet_positions)

                if sheet_positions:
                    logger.info(
                        f"Extracted {raw_count} positions from sheet '{sheet_name}'"
                    )
                    all_positions.extend(sheet_positions)
                else:
                    logger.debug(f"No positions found in sheet '{sheet_name}'")

                sheet_summary = {
                    "sheet_name": sheet_name,
                    "raw_positions": raw_count,
                }
                sheet_summary.update(sheet_diag)

                sheet_summaries.append(sheet_summary)

            logger.info(f"Total raw positions from all sheets: {len(all_positions)}")

            # Normalize all positions and capture statistics
            normalized_positions, normalization_stats = normalize_positions(
                all_positions,
                return_stats=True
            )

            logger.info(
                f"✅ Excel parsed: {normalization_stats['normalized_total']} valid positions "
                f"from {len(workbook.sheetnames)} sheet(s)"
            )

            header_detection = [
                {
                    "sheet_name": summary.get("sheet_name"),
                    "header_found": summary.get("header_found", False),
                    "header_row": summary.get("header_row"),
                }
                for summary in sheet_summaries
            ]

            return {
                "document_info": {
                    "filename": file_path.name,
                    "format": "excel",
                    "sheets": workbook.sheetnames,
                    "total_sheets": len(workbook.sheetnames)
                },
                "positions": normalized_positions,
                "diagnostics": {
                    "raw_total": normalization_stats["raw_total"],
                    "normalized_total": normalization_stats["normalized_total"],
                    "skipped_total": normalization_stats["skipped_total"],
                    "sheet_summaries": sheet_summaries,
                    "header_detection": header_detection,
                }
            }

        except Exception as e:
            logger.error(f"❌ Excel parsing failed: {str(e)}", exc_info=True)
            return {
                "document_info": {
                    "filename": file_path.name,
                    "format": "excel",
                    "error": str(e)
                },
                "positions": [],
                "diagnostics": {
                    "raw_total": 0,
                    "normalized_total": 0,
                    "skipped_total": 0,
                    "sheet_summaries": [],
                    "header_detection": []
                }
            }
    
    def _parse_sheet(
        self, sheet: Worksheet, sheet_name: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Parse a single Excel sheet
        
        Args:
            sheet: openpyxl Worksheet object
            sheet_name: Name of the sheet
            
        Returns:
            Tuple of raw position dicts (not normalized yet) and diagnostics
        """
        if not sheet or sheet.max_row < 2:
            logger.debug(f"Sheet '{sheet_name}' is empty or too small")
            diagnostics = {
                "header_found": False,
                "header_row": None,
                "header_values": [],
                "matched_keywords": [],
                "searched_rows": sheet.max_row if sheet else 0,
                "reason": "Sheet is empty or too small",
            }
            return [], diagnostics
        
        # Find header row
        header_search = self._find_header_row(sheet)
        header_row = header_search.get("row_index")

        sheet_diagnostics = {
            "header_found": header_row is not None,
            "header_row": header_row,
            "header_values": header_search.get("header_values", []),
            "matched_keywords": header_search.get("matched_keywords", []),
            "searched_rows": header_search.get("searched_rows"),
        }

        if header_row is None:
            reason = (
                "Header row not found within scan range"
                if sheet.max_row > 0
                else "Sheet is empty"
            )
            sheet_diagnostics["reason"] = reason
            sheet_diagnostics["best_candidate"] = header_search.get("best_candidate")
            sheet_diagnostics["sample_rows"] = header_search.get("sample_rows", [])
            logger.warning(
                "No header row found in sheet '%s'. Reason: %s. Best candidate: %s",
                sheet_name,
                reason,
                header_search.get("best_candidate"),
            )
            return [], sheet_diagnostics

        logger.info(
            "Found header row at row %s with values: %s",
            header_row,
            header_search.get("header_values", []),
        )
        
        # Extract headers
        headers = []
        for cell in sheet[header_row]:
            if cell.value:
                # Clean header
                header = ExcelParser._normalize_header_value(cell.value)
                if header:
                    header = header.replace(' ', '_')
                    headers.append(header)
                else:
                    headers.append(f"col_{len(headers)}")
            else:
                headers.append(f"col_{len(headers)}")

        logger.debug(f"Sheet headers: {headers}")
        
        positions = []
        
        # Process data rows
        for row_idx in range(header_row + 1, sheet.max_row + 1):
            row = sheet[row_idx]
            
            # Skip empty rows
            if all(not cell.value for cell in row):
                continue
            
            # Create position dict
            position = {}
            for col_idx, cell in enumerate(row):
                if col_idx < len(headers):
                    header = headers[col_idx]
                    value = cell.value
                    
                    if value is not None:
                        # Convert to string and clean
                        if isinstance(value, (int, float)):
                            position[header] = value
                        else:
                            value_str = str(value).strip()
                            if value_str:
                                position[header] = value_str
            
            # Skip separator rows
            if self._is_separator_row(position):
                continue
            
            # Add metadata
            position['_source'] = f"sheet_{sheet_name}_row_{row_idx}"
            
            if position:
                positions.append(position)
        
        logger.debug(f"Extracted {len(positions)} raw positions from sheet")
        
        return positions, sheet_diagnostics

    @staticmethod
    def _normalize_header_value(value: Any) -> str:
        """Normalize header values by lowering and stripping diacritics/symbols."""
        if value is None:
            return ""

        text = str(value).strip().lower()
        if not text:
            return ""

        normalized = unicodedata.normalize("NFKD", text)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    @staticmethod
    def _find_header_row(sheet: Worksheet) -> Dict[str, Any]:
        """
        Find the row that contains column headers

        Looks for rows with typical header keywords

        Returns:
            Detailed information about detected header row search
        """
        header_keywords = [
            "text",
            "popis",
            "opis",
            "nazev",
            "description",
            "desc",
            "jednotka",
            "mj",
            "m.j.",
            "množství",
            "mnozstvi",
            "qty",
            "quantity",
            "j.cena",
            "jednotkova cena",
            "jednotková cena",
            "cena celkem",
            "cena",
            "price",
            "kc",
            "czk",
            "kod",
            "kd",
            "typ",
            "normohodiny",
            "dph",
            "souhrn",
            "cena bez dph",
            "unit",
        ]

        normalized_keywords = {
            ExcelParser._normalize_header_value(keyword)
            for keyword in header_keywords
        }
        normalized_keywords.discard("")

        search_limit = min(100, sheet.max_row)
        sample_rows: List[List[str]] = []
        best_candidate: Optional[Dict[str, Any]] = None

        for row_idx in range(1, search_limit + 1):
            row = sheet[row_idx]
            raw_values = [
                str(cell.value).strip() if cell.value is not None else ""
                for cell in row
            ]

            if len(sample_rows) < 5:
                sample_rows.append(raw_values)

            normalized_cells = [
                ExcelParser._normalize_header_value(cell.value)
                for cell in row
                if cell.value is not None
            ]

            row_text = " ".join(value for value in normalized_cells if value)
            matched_keywords = {
                keyword for keyword in normalized_keywords if keyword in row_text
            }

            if matched_keywords:
                candidate = {
                    "row_index": row_idx,
                    "matches": sorted(matched_keywords),
                    "header_values": raw_values,
                }
                if not best_candidate or len(matched_keywords) > len(best_candidate["matches"]):
                    best_candidate = candidate

            if len(matched_keywords) >= 2:
                return {
                    "row_index": row_idx,
                    "header_values": raw_values,
                    "matched_keywords": sorted(matched_keywords),
                    "searched_rows": row_idx,
                    "sample_rows": sample_rows,
                    "best_candidate": best_candidate,
                }

        return {
            "row_index": None,
            "header_values": [],
            "matched_keywords": [],
            "searched_rows": search_limit,
            "sample_rows": sample_rows,
            "best_candidate": best_candidate,
        }
    
    @staticmethod
    def _is_separator_row(position: Dict[str, Any]) -> bool:
        """Check if row is a separator or section header"""
        if not position:
            return True
        
        # Get all text from row
        all_values = ' '.join(str(v) for v in position.values() if v)
        
        # Separators often have repeated characters or are very short
        if re.match(r'^[\-\=\*\s\.]+$', all_values):
            return True
        
        if len(all_values) < 3:
            return True
        
        # Check for section headers (often in uppercase)
        if all_values.isupper() and len(all_values) < 50:
            return True
        
        return False
    
    def get_supported_extensions(self) -> set:
        """Return supported file extensions"""
        return {'.xlsx', '.xls'}


# ==============================================================================
# USAGE EXAMPLE
# ==============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        excel_path = Path(sys.argv[1])
        
        parser = ExcelParser()
        result = parser.parse(excel_path)
        
        print(f"\n📊 Parsing Results:")
        print(f"File: {result['document_info']['filename']}")
        print(f"Sheets: {result['document_info'].get('sheets', [])}")
        print(f"Positions found: {len(result['positions'])}")
        
        if result['positions']:
            print(f"\n📝 First 3 positions:")
            for pos in result['positions'][:3]:
                print(f"\n  Position: {pos.get('position_number', 'N/A')}")
                print(f"  Description: {pos.get('description', 'N/A')[:50]}")
                print(f"  Quantity: {pos.get('quantity', 0)} {pos.get('unit', '')}")
                if 'unit_price' in pos:
                    print(f"  Price: {pos['unit_price']} CZK")
    else:
        print("Usage: python excel_parser.py <path_to_excel>")
        print("Example: python excel_parser.py data/raw/project1/vykaz_vymer/estimate.xlsx")
