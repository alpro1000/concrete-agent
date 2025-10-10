"""
Excel Parser for construction estimates
БЕЗ CLAUDE FALLBACK - только локальный парсинг

Поддерживает:
- .xlsx (Office 2007+)
- .xls (Office 97-2003)
- Чешские форматы выказов
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import re

logger = logging.getLogger(__name__)


class ExcelParser:
    """
    Excel parser для строительных смет
    
    ✅ БЕЗ Claude fallback - только pandas
    ✅ Полная поддержка чешских столбцов
    """
    
    # Расширенные чешские столбцы
    CZECH_COLUMNS = {
        'number': ['pč', 'p.č.', 'číslo', 'cislo', 'number', 'no'],
        'type': ['typ', 'type'],
        'code': ['kód', 'kod', 'code'],
        'description': ['popis', 'název', 'nazev', 'description', 'name'],
        'unit': ['mj', 'm.j.', 'jednotka', 'unit'],
        'quantity': ['množství', 'mnozstvi', 'quantity', 'počet', 'pocet'],
        'unit_price': ['j.cena', 'j. cena', 'jednotková', 'unit price', 'cena'],
        'total_price': ['cena celkem', 'celkem', 'total', 'celková cena']
    }
    
    def __init__(self):
        """БЕЗ claude_client параметра!"""
        pass
    
    def parse(self, excel_path: Path) -> Dict[str, Any]:
        """
        Parse Excel estimate
        
        Args:
            excel_path: Path to Excel file
            
        Returns:
            Dict with parsed data
        """
        logger.info(f"📊 Parsing Excel: {excel_path}")
        
        return self._parse_with_pandas(excel_path)
    
    def _parse_with_pandas(self, excel_path: Path) -> Dict[str, Any]:
        """Parse Excel using pandas"""
        logger.info("Using pandas parser...")
        
        # Read Excel file
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
        """Parse positions from pandas DataFrame"""
        if df.empty:
            return []
        
        positions = []
        
        # Normalize column names (lowercase, strip)
        df.columns = [str(col).lower().strip() for col in df.columns]
        
        # Find relevant columns - ✅ CASE-INSENSITIVE!
        code_col = self._find_column(df.columns, self.CZECH_COLUMNS['code'])
        desc_col = self._find_column(df.columns, self.CZECH_COLUMNS['description'])
        unit_col = self._find_column(df.columns, self.CZECH_COLUMNS['unit'])
        qty_col = self._find_column(df.columns, self.CZECH_COLUMNS['quantity'])
        price_col = self._find_column(df.columns, self.CZECH_COLUMNS['unit_price'])
        total_col = self._find_column(df.columns, self.CZECH_COLUMNS['total_price'])
        
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
                    "quantity": self._parse_czech_number(self._get_cell_value(row, qty_col, '0')),
                    "unit_price": self._parse_czech_number(self._get_cell_value(row, price_col, '0')),
                    "total_price": self._parse_czech_number(self._get_cell_value(row, total_col, '0')),
                    "sheet": sheet_name,
                    "row_number": int(idx) + 2  # +2 for Excel row number (1-indexed + header)
                }
                
                # Calculate total if not present
                if position["quantity"] and position["unit_price"] and not position["total_price"]:
                    position["total_price"] = position["quantity"] * position["unit_price"]
                
                positions.append(position)
                
            except Exception as e:
                logger.warning(f"  Failed to parse row {idx}: {e}")
                continue
        
        return positions
    
    def _find_column(self, columns: List[str], keywords: List[str]) -> Optional[str]:
        """
        Find column name by keywords
        ✅ CASE-INSENSITIVE поиск!
        """
        for col in columns:
            col_clean = col.lower().strip()
            for keyword in keywords:
                keyword_clean = keyword.lower().strip()
                if keyword_clean in col_clean or col_clean == keyword_clean:
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
        
        # If short and matches header keyword exactly
        if len(text_lower) < 20:
            return any(keyword == text_lower for keyword in header_keywords)
        
        return False
    
    def _parse_czech_number(self, value: Any) -> float:
        """
        Parse Czech number format
        ✅ Улучшенный парсинг
        
        Examples:
        - "1 220,168" → 1220.168
        - "15,50" → 15.50
        - "1 000" → 1000.0
        """
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            try:
                text = value.strip()
                
                # Remove spaces and non-breaking spaces
                text = text.replace(' ', '').replace('\xa0', '')
                
                # Remove currency
                text = text.replace('Kč', '').replace('CZK', '').replace('EUR', '').replace('€', '')
                text = text.strip()
                
                # Handle Czech decimal separator
                # If has both . and , → European format
                if '.' in text and ',' in text:
                    text = text.replace('.', '')  # Remove thousands
                    text = text.replace(',', '.')  # Comma is decimal
                elif ',' in text:
                    # Check if comma is thousands or decimal
                    parts = text.split(',')
                    if len(parts) == 2 and len(parts[1]) <= 2:
                        # Decimal: 15,50
                        text = text.replace(',', '.')
                    else:
                        # Thousands: 1,220
                        text = text.replace(',', '')
                
                # Clean any remaining non-numeric
                text = re.sub(r'[^\d.-]', '', text)
                
                if not text or text == '-':
                    return 0.0
                
                return float(text)
            except (ValueError, AttributeError):
                return 0.0
        
        return 0.0
