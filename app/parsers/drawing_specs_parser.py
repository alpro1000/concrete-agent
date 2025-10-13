"""
Drawing Specifications Parser
Извлекает таблицы спецификаций материалов из PDF чертежей
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import pdfplumber
import re

logger = logging.getLogger(__name__)


class DrawingSpecsParser:
    """
    Extract material specification tables from PDF drawings
    
    Находит и парсит таблицы с техническими спецификациями:
    - Бетон: класс, exposure classes, покрытие
    - Арматура: класс, диаметр
    - Изоляция: тип, толщина
    - Прочие материалы
    """
    
    # Ключевые слова для определения таблиц материалов
    MATERIAL_TABLE_KEYWORDS = [
        'materiál', 'material', 'beton', 'concrete',
        'třída', 'class', 'expozice', 'exposure',
        'specifikace', 'specification', 'výztuž', 'reinforcement',
        'izolace', 'insulation', 'povrch', 'surface'
    ]
    
    # Ключевые слова для различных типов материалов
    CONCRETE_KEYWORDS = ['beton', 'concrete', 'c20', 'c25', 'c30', 'c35', 'c40']
    REINFORCEMENT_KEYWORDS = ['výztuž', 'ocel', 'reinforcement', 'steel', 'b500']
    INSULATION_KEYWORDS = ['izolace', 'insulation', 'eps', 'xps', 'pir']
    
    def parse(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Parse PDF drawing and extract all material specifications
        
        Args:
            pdf_path: Path to PDF drawing file
            
        Returns:
            {
                "document_info": {...},
                "specifications": [...]
            }
        """
        logger.info(f"📐 Parsing drawing specifications: {pdf_path.name}")
        
        try:
            all_specs = []
            
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"Drawing has {total_pages} pages")
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract tables
                    tables = page.extract_tables()
                    
                    if tables:
                        logger.info(f"Found {len(tables)} table(s) on page {page_num}")
                        
                        for table_idx, table in enumerate(tables, start=1):
                            # Check if this is a material specification table
                            if self._is_material_table(table):
                                logger.info(
                                    f"Found material spec table on page {page_num}, "
                                    f"table {table_idx}"
                                )
                                
                                # Parse the table
                                specs = self._parse_material_table(
                                    table,
                                    pdf_path.name,
                                    page_num,
                                    table_idx
                                )
                                
                                all_specs.extend(specs)
                                logger.info(
                                    f"Extracted {len(specs)} specifications "
                                    f"from table {table_idx}"
                                )
                    
                    # Also extract text blocks (надписи вне таблиц)
                    text_specs = self._extract_text_specifications(
                        page,
                        pdf_path.name,
                        page_num
                    )
                    
                    if text_specs:
                        all_specs.extend(text_specs)
                        logger.info(
                            f"Extracted {len(text_specs)} specifications "
                            f"from text on page {page_num}"
                        )
            
            logger.info(
                f"✅ Drawing parsed: {len(all_specs)} total specifications "
                f"from {total_pages} pages"
            )
            
            return {
                "document_info": {
                    "filename": pdf_path.name,
                    "format": "pdf_drawing",
                    "total_pages": total_pages,
                    "tables_found": len(all_specs)
                },
                "specifications": all_specs
            }
            
        except Exception as e:
            logger.error(f"❌ Drawing parsing failed: {str(e)}", exc_info=True)
            return {
                "document_info": {
                    "filename": pdf_path.name,
                    "format": "pdf_drawing",
                    "error": str(e)
                },
                "specifications": []
            }
    
    def _is_material_table(self, table: List[List[str]]) -> bool:
        """
        Check if table contains material specifications
        
        Args:
            table: Extracted table as list of rows
            
        Returns:
            True if table looks like material specs
        """
        if not table or len(table) < 2:
            return False
        
        # Get header row text
        header_row = table[0] if table else []
        header_text = ' '.join(
            str(cell).lower() 
            for cell in header_row 
            if cell
        )
        
        # Check if header contains material keywords
        keyword_matches = sum(
            1 for keyword in self.MATERIAL_TABLE_KEYWORDS
            if keyword in header_text
        )
        
        # Need at least 2 matching keywords
        return keyword_matches >= 2
    
    def _parse_material_table(
        self,
        table: List[List[str]],
        filename: str,
        page_num: int,
        table_idx: int
    ) -> List[Dict[str, Any]]:
        """
        Parse material specification table
        
        Args:
            table: Extracted table
            filename: Source PDF filename
            page_num: Page number
            table_idx: Table index on page
            
        Returns:
            List of material specifications
        """
        if not table or len(table) < 2:
            return []
        
        # Extract and normalize headers
        headers = self._normalize_headers(table[0])
        
        logger.debug(f"Table headers: {headers}")
        
        specs = []
        
        # Process data rows
        for row_idx, row in enumerate(table[1:], start=2):
            # Skip empty rows
            if not row or all(not cell for cell in row):
                continue
            
            # Create specification dict
            spec = {}
            
            for col_idx, cell in enumerate(row):
                if col_idx < len(headers) and cell:
                    header = headers[col_idx]
                    value = str(cell).strip()
                    
                    if value and value not in ['-', '', 'N/A']:
                        spec[header] = value
            
            # Skip if no meaningful data
            if not spec or len(spec) < 2:
                continue
            
            # Determine material type
            spec['material_type'] = self._determine_material_type(spec)
            
            # Add source metadata
            spec['_source'] = {
                'drawing': filename,
                'page': page_num,
                'table': table_idx,
                'row': row_idx
            }
            
            # Extract structured data based on material type
            spec = self._structure_specification(spec)
            
            specs.append(spec)
        
        return specs
    
    def _normalize_headers(self, header_row: List[str]) -> List[str]:
        """
        Normalize table headers to standard names
        
        Args:
            header_row: Raw header row from table
            
        Returns:
            List of normalized header names
        """
        # Mapping of various header names to standard
        header_mapping = {
            'materiál': 'material',
            'material': 'material',
            'název': 'material',
            'nazev': 'material',
            
            'třída': 'class',
            'trida': 'class',
            'class': 'class',
            
            'expozice': 'exposure',
            'exposure': 'exposure',
            'exp': 'exposure',
            
            'povrch': 'surface',
            'surface': 'surface',
            'povrchová úprava': 'surface',
            'povrchova uprava': 'surface',
            
            'krytí': 'cover',
            'kryti': 'cover',
            'cover': 'cover',
            
            'tloušťka': 'thickness',
            'tloustka': 'thickness',
            'thickness': 'thickness',
            
            'poznámka': 'note',
            'poznamka': 'note',
            'note': 'note',
            'remarks': 'note'
        }
        
        normalized = []
        
        for header in header_row:
            if not header:
                normalized.append(f'col_{len(normalized)}')
                continue
            
            # Clean header
            clean = str(header).lower().strip()
            clean = re.sub(r'[^\w\s]', '', clean)
            clean = re.sub(r'\s+', ' ', clean)
            
            # Map to standard name
            standard = header_mapping.get(clean, clean)
            normalized.append(standard)
        
        return normalized
    
    def _determine_material_type(self, spec: Dict[str, Any]) -> str:
        """
        Determine type of material from specification
        
        Returns:
            'concrete', 'reinforcement', 'insulation', 'other'
        """
        spec_text = ' '.join(str(v).lower() for v in spec.values())
        
        if any(kw in spec_text for kw in self.CONCRETE_KEYWORDS):
            return 'concrete'
        
        if any(kw in spec_text for kw in self.REINFORCEMENT_KEYWORDS):
            return 'reinforcement'
        
        if any(kw in spec_text for kw in self.INSULATION_KEYWORDS):
            return 'insulation'
        
        return 'other'
    
    def _structure_specification(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure specification based on material type
        
        Extracts specific parameters for each material type
        """
        material_type = spec.get('material_type', 'other')
        
        if material_type == 'concrete':
            spec = self._structure_concrete_spec(spec)
        elif material_type == 'reinforcement':
            spec = self._structure_reinforcement_spec(spec)
        elif material_type == 'insulation':
            spec = self._structure_insulation_spec(spec)
        
        return spec
    
    def _structure_concrete_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract concrete-specific parameters
        
        - Concrete class (C20/25, C30/37, etc.)
        - Exposure classes (XA1, XC2, XF2, etc.)
        - Surface finish
        - Concrete cover
        - Additional requirements
        """
        # Extract concrete class
        material_text = spec.get('material', '') + ' ' + spec.get('class', '')
        
        concrete_class_match = re.search(r'C\d{2,3}/\d{2,3}', material_text, re.IGNORECASE)
        if concrete_class_match:
            spec['concrete_class'] = concrete_class_match.group(0).upper()
        
        # Extract exposure classes
        exposure_text = spec.get('exposure', '')
        if exposure_text:
            # Find patterns like XA1, XC2, XF2
            exposure_classes = re.findall(r'X[A-Z]\d', exposure_text.upper())
            if exposure_classes:
                spec['exposure_classes'] = list(set(exposure_classes))
        
        # Extract concrete cover
        cover_text = spec.get('cover', '')
        if cover_text:
            cover_match = re.search(r'(\d+)\s*mm', cover_text)
            if cover_match:
                spec['concrete_cover_mm'] = int(cover_match.group(1))
        
        return spec
    
    def _structure_reinforcement_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract reinforcement-specific parameters"""
        
        # Extract steel class
        material_text = spec.get('material', '') + ' ' + spec.get('class', '')
        
        steel_class_match = re.search(r'B\d{3}[A-Z]?', material_text, re.IGNORECASE)
        if steel_class_match:
            spec['steel_class'] = steel_class_match.group(0).upper()
        
        # Extract diameter if present
        diameter_match = re.search(r'[øΦ]?\s*(\d+)', material_text)
        if diameter_match:
            spec['diameter_mm'] = int(diameter_match.group(1))
        
        return spec
    
    def _structure_insulation_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insulation-specific parameters"""
        
        # Extract thickness
        material_text = spec.get('material', '') + ' ' + spec.get('thickness', '')
        
        thickness_match = re.search(r'(\d+)\s*mm', material_text)
        if thickness_match:
            spec['thickness_mm'] = int(thickness_match.group(1))
        
        # Extract insulation type
        for insul_type in ['EPS', 'XPS', 'PIR', 'MW', 'PUR']:
            if insul_type.lower() in material_text.lower():
                spec['insulation_type'] = insul_type
                break
        
        return spec
    
    def _extract_text_specifications(
        self,
        page,
        filename: str,
        page_num: int
    ) -> List[Dict[str, Any]]:
        """
        Extract specifications from text blocks (надписи вне таблиц)
        
        Ищет паттерны типа:
        "Beton C30/37 XA1, XC2, XF2"
        "Výztuž B500B"
        """
        specs = []
        
        try:
            text = page.extract_text()
            
            if not text:
                return []
            
            lines = text.split('\n')
            
            for line_idx, line in enumerate(lines, start=1):
                line = line.strip()
                
                if not line or len(line) < 10:
                    continue
                
                # Look for concrete specifications
                if any(kw in line.lower() for kw in self.CONCRETE_KEYWORDS):
                    spec = self._parse_text_concrete_spec(line)
                    if spec:
                        spec['_source'] = {
                            'drawing': filename,
                            'page': page_num,
                            'line': line_idx,
                            'type': 'text'
                        }
                        specs.append(spec)
                
                # Look for reinforcement specifications
                elif any(kw in line.lower() for kw in self.REINFORCEMENT_KEYWORDS):
                    spec = self._parse_text_reinforcement_spec(line)
                    if spec:
                        spec['_source'] = {
                            'drawing': filename,
                            'page': page_num,
                            'line': line_idx,
                            'type': 'text'
                        }
                        specs.append(spec)
        
        except Exception as e:
            logger.debug(f"Error extracting text specs: {e}")
        
        return specs
    
    def _parse_text_concrete_spec(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse concrete specification from text line"""
        
        spec = {
            'material_type': 'concrete',
            'raw_text': text
        }
        
        # Extract concrete class
        concrete_class = re.search(r'C\d{2,3}/\d{2,3}', text, re.IGNORECASE)
        if concrete_class:
            spec['concrete_class'] = concrete_class.group(0).upper()
            spec['material'] = f"Beton {spec['concrete_class']}"
        else:
            return None
        
        # Extract exposure classes
        exposure_classes = re.findall(r'X[A-Z]\d', text.upper())
        if exposure_classes:
            spec['exposure_classes'] = list(set(exposure_classes))
        
        return spec
    
    def _parse_text_reinforcement_spec(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse reinforcement specification from text line"""
        
        spec = {
            'material_type': 'reinforcement',
            'raw_text': text
        }
        
        # Extract steel class
        steel_class = re.search(r'B\d{3}[A-Z]?', text, re.IGNORECASE)
        if steel_class:
            spec['steel_class'] = steel_class.group(0).upper()
            spec['material'] = f"Výztuž {spec['steel_class']}"
            return spec
        
        return None


# ==============================================================================
# USAGE EXAMPLE
# ==============================================================================

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) > 1:
        drawing_path = Path(sys.argv[1])
        
        parser = DrawingSpecsParser()
        result = parser.parse(drawing_path)
        
        print(f"\n📊 Drawing Specifications:")
        print(f"File: {result['document_info']['filename']}")
        print(f"Pages: {result['document_info'].get('total_pages', 0)}")
        print(f"Specifications found: {len(result['specifications'])}")
        
        if result['specifications']:
            print(f"\n📝 Specifications:")
            for spec in result['specifications']:
                print(f"\n  Material: {spec.get('material', 'N/A')}")
                print(f"  Type: {spec.get('material_type', 'N/A')}")
                if spec.get('concrete_class'):
                    print(f"  Class: {spec['concrete_class']}")
                if spec.get('exposure_classes'):
                    print(f"  Exposure: {', '.join(spec['exposure_classes'])}")
                if spec.get('concrete_cover_mm'):
                    print(f"  Cover: {spec['concrete_cover_mm']} mm")
                print(f"  Source: page {spec['_source']['page']}")
    else:
        print("Usage: python drawing_specs_parser.py <path_to_drawing.pdf>")
        print("Example: python drawing_specs_parser.py data/raw/project1/vykresy/SO1-01.pdf")
