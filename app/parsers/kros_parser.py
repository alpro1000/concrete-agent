"""
KROS XML Parser with fallback strategies
Специализированный парсер для KROS XML с поддержкой различных форматов
"""
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class KROSParser:
    """
    Специализированный парсер для KROS XML
    Поддерживает:
    - KROS Table XML 
    - KROS UNIXML
    - Старые форматы KROS
    
    Использует fallback стратегию:
    1. Прямой XML parsing
    2. Nanonets API (если XML поврежден) - если доступен
    3. Claude + промпты (последний вариант)
    """
    
    def __init__(self, claude_client=None, nanonets_client=None):
        """
        Args:
            claude_client: ClaudeClient instance for fallback
            nanonets_client: NanonetsClient instance for fallback
        """
        self.claude = claude_client
        self.nanonets = nanonets_client
    
    def parse(self, xml_path: Path) -> Dict[str, Any]:
        """
        Парсинг KROS XML с fallback стратегией
        
        Args:
            xml_path: Path to KROS XML file
            
        Returns:
            Dict with parsed data:
            {
                "positions": List[Dict],
                "total_positions": int,
                "document_info": Dict,
                "sections": List[Dict]
            }
        """
        logger.info(f"Parsing KROS XML: {xml_path}")
        
        # Read XML content
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read XML file: {e}")
            raise
        
        # Detect format
        xml_format = self._detect_format(xml_content)
        logger.info(f"Detected KROS format: {xml_format}")
        
        # Try direct XML parsing
        try:
            if xml_format == "KROS_UNIXML":
                return self._parse_unixml(xml_content)
            elif xml_format == "KROS_TABLE":
                return self._parse_table_xml(xml_content)
            else:
                return self._parse_generic_xml(xml_content)
                
        except Exception as e:
            logger.warning(f"Direct XML parsing failed: {e}")
            
            # Fallback to Nanonets if available
            if self.nanonets:
                try:
                    logger.info("Trying Nanonets fallback...")
                    return self._parse_with_nanonets(xml_path)
                except Exception as e2:
                    logger.warning(f"Nanonets parsing failed: {e2}")
            
            # Last resort: Claude
            if self.claude:
                logger.info("Using Claude fallback...")
                return self._parse_with_claude(xml_path)
            
            # No fallback available
            raise Exception(f"All parsing methods failed. Last error: {e}")
    
    def _detect_format(self, xml_content: str) -> str:
        """Detect KROS XML format type"""
        if '<unixml' in xml_content.lower():
            return "KROS_UNIXML"
        elif '<TZ>' in xml_content or '<Row>' in xml_content:
            return "KROS_TABLE"
        else:
            return "GENERIC"
    
    def _parse_unixml(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse KROS UNIXML format (Soupis prací)
        
        UNIXML structure:
        <unixml>
            <global_header>...</global_header>
            <body>
                <section>
                    <header>...</header>
                    <item>...</item>
                </section>
            </body>
        </unixml>
        """
        logger.info("Parsing KROS UNIXML format")
        
        try:
            root = ET.fromstring(xml_content)
            positions = []
            sections = []
            
            # Find all sections
            body = root.find('.//body')
            if body is None:
                raise ValueError("No <body> found in UNIXML")
            
            for section in body.findall('section'):
                section_info = self._parse_unixml_section(section)
                sections.append(section_info)
                
                # Extract items from section
                for item in section.findall('.//item'):
                    position = self._parse_unixml_item(item, section_info)
                    if position:
                        positions.append(position)
            
            # Extract document info
            doc_info = self._parse_unixml_header(root)
            
            result = {
                "positions": positions,
                "total_positions": len(positions),
                "document_info": doc_info,
                "sections": sections,
                "format": "KROS_UNIXML"
            }
            
            logger.info(f"✅ Parsed {len(positions)} positions from UNIXML")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse UNIXML: {e}")
            raise
    
    def _parse_table_xml(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse KROS Table XML format (Kalkulace s cenami)
        
        Table XML structure:
        <TZ>
            <Row>
                <C1>Kód</C1>
                <C2>Popis</C2>
                <C3>MJ</C3>
                <C4>Množství</C4>
                <C5>Cena</C5>
            </Row>
        </TZ>
        """
        logger.info("Parsing KROS Table XML format")
        
        try:
            root = ET.fromstring(xml_content)
            positions = []
            
            # Find all rows
            for row in root.findall('.//Row'):
                position = self._parse_table_row(row)
                if position:
                    positions.append(position)
            
            result = {
                "positions": positions,
                "total_positions": len(positions),
                "document_info": {
                    "document_type": "KROS Table XML",
                    "format": "KROS_TABLE"
                },
                "sections": [],
                "format": "KROS_TABLE"
            }
            
            logger.info(f"✅ Parsed {len(positions)} positions from Table XML")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse Table XML: {e}")
            raise
    
    def _parse_generic_xml(self, xml_content: str) -> Dict[str, Any]:
        """Parse generic XML format"""
        logger.info("Parsing generic XML format")
        
        try:
            root = ET.fromstring(xml_content)
            positions = []
            
            # Try to find common position elements
            for elem in root.iter():
                if self._looks_like_position(elem):
                    position = self._extract_position_data(elem)
                    if position:
                        positions.append(position)
            
            result = {
                "positions": positions,
                "total_positions": len(positions),
                "document_info": {
                    "document_type": "Generic XML",
                    "format": "GENERIC"
                },
                "sections": [],
                "format": "GENERIC"
            }
            
            logger.info(f"✅ Parsed {len(positions)} positions from generic XML")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse generic XML: {e}")
            raise
    
    def _parse_unixml_section(self, section: ET.Element) -> Dict[str, Any]:
        """Extract section info from UNIXML"""
        header = section.find('header')
        if header is None:
            return {"name": "Unknown", "code": ""}
        
        return {
            "name": self._get_element_text(header, 'name', 'Unknown Section'),
            "code": self._get_element_text(header, 'code', ''),
            "description": self._get_element_text(header, 'description', '')
        }
    
    def _parse_unixml_item(self, item: ET.Element, section_info: Dict) -> Optional[Dict[str, Any]]:
        """Extract position from UNIXML item"""
        try:
            position = {
                "code": self._get_element_text(item, 'code', ''),
                "description": self._get_element_text(item, 'name', ''),
                "unit": self._get_element_text(item, 'unit', ''),
                "quantity": self._get_element_float(item, 'quantity', 0.0),
                "unit_price": self._get_element_float(item, 'unit_price', 0.0),
                "total_price": self._get_element_float(item, 'total_price', 0.0),
                "section": section_info.get("name", ""),
                "section_code": section_info.get("code", "")
            }
            
            # Only return if we have meaningful data
            if position["description"] or position["code"]:
                return position
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse item: {e}")
            return None
    
    def _parse_table_row(self, row: ET.Element) -> Optional[Dict[str, Any]]:
        """Extract position from Table XML row"""
        try:
            # Extract data from columns
            position = {
                "code": self._get_element_text(row, 'C1', ''),
                "description": self._get_element_text(row, 'C2', ''),
                "unit": self._get_element_text(row, 'C3', ''),
                "quantity": self._parse_float(self._get_element_text(row, 'C4', '0')),
                "unit_price": self._parse_float(self._get_element_text(row, 'C5', '0')),
                "total_price": self._parse_float(self._get_element_text(row, 'C6', '0'))
            }
            
            # Only return if we have meaningful data
            if position["description"] or position["code"]:
                return position
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse row: {e}")
            return None
    
    def _parse_unixml_header(self, root: ET.Element) -> Dict[str, Any]:
        """Extract document info from UNIXML header"""
        header = root.find('.//global_header')
        if header is None:
            return {"document_type": "KROS UNIXML"}
        
        return {
            "document_type": "KROS UNIXML",
            "project_name": self._get_element_text(header, 'project_name', ''),
            "contractor": self._get_element_text(header, 'contractor', ''),
            "date": self._get_element_text(header, 'date', ''),
            "total_amount": self._get_element_float(header, 'total_amount', 0.0)
        }
    
    def _looks_like_position(self, elem: ET.Element) -> bool:
        """Check if element looks like a position"""
        # Simple heuristic: has child elements that look like position fields
        children = list(elem)
        if len(children) < 3:
            return False
        
        # Check for common position field names
        child_tags = {child.tag.lower() for child in children}
        position_keywords = {'code', 'name', 'description', 'quantity', 'unit', 'price', 'item'}
        
        return len(child_tags & position_keywords) >= 2
    
    def _extract_position_data(self, elem: ET.Element) -> Optional[Dict[str, Any]]:
        """Extract position data from generic element"""
        try:
            position = {}
            
            for child in elem:
                tag = child.tag.lower()
                text = child.text or ''
                
                if 'code' in tag or 'kod' in tag:
                    position['code'] = text
                elif 'name' in tag or 'description' in tag or 'popis' in tag:
                    position['description'] = text
                elif 'unit' in tag or 'mj' in tag:
                    position['unit'] = text
                elif 'quantity' in tag or 'mnozstvi' in tag:
                    position['quantity'] = self._parse_float(text)
                elif 'price' in tag or 'cena' in tag:
                    if 'unit' in tag or 'jednotkova' in tag:
                        position['unit_price'] = self._parse_float(text)
                    else:
                        position['total_price'] = self._parse_float(text)
            
            # Return only if we have description or code
            if position.get('description') or position.get('code'):
                return position
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract position data: {e}")
            return None
    
    def _parse_with_nanonets(self, xml_path: Path) -> Dict[str, Any]:
        """Parse using Nanonets API (fallback)"""
        if not self.nanonets:
            raise ValueError("Nanonets client not available")
        
        logger.info("Parsing with Nanonets...")
        result = self.nanonets.extract_estimate_data(xml_path)
        
        # Convert Nanonets result to our format
        return {
            "positions": result.get("positions", []),
            "total_positions": len(result.get("positions", [])),
            "document_info": result.get("metadata", {}),
            "sections": [],
            "format": "NANONETS_PARSED"
        }
    
    def _parse_with_claude(self, xml_path: Path) -> Dict[str, Any]:
        """Parse using Claude (last resort fallback)"""
        if not self.claude:
            raise ValueError("Claude client not available")
        
        logger.info("Parsing with Claude...")
        return self.claude.parse_xml(xml_path)
    
    # Utility methods
    def _get_element_text(self, parent: ET.Element, tag: str, default: str = '') -> str:
        """Safely get text from child element"""
        elem = parent.find(tag)
        return elem.text if elem is not None and elem.text else default
    
    def _get_element_float(self, parent: ET.Element, tag: str, default: float = 0.0) -> float:
        """Safely get float from child element"""
        text = self._get_element_text(parent, tag, str(default))
        return self._parse_float(text)
    
    def _parse_float(self, text: str) -> float:
        """Parse float from text, handling various formats"""
        try:
            # Remove spaces and replace comma with dot
            text = text.strip().replace(' ', '').replace(',', '.')
            return float(text)
        except (ValueError, AttributeError):
            return 0.0
