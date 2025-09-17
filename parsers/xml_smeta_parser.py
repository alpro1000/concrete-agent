from lxml import etree

def parse_xml_smeta(path: str) -> list[dict]:
    tree = etree.parse(path)
    return [
        {
            "code": el.findtext("kod"),
            "name": el.findtext("nazev"),
            "qty": float(el.findtext("mnozstvi") or 0),
            ...
        }
        for el in tree.findall(".//polozka")
    ]
