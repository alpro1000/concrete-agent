"""
xml_smeta_parser.py
Парсинг смет в формате XML.
"""
import xml.etree.ElementTree as ET

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
