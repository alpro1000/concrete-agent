import re
import json
import logging
from parsers.doc_parser import DocParser

logger = logging.getLogger(__name__)

# Загружаем промт с шаблонами, если он есть
try:
    with open("prompts/materials_prompt.json", encoding="utf-8") as f:
        materials_prompt = json.load(f)
except FileNotFoundError:
    materials_prompt = {}
    logger.warning("⚠️ Файл prompts/materials_prompt.json не найден, используем дефолтные шаблоны.")

# Шаблоны поиска материалов (если нет внешнего файла)
MATERIAL_PATTERNS = {
    "reinforcement": r"\b(výztuž|Fe\s?\d{3}|R\d{2,3}|ocel)\b",
    "windows": r"\b(okno|okna|PVC|dřevo|sklo)\b",
    "seals": r"\b(těsnění|těsnicí|pryž|guma|EPDM)\b",
    "metal_structures": r"\b(konstrukce z oceli|kovová konstrukce|ocelový rám|nosník)\b"
}

def analyze_materials(doc_paths: list[str]) -> dict:
    """
    Поиск строительных материалов в текстах документов
    """
    parser = DocParser()
    all_text = ""

    # Собираем текст из всех документов
    for path in doc_paths:
        try:
            all_text += "\n" + parser.parse(path)
        except Exception as e:
            logger.error(f"Ошибка при обработке {path}: {e}")

    results = []

    # Проверяем каждую категорию материалов
    for category, pattern in MATERIAL_PATTERNS.items():
        matches = re.findall(pattern, all_text, re.IGNORECASE)
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
