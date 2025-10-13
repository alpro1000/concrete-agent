from pathlib import Path
from xml.etree import ElementTree
from typing import List, Dict


class XMLParser:
    def parse(self, xml_path: Path) -> List[Dict]:
        tree = ElementTree.parse(xml_path)
        root = tree.getroot()
        items: List[Dict] = []
        for el in root.findall(".//Polozka"):
            quantity_text = el.findtext("mnozstvi")
            unit_price_text = el.findtext("jedn_cena")
            item = {
                "position_number": el.findtext("position_number") or el.findtext("pozice"),
                "code": el.findtext("znacka"),
                "description": el.findtext("nazev"),
                "unit": el.findtext("MJ"),
                "quantity": float(quantity_text.replace(",", ".")) if quantity_text else 0.0,
                "unit_price": float(unit_price_text.replace(",", ".")) if unit_price_text else None,
                "technical_spec": el.findtext("technicka_specifikace"),
            }
            items.append(item)
        return items


__all__ = ["XMLParser"]
