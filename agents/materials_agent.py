import re
import json
from parsers.doc_parser import extract_text_from_docs
from parsers.pdf_parser import extract_text_from_pdfs

# Загрузка промта с шаблоном поиска
try:
    with open("prompts/materials_prompt.json", encoding="utf-8") as f:
        materials_prompt = json.load(f)
except FileNotFoundError:
    materials_prompt = {}
    print("⚠️ Файл prompts/materials_prompt.json не найден, используем дефолтные шаблоны.")

# Шаблоны поиска по категориям материалов (если нет внешнего файла)
MATERIAL_PATTERNS = {
    "reinforcement": r"\b(výztuž|Fe\s?\d{3}|R\d{2,3}|ocel)\b",
    "windows": r"\b(okno|okna|PVC|dřevo|sklo)\b",
    "seals": r"\b(těsnění|těsnicí|pryž|guma|EPDM)\b",
    "metal_structures": r"\b(konstrukce z oceli|kovová konstrukce|ocelový rám|nosník)\b"
}

def analyze_materials(doc_paths: list[str]) -> dict:
    # Извлечение текста из документов
    text = extract_text_from_docs(doc_paths)
    if not text.strip():
        text = extract_text_from_pdfs(doc_paths)  # fallback, если не получилось

    results = []

    for category, pattern in MATERIAL_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            results.append({
                "type": category,
                "found_terms": sorted(set(matches)),
                "total_mentions": len(matches)
            })

    return {
        "materials_found": results,
        "document_count": len(doc_paths)
    }
