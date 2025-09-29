"""
xml_smeta_parser.py
Парсинг смет в формате XML.
"""
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)

def parse_xml_smeta(path):
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception:
        return []

    rows = []
    for idx, item in enumerate(root.findall(".//Item")):
        rows.append({
            "row": idx + 1,
            "code": item.findtext("Code", "").strip(),
            "name": item.findtext("Name", "").strip(),
            "qty": float(item.findtext("Qty", "0").replace(",", ".") or 0),
            "unit": item.findtext("Unit", "").strip()
        })
    return rows


class XMLSmetaParser:
    """
    XML Smeta Parser class for consistency with other parsers
    """
    
    def __init__(self):
        """Initialize XML smeta parser"""
        logger.info("📄 XML Smeta Parser initialized")
    
    def parse(self, file_path: str) -> dict:
        """
        Parse XML smeta file
        
        Args:
            file_path: Path to XML file
            
        Returns:
            Dictionary with parsed smeta data
        """
        try:
            items = parse_xml_smeta(file_path)
            
            # Calculate totals
            total_cost = 0.0
            total_volume = 0.0
            work_items = []
            materials = []
            resources = []
            
            for item in items:
                work_item = {
                    "code": item.get("code", ""),
                    "name": item.get("name", ""),
                    "quantity": item.get("qty", 0),
                    "unit": item.get("unit", ""),
                    "cost": 0.0,  # XML doesn't provide cost info
                    "duration": 1   # Default duration
                }
                work_items.append(work_item)
                
                # Extract materials from work item names
                if any(keyword in item.get("name", "").lower() for keyword in ["beton", "cement", "armatura", "výztuž"]):
                    materials.append({
                        "name": item.get("name", ""),
                        "quantity": item.get("qty", 0),
                        "unit": item.get("unit", "")
                    })
                
                total_volume += item.get("qty", 0)
            
            return {
                "total_cost": total_cost,
                "total_volume": total_volume,
                "work_items": work_items,
                "materials": materials,
                "resources": resources,
                "items_count": len(items),
                "parser_used": "xml_smeta_parser"
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing XML smeta {file_path}: {e}")
            return {
                "total_cost": 0.0,
                "total_volume": 0.0,
                "work_items": [],
                "materials": [],
                "resources": [],
                "items_count": 0,
                "error": str(e),
                "parser_used": "xml_smeta_parser"
            }
