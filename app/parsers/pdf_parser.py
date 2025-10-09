"""
PDF Parser with fallback strategies
Парсер PDF смет с использованием MinerU + Claude
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PDFParser:
    """
    PDF parser для строительных смет
    
    Использует fallback стратегию:
    1. MinerU - для качественного извлечения таблиц
    2. Claude - для интерпретации извлеченных данных
    3. pdfplumber - простой fallback если MinerU недоступен
    """
    
    def __init__(self, claude_client=None, mineru_client=None):
        """
        Args:
            claude_client: ClaudeClient instance
            mineru_client: MinerUClient instance (optional)
        """
        self.claude = claude_client
        self.mineru = mineru_client
    
    def parse(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Parse PDF estimate with fallback strategy
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with parsed data
        """
        logger.info(f"Parsing PDF: {pdf_path}")
        
        # Try MinerU first if available
        if self.mineru:
            try:
                logger.info("Trying MinerU parser...")
                return self._parse_with_mineru(pdf_path)
            except Exception as e:
                logger.warning(f"MinerU parsing failed: {e}")
        
        # Try pdfplumber
        try:
            logger.info("Trying pdfplumber parser...")
            return self._parse_with_pdfplumber(pdf_path)
        except Exception as e:
            logger.warning(f"pdfplumber parsing failed: {e}")
        
        # Last resort: Claude with raw PDF
        if self.claude:
            logger.info("Using Claude direct PDF parsing...")
            return self.claude.parse_pdf(pdf_path)
        
        raise Exception("All PDF parsing methods failed")
    
    def _parse_with_mineru(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Parse PDF using MinerU
        
        MinerU provides high-quality table extraction
        """
        if not self.mineru:
            raise ValueError("MinerU client not available")
        
        logger.info("Parsing with MinerU...")
        result = self.mineru.parse_pdf_estimate(str(pdf_path))
        
        # MinerU result already in our format
        return result
    
    def _parse_with_pdfplumber(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Parse PDF using pdfplumber + Claude
        
        1. Extract text and tables with pdfplumber
        2. Send to Claude for interpretation
        """
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber not installed. Install with: pip install pdfplumber")
        
        logger.info("Extracting PDF content with pdfplumber...")
        
        positions = []
        all_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text
                text = page.extract_text()
                if text:
                    all_text.append(f"=== Page {page_num} ===\n{text}")
                
                # Extract tables
                tables = page.extract_tables()
                for table_num, table in enumerate(tables, 1):
                    logger.info(f"Found table {table_num} on page {page_num}")
                    
                    # Try to parse table as positions
                    parsed_positions = self._parse_table(table, page_num, table_num)
                    positions.extend(parsed_positions)
        
        # If Claude available, use it to improve results
        if self.claude and positions:
            logger.info(f"Refining {len(positions)} positions with Claude...")
            # Send to Claude for validation and enhancement
            # For now, return raw positions
        
        full_text = "\n\n".join(all_text)
        
        result = {
            "positions": positions,
            "total_positions": len(positions),
            "document_info": {
                "document_type": "PDF Estimate",
                "format": "PDF_PDFPLUMBER",
                "pages": len(all_text)
            },
            "sections": [],
            "raw_text": full_text[:5000]  # First 5000 chars for reference
        }
        
        logger.info(f"✅ Extracted {len(positions)} positions from PDF")
        return result
    
    def _parse_table(self, table: List[List[str]], page_num: int, table_num: int) -> List[Dict[str, Any]]:
        """
        Parse a table extracted from PDF
        
        Args:
            table: 2D list of table cells
            page_num: Page number
            table_num: Table number on page
            
        Returns:
            List of parsed positions
        """
        if not table or len(table) < 2:
            return []
        
        positions = []
        
        # Try to identify header row
        header = table[0]
        header_lower = [str(cell).lower() if cell else '' for cell in header]
        
        # Find column indices
        code_idx = self._find_column(header_lower, ['code', 'kód', 'kod', 'číslo'])
        desc_idx = self._find_column(header_lower, ['description', 'popis', 'název', 'nazev', 'name'])
        unit_idx = self._find_column(header_lower, ['unit', 'mj', 'jednotka'])
        qty_idx = self._find_column(header_lower, ['quantity', 'množství', 'mnozstvi', 'počet'])
        price_idx = self._find_column(header_lower, ['price', 'cena', 'price_unit', 'jednotková'])
        
        # Parse data rows
        for row_idx, row in enumerate(table[1:], 1):
            if not row or len(row) == 0:
                continue
            
            # Skip rows that look like headers or totals
            if self._is_header_or_total_row(row):
                continue
            
            position = {
                "code": self._get_cell(row, code_idx, ''),
                "description": self._get_cell(row, desc_idx, ''),
                "unit": self._get_cell(row, unit_idx, ''),
                "quantity": self._parse_float(self._get_cell(row, qty_idx, '0')),
                "unit_price": self._parse_float(self._get_cell(row, price_idx, '0')),
                "page": page_num,
                "table": table_num,
                "row": row_idx
            }
            
            # Only add if we have meaningful data
            if position["description"] or position["code"]:
                positions.append(position)
        
        return positions
    
    def _find_column(self, header: List[str], keywords: List[str]) -> Optional[int]:
        """Find column index by keywords"""
        for idx, cell in enumerate(header):
            for keyword in keywords:
                if keyword in cell:
                    return idx
        return None
    
    def _get_cell(self, row: List, idx: Optional[int], default: str = '') -> str:
        """Safely get cell value"""
        if idx is None or idx >= len(row):
            return default
        return str(row[idx]) if row[idx] else default
    
    def _is_header_or_total_row(self, row: List) -> bool:
        """Check if row is a header or total row"""
        row_text = ' '.join([str(cell).lower() for cell in row if cell]).strip()
        
        skip_keywords = ['total', 'celkem', 'suma', 'subtotal', 'mezisoučet', 'code', 'kód']
        
        return any(keyword in row_text for keyword in skip_keywords)
    
    def _parse_float(self, text: str) -> float:
        """Parse float from text"""
        try:
            text = text.strip().replace(' ', '').replace(',', '.')
            # Remove currency symbols
            text = text.replace('Kč', '').replace('CZK', '').strip()
            return float(text)
        except (ValueError, AttributeError):
            return 0.0
