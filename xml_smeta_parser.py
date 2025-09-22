from defusedxml import ElementTree as ET

def safe_float(value: str) -> float:
    """Safely convert string to float, handling Czech decimal format"""
    if not value:
        return 0.0
    try:
        # Handle Czech decimal format (comma as decimal separator)
        normalized = str(value).strip().replace(',', '.')
        return float(normalized)
    except (ValueError, TypeError):
        return 0.0

def parse_xml_smeta(path: str) -> list[dict]:
    try:
        tree = ET.parse(path)
        records = []
        for el in tree.findall(".//polozka"):
            name = el.findtext("nazev") or el.findtext("název") or ""
            if name.strip():  # Only include records with non-empty names
                records.append({
                    "code": el.findtext("kod") or "",
                    "name": name,
                    "qty": safe_float(el.findtext("mnozstvi") or el.findtext("množství")),
                    "unit": el.findtext("mj") or "",
                    "price": safe_float(el.findtext("cena"))
                })
        return records
    except Exception:
        return []
