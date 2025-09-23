"""
merge_parser.py
Объединяет данные из документов и смет.
"""
from collections import defaultdict

def merge_concrete_data(doc_data, smeta_data):
    merged = defaultdict(lambda: {
        "classes": set(),
        "workability": set(),
        "contexts": set(),
        "smeta_positions": [],
        "quantities": []
    })

    # Данные из текстов
    for mark, data in doc_data.get("concrete_grades", {}).items():
        merged[mark]["contexts"].update(data.get("used_in", []))
        merged[mark]["smeta_positions"].extend(data.get("found_in_smeta", []))

    for cls in doc_data.get("environment_classes", []):
        for mark in merged:
            merged[mark]["classes"].add(cls["code"])

    # Данные из смет
    for s in smeta_data:
        mark = s.get("mark")
        if mark:
            merged[mark]["quantities"].append({
                "qty": s.get("qty"),
                "unit": s.get("unit"),
                "row": s.get("row"),
                "description": s.get("name")
            })

    # Приводим множества в списки
    result = []
    for mark, data in merged.items():
        result.append({
            "mark": mark,
            "classes": sorted(data["classes"]),
            "workability": sorted(data["workability"]),
            "contexts": sorted(data["contexts"]),
            "quantities": data["quantities"],
            "smeta_positions": data["smeta_positions"]
        })

    return result

