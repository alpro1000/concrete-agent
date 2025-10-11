"""
KROS XML Parser
БЕЗ CLAUDE/NANONETS FALLBACK - только XML parsing

Поддерживает:
- KROS Table XML (с ценами)
- KROS UNIXML (без цен) - УЛУЧШЕННАЯ ПОДДЕРЖКА
- Старые форматы KROS
"""
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class KROSParser:
    """
    Специализированный парсер для KROS XML
    
    ✅ БЕЗ Claude/Nanonets fallback
    ✅ Прямой XML parsing
    ✅ Улучшенная поддержка разных структур UNIXML
    """
    
    def __init__(self):
        """БЕЗ claude_client и nanonets_client!"""
        pass
    
    def parse(self, xml_path: Path) -> Dict[str, Any]:
        """
        Парсинг KROS XML
        
        Args:
            xml_path: Path to KROS XML file
            
        Returns:
            Dict with parsed data
        """
        logger.info(f"📝 Parsing KROS XML: {xml_path}")
        
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
        
        # Parse based on format
        if xml_format == "KROS_UNIXML":
            return self._parse_unixml(xml_content, xml_path)
        elif xml_format == "KROS_TABLE":
            return self._parse_table_xml(xml_content)
        else:
            return self._parse_generic_xml(xml_content)
    
    def _detect_format(self, xml_content: str) -> str:
        """Detect KROS XML format type"""
        content_lower = xml_content.lower()
        
        if '<unixml' in content_lower:
            return "KROS_UNIXML"
        elif '<tz>' in content_lower or '<row>' in content_lower:
            return "KROS_TABLE"
        else:
            return "GENERIC"
    
    def _parse_unixml(self, xml_content: str, xml_path: Path) -> Dict[str, Any]:
        """
        Parse KROS UNIXML format (Soupis prací)
        ✅ УЛУЧШЕНО: Поддержка разных структур
        """
        logger.info("Parsing KROS UNIXML format")
        
        try:
            root = ET.fromstring(xml_content)
            positions = []
            sections = []
            
            # ✅ НОВОЕ: Попробовать разные пути к данным
            
            # Вариант 1: Классическая структура с <body>
            body = root.find('.//body')
            if body is not None:
                logger.info("  Found <body> structure")
                for section in body.findall('section'):
                    section_info = self._parse_unixml_section(section)
                    sections.append(section_info)
                    
                    for item in section.findall('.//item'):
                        position = self._parse_unixml_item(item, section_info)
                        if position:
                            positions.append(position)
            
            # Вариант 2: Прямые <item> без <body>
            elif root.findall('.//item'):
                logger.info("  Found direct <item> structure (no <body>)")
                all_items = root.findall('.//item')
                
                # Попробовать найти sections
                all_sections = root.findall('.//section')
                if all_sections:
                    for section in all_sections:
                        section_info = self._parse_unixml_section(section)
                        sections.append(section_info)
                        
                        # Найти items внутри этой section
                        for item in section.findall('.//item'):
                            position = self._parse_unixml_item(item, section_info)
                            if position:
                                positions.append(position)
                else:
                    # Нет sections - парсим все items как есть
                    default_section = {"name": "Unknown", "code": ""}
                    for item in all_items:
                        position = self._parse_unixml_item(item, default_section)
                        if position:
                            positions.append(position)
            
            # Вариант 3: Другие структуры - ищем по всем элементам
            else:
                logger.warning("  ⚠️  Non-standard UNIXML structure, trying generic approach")
                # Попробовать найти любые элементы похожие на позиции
                for elem in root.iter():
                    if self._looks_like_position_element(elem):
                        position = self._extract_position_from_element(elem)
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
            
            if not positions:
                logger.warning("⚠️  No positions found - check XML structure")
                # Вывести структуру для отладки
                self._debug_xml_structure(root)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse UNIXML: {e}", exc_info=True)
            raise
    
    def _looks_like_position_element(self, elem: ET.Element) -> bool:
        """Check if element looks like a position"""
        # Проверить имя тега
        tag_name = elem.tag.lower()
        if any(keyword in tag_name for keyword in ['item', 'position', 'polozka', 'row']):
            return True
        
        # Проверить наличие дочерних элементов с типичными полями
        children_tags = {child.tag.lower() for child in elem}
        position_tags = {'code', 'name', 'description', 'popis', 'kod', 'quantity', 'mnozstvi', 'unit', 'mj'}
        
        return len(children_tags & position_tags) >= 2
    
    def _extract_position_from_element(self, elem: ET.Element) -> Optional[Dict[str, Any]]:
        """Extract position data from generic element"""
        try:
            position = {}
            
            for child in elem:
                tag = child.tag.lower()
                text = child.text or ''
                
                # Код
                if any(kw in tag for kw in ['code', 'kod']):
                    position['code'] = text
                
                # Описание
                elif any(kw in tag for kw in ['name', 'description', 'popis', 'nazev']):
                    position['description'] = text
                
                # Единица
                elif any(kw in tag for kw in ['unit', 'mj', 'jednotka']):
                    position['unit'] = text
                
                # Количество
                elif any(kw in tag for kw in ['quantity', 'mnozstvi', 'pocet']):
                    position['quantity'] = self._parse_float(text)
                
                # Цены
                elif 'price' in tag or 'cena' in tag:
                    if 'unit' in tag or 'jednotkova' in tag:
                        position['unit_price'] = self._parse_float(text)
                    elif 'total' in tag or 'celkem' in tag:
                        position['total_price'] = self._parse_float(text)
            
            # Вернуть только если есть хоть что-то осмысленное
            if position.get('description') or position.get('code'):
                return position
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract position from element: {e}")
            return None
    
    def _debug_xml_structure(self, root: ET.Element, max_depth: int = 3):
        """
        Вывести структуру XML для отладки
        Помогает понять почему не нашли позиции
        """
        logger.debug("📊 XML Structure (first 3 levels):")
        
        def log_tree(elem: ET.Element, depth: int = 0, max_items: int = 3):
            if depth > max_depth:
                return
            
            indent = "  " * depth
            
            # Показать тег и количество детей
            children_count = len(list(elem))
            logger.debug(f"{indent}<{elem.tag}> ({children_count} children)")
            
            # Показать первых max_items детей
            for i, child in enumerate(elem):
                if i >= max_items:
                    logger.debug(f"{indent}  ... and {children_count - max_items} more")
                    break
                log_tree(child, depth + 1, max_items)
        
        log_tree(root)
    
    def _parse_table_xml(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse KROS Table XML format (Kalkulace s cenami)
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
        # Попробовать найти header разными способами
        header = section.find('header')
        if header is None:
            header = section.find('Header')
        if header is None:
            # Может section сам содержит атрибуты
            return {
                "name": section.get('name', 'Unknown Section'),
                "code": section.get('code', ''),
                "description": section.get('description', '')
            }
        
        return {
            "name": self._get_element_text(header, 'name', 'Unknown Section'),
            "code": self._get_element_text(header, 'code', ''),
            "description": self._get_element_text(header, 'description', '')
        }
    
    def _parse_unixml_item(self, item: ET.Element, section_info: Dict) -> Optional[Dict[str, Any]]:
        """
        Extract position from UNIXML item
        ✅ Улучшенная логика извлечения
        """
        try:
            # Попробовать разные варианты полей
            code = (self._get_element_text(item, 'code', '') or 
                   self._get_element_text(item, 'Code', '') or
                   self._get_element_text(item, 'kod', ''))
            
            description = (self._get_element_text(item, 'name', '') or
                         self._get_element_text(item, 'Name', '') or
                         self._get_element_text(item, 'description', '') or
                         self._get_element_text(item, 'popis', ''))
            
            unit = (self._get_element_text(item, 'unit', '') or
                   self._get_element_text(item, 'Unit', '') or
                   self._get_element_text(item, 'mj', '') or
                   self._get_element_text(item, 'MJ', ''))
            
            quantity = (self._get_element_float(item, 'quantity', 0.0) or
                       self._get_element_float(item, 'Quantity', 0.0) or
                       self._get_element_float(item, 'mnozstvi', 0.0))
            
            unit_price = (self._get_element_float(item, 'unit_price', 0.0) or
                         self._get_element_float(item, 'unitPrice', 0.0) or
                         self._get_element_float(item, 'UnitPrice', 0.0))
            
            total_price = (self._get_element_float(item, 'total_price', 0.0) or
                          self._get_element_float(item, 'totalPrice', 0.0) or
                          self._get_element_float(item, 'TotalPrice', 0.0))
            
            position = {
                "code": code,
                "description": description,
                "unit": unit,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
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
            code = self._get_element_text(row, 'C1', '')
            description = self._get_element_text(row, 'C2', '')
            
            # Skip if no description or code
            if not description and not code:
                return None
            
            # Skip section headers (HSV, PSV, etc.)
            if code.upper() in ['HSV', 'PSV', 'M', 'VRN'] or len(code) <= 2:
                return None
            
            position = {
                "code": code,
                "description": description,
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
        # Попробовать найти header разными способами
        header = root.find('.//global_header')
        if header is None:
            header = root.find('.//GlobalHeader')
        if header is None:
            header = root.find('.//header')
        
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
        position_keywords = {'code', 'name', 'description', 'quantity', 'unit', 'price', 'item', 'popis', 'kod', 'mj'}
        
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
            return float(text) if text else 0.0
        except (ValueError, AttributeError):
            return 0.0
