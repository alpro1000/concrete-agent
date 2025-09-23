# parsers/merge_parser.py
"""
Модуль для объединения результатов анализа (concrete, materials, smeta, diff)
согласно правилам из prompts/merge_logic_prompt.json
"""

import json
import os
import logging
from typing import Dict, Any

from outputs.save_report import save_merged_report

logger = logging.getLogger(__name__)

# Загружаем правила слияния
MERGE_RULES = {}
PROMPT_PATH = os.path.join("prompts", "merge_logic_prompt.json")

try:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        MERGE_RULES = json.load(f)
    logger.info(f"✅ Загружены правила объединения из {PROMPT_PATH}")
except FileNotFoundError:
    logger.warning(f"⚠️ Файл {PROMPT_PATH} не найден. Используем дефолтные правила.")
    MERGE_RULES = {
        "conflict_resolution": {"strategy": "prefer_concrete_agent"},
        "output_format": {"final_report": "json"}
    }


def merge_results(
    concrete_data: Dict[str, Any] = None,
    materials_data: Dict[str, Any] = None,
    smeta_data: Dict[str, Any] = None,
    diff_data: Dict[str, Any] = None,
    output_path: str = "outputs/merged_report.json"
) -> Dict[str, Any]:
    """
    Объединяет результаты разных агентов в единый JSON-отчёт.

    :param concrete_data: результат от concrete_agent
    :param materials_data: результат от materials_agent
    :param smeta_data: результат от smetny_inzenyr
    :param diff_data: результат от version_diff_agent
    :param output_path: путь для сохранения финального отчёта
    :return: объединённый словарь
    """

    logger.info("🔄 Объединение результатов анализа")

    final_report: Dict[str, Any] = {
        "concrete": concrete_data or {},
        "materials": materials_data or {},
        "smeta": smeta_data or {},
        "diff": diff_data or {},
        "metadata": {
            "merge_strategy": MERGE_RULES.get("merge_strategy", {}),
            "conflict_resolution": MERGE_RULES.get("conflict_resolution", {}),
        }
    }

    # --- Простейшие правила объединения ---
    if concrete_data and materials_data:
        # пример: если встречается "бетон + арматура" → помечаем связку
        for mat in materials_data.get("materials_found", []):
            if "ocel" in mat.get("found_terms", []):
                final_report.setdefault("relations", []).append(
                    {"material": "steel", "linked_with": "concrete"}
                )

    if smeta_data and concrete_data:
        # если смета упоминает бетонные марки — связываем
        for grade_info in concrete_data.get("concrete_summary", []):
            mentions = grade_info.get("smeta_mentions", [])
            if mentions:
                final_report.setdefault("cross_links", []).append(
                    {"grade": grade_info["grade"], "smeta_mentions": mentions}
                )

    # --- Сохраняем результат ---
    save_merged_report(final_report, output_path)

    logger.info(f"📊 Итоговый отчёт собран и сохранён в {output_path}")
    return final_report
