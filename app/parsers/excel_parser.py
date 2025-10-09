"""
Excel Parser for construction estimates
Парсер Excel выказов
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class ExcelParser:
    """
    Excel parser для строительных смет
    
    Поддерживает:
    - .xlsx (Office 2007+)
    - .xls (Office 97-2003)
    - Различные форматы выказов
    """
    
    def __init__(self, claude_client=None):
        """
        Args:
            claude_client: ClaudeClient instance for fallback
        """
        self.claude = claude_client
    
    def parse(self, excel_path: Path) -> Dict[str, Any]:
        """
        Parse Excel estimate
        
        Args:
            excel_path: Path to Excel file
            
        Returns:
            Dict with parsed data
        """
        logger.info(f"Parsing Excel: {excel_path}")
        
        try:
            # Try pandas first
            return self._parse_with_pandas(excel_path)
        except Exception as e:
            logger.warning(f"Pandas parsing failed: {e}")
            
            # Fallback to Claude if available
            if self.claude:
                logger.info("Using Claude fallback...")
                return self.claude.parse_excel(excel_path)
            
            raise Exception(f"Failed to parse Excel: {e}")
    
    def _parse_with_pandas(self, excel_path: Path) -> Dict[str, Any]:
        """
        Parse Excel using pandas
        """
        logger.info("Parsing Excel with pandas...")
        
        # Read Excel file
        # Try to read all sheets
        try:
            excel_file = pd.ExcelFile(excel_path)
            sheet_names = excel_file.sheet_names
            logger.info(f"Found {len(sheet_names)} sheets: {sheet_names}")
        except Exception as e:
            logger.error(f"Failed to read Excel file: {e}")
            raise
        
        all_positions = []
        sections = []
        
        # Parse each sheet
        for sheet_name in sheet_names:
            logger.info(f"Parsing sheet: {sheet_name}")
            
            try:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                
                # Parse positions from dataframe
                positions = self._parse_dataframe(df, sheet_name)
                
                if positions:
                    all_positions.extend(positions)
                    sections.append({
                        "name": sheet_name,
                        "positions_count": len(positions)
                    })
                    
                    logger.info(f"  Found {len(positions)} positions in {sheet_name}")
                
            except Exception as e:
                logger.warning(f"Failed to parse sheet {sheet_name}: {e}")
                continue
        
        result = {
            "positions": all_positions,
            "total_positions": len(all_positions),
            "document_info": {
                "document_type": "Excel Estimate",
                "format": "EXCEL_PANDAS",
                "sheets": len(sheet_names),
                "sheet_names": sheet_names
            },
            "sections": sections
        }
        
        logger.info(f"✅ Parsed {len(all_positions)} total positions from Excel")
        return result
    
    def _parse_dataframe(self, df: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
        """
        Parse positions from pandas DataFrame
        
        Args:
            df: pandas DataFrame
            sheet_name: Name of the sheet
            
        Returns:
            List of parsed positions
        """
        if df.empty:
            return []
        
        positions = []
        
        # Normalize column names (lowercase, strip)
        df.columns = [str(col).lower().strip() for col in df.columns]
        
        # Find relevant columns
        code_col = self._find_column(df.columns, ['code', 'kód', 'kod', 'číslo', 'cislo'])
        desc_col = self._find_column(df.columns, ['description', 'popis', 'název', 'nazev', 'name'])
        unit_col = self._find_column(df.columns, ['unit', 'mj', 'jednotka'])
        qty_col = self._find_column(df.columns, ['quantity', 'množství', 'mnozstvi', 'počet', 'pocet'])
        price_col = self._find_column(df.columns, ['price', 'cena', 'unit_price', 'jednotková'])
        
        logger.info(f"  Column mapping: code={code_col}, desc={desc_col}, unit={unit_col}, qty={qty_col}, price={price_col}")
        
        # If no description column found, skip this sheet
        if desc_col is None:
            logger.warning(f"  No description column found in {sheet_name}")
            return []
        
        # Parse each row
        for idx, row in df.iterrows():
            try:
                # Get description - this is required
                description = self._get_cell_value(row, desc_col, '')
                
                # Skip empty rows or header-like rows
                if not description or self._is_header_row(description):
                    continue
                
                position = {
                    "code": self._get_cell_value(row, code_col, ''),
                    "description": description,
                    "unit": self._get_cell_value(row, unit_col, ''),
                    "quantity": self._parse_float(self._get_cell_value(row, qty_col, '0')),
                    "unit_price": self._parse_float(self._get_cell_value(row, price_col, '0')),
                    "sheet": sheet_name,
                    "row_number": int(idx) + 2  # +2 for Excel row number (1-indexed + header)
                }
                
                # Calculate total if not present
                if position["quantity"] and position["unit_price"]:
                    position["total_price"] = position["quantity"] * position["unit_price"]
                
                positions.append(position)
                
            except Exception as e:
                logger.warning(f"  Failed to parse row {idx}: {e}")
                continue
        
        return positions
    
    def _find_column(self, columns: List[str], keywords: List[str]) -> Optional[str]:
        """Find column name by keywords"""
        for col in columns:
            for keyword in keywords:
                if keyword in col:
                    return col
        return None
    
    def _get_cell_value(self, row: pd.Series, col: Optional[str], default: Any = '') -> Any:
        """Safely get cell value"""
        if col is None or col not in row.index:
            return default
        
        value = row[col]
        
        # Handle NaN/None
        if pd.isna(value):
            return default
        
        return value
    
    def _is_header_row(self, text: str) -> bool:
        """Check if text looks like a header row"""
        text_lower = str(text).lower().strip()
        
        # Skip common header keywords
        header_keywords = [
            'code', 'kód', 'kod', 'popis', 'description',
            'jednotka', 'unit', 'mj', 'množství', 'quantity',
            'cena', 'price', 'celkem', 'total'
        ]
        
        return any(keyword == text_lower for keyword in header_keywords)
    
    def _parse_float(self, value: Any) -> float:
        """Parse float from value"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            try:
                # Remove spaces and replace comma with dot
                value = value.strip().replace(' ', '').replace(',', '.')
                # Remove currency symbols
                value = value.replace('Kč', '').replace('CZK', '').strip()
                return float(value)
            except (ValueError, AttributeError):
                return 0.0
        
        return 0.0
