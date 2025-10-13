"""
Excel Parser - ИСПРАВЛЕНО
Теперь использует универсальный нормализатор для всех форматов
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
import re

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
                sheet_positions = self._parse_sheet(sheet, sheet_name)
                
                raw_count = len(sheet_positions)

                if sheet_positions:
                    logger.info(
                        f"Extracted {raw_count} positions from sheet '{sheet_name}'"
                    )
                    all_positions.extend(sheet_positions)
                else:
                    logger.debug(f"No positions found in sheet '{sheet_name}'")

                sheet_summaries.append({
                    "sheet_name": sheet_name,
                    "raw_positions": raw_count
                })

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
                    "sheet_summaries": sheet_summaries
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
                    "sheet_summaries": []
                }
            }
    
    def _parse_sheet(self, sheet: Worksheet, sheet_name: str) -> List[Dict[str, Any]]:
        """
        Parse a single Excel sheet
        
        Args:
            sheet: openpyxl Worksheet object
            sheet_name: Name of the sheet
            
        Returns:
            List of raw position dicts (not normalized yet)
        """
        if not sheet or sheet.max_row < 2:
            logger.debug(f"Sheet '{sheet_name}' is empty or too small")
            return []
        
        # Find header row
        header_row = self._find_header_row(sheet)
        
        if header_row is None:
            logger.warning(f"No header row found in sheet '{sheet_name}'")
            return []
        
        logger.debug(f"Found header row at row {header_row}")
        
        # Extract headers
        headers = []
        for cell in sheet[header_row]:
            if cell.value:
                # Clean header
                header = str(cell.value).lower().strip()
                header = re.sub(r'[^\w\s]', '', header)
                header = re.sub(r'\s+', '_', header)
                headers.append(header)
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
        
        return positions
    
    @staticmethod
    def _find_header_row(sheet: Worksheet) -> Optional[int]:
        """
        Find the row that contains column headers
        
        Looks for rows with typical header keywords
        
        Returns:
            Row number (1-indexed) or None if not found
        """
        header_keywords = [
            'popis', 'opis', 'nazev', 'description', 'desc',
            'mnozstvi', 'množství', 'qty', 'quantity',
            'cena', 'price', 'kc', 'czk',
            'mj', 'unit', 'jednotka'
        ]
        
        # Check first 20 rows for headers
        for row_idx in range(1, min(21, sheet.max_row + 1)):
            row = sheet[row_idx]
            row_text = ' '.join(
                str(cell.value).lower() 
                for cell in row 
                if cell.value
            )
            
            # If row contains at least 2 header keywords, it's likely a header
            matches = sum(1 for keyword in header_keywords if keyword in row_text)
            if matches >= 2:
                return row_idx
        
        # Default to first row if no header found
        return 1
    
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
