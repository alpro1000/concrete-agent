import re
import logging
from typing import List, Dict, Any

from parsers.doc_parser import extract_text_from_docs
from parsers.smeta_parser import extract_smeta_positions

# Регулярные выражения
CONCRETE_REGEX = r"\b(C\d{1,2}/\d{1,2}|B\d{1,2})\b"
ENV_CLASSES_REGEX = r"\b(XO|XC[1-4]|XD[1-3]|XS[1-3]|XF[1-4]|XA[1-3])\b"
WORKABILITY_REGEX = r"\bS[1-5]\b"

# Описание классов среды
ENV_CLASS_DESCRIPTION = {
    "XO": "Bez rizika koroze nebo degradace. Pro beton bez výztuže v suchém prostředí.",
    "XC1": "Koroze karbonatací – suché nebo trvale vlhké prostředí.",
    "XC2": "Koroze karbonatací – vlhké, občas suché prostředí.",
    "XC3": "Koroze karbonatací – středně vlhké prostředí.",
    "XC4": "Koroze karbonatací – střídavě vlhké a suché prostředí.",
    "XD1": "Koroze chloridy (mimo mořské vody) – středně vlhké prostředí.",
    "XD2": "Koroze chloridy – vlhké, občas suché prostředí.",
    "XD3": "Koroze chloridy – střídavě vlhké a suché prostředí.",
    "XS1": "Mořská sůl ve vzduchu – povrch vystavený solím.",
    "XS2": "Stálé ponoření do mořské vody.",
    "XS3": "Zóny přílivu, odlivu a rozstřiků mořské vody.",
    "XF1": "Zamrzání/rozmrazování – mírně nasákavé prostředí, bez posypových solí.",
    "XF2": "Zamrzání/rozmrazování – mírně nasákavé, s posypovými solemi.",
    "XF3": "Zamrzání/rozmrazování – silně nasákavé, bez posypových solí.",
    "XF4": "Zamrzání/rozmrazování – silně nasákavé, s posypovými solemi.",
    "XA1": "Slabě agresivní chemické prostředí.",
    "XA2": "Středně agresivní chemické prostředí.",
    "XA3": "Silně agresivní chemické prostředí."
}

# Контексты применения
CONTEXT_PATTERNS = {
    "základy": r"základ",
    "věnec": r"věnec",
    "piloty": r"pilot[ay]?",
    "zdi": r"příčka|zeď|stěna",
    "mostní konstrukce": r"most",
    "schodiště": r"schodiště"
}


def analyze_concrete(doc_paths: List[str], smeta_path: str) -> Dict[str, Any]:
    logging.info("🚀 Старт анализа бетонных марок и сметной документации")

    try:
        doc_text = extract_text_from_docs(doc_paths).lower()
        logging.info("📄 Текст успешно извлечён из проектной документации")

        smeta = extract_smeta_positions(smeta_path)
        logging.info("📊 Данные из сметы успешно получены")

        concrete_data = {}

        for match in re.finditer(CONCRETE_REGEX, doc_text):
            grade = match.group(0)
            logging.debug(f"🔍 Найдена марка бетона: {grade}")

            snippet = doc_text[max(0, match.start() - 150): match.end() + 150]
            env_classes = set(re.findall(ENV_CLASSES_REGEX, snippet))
            workability = set(re.findall(WORKABILITY_REGEX, snippet))

            if grade not in concrete_data:
                concrete_data[grade] = {
                    "environment_classes": set(),
                    "workability_classes": set(),
                    "used_in": set(),
                    "smeta_mentions": []
                }

            concrete_data[grade]["environment_classes"].update(env_classes)
            concrete_data[grade]["workability_classes"].update(workability)

            for ctx, pattern in CONTEXT_PATTERNS.items():
                if re.search(pattern, snippet):
                    logging.debug(f"🏗️ Марка {grade} применяется в контексте: {ctx}")
                    concrete_data[grade]["used_in"].add(ctx)

        # Поиск упоминаний в смете
        for i, row in enumerate(smeta):
            name = str(row.get("name", "")).lower().strip()
            code = str(row.get("code", ""))
            qty = row.get("qty", 0.0)
            unit = row.get("unit", "")

            for grade in concrete_data:
                if grade.lower() in name:
                    logging.debug(f"📌 Совпадение в смете: {grade} → строка {i + 1}")
                    concrete_data[grade]["smeta_mentions"].append({
                        "row": i + 1,
                        "description": name,
                        "code": code,
                        "qty": qty,
                        "unit": unit
                    })

        # Финальный формат
        result = []
        for grade, data in concrete_data.items():
            result.append({
                "grade": grade,
                "used_in": sorted(data["used_in"]),
                "environment_classes": [{
                    "code": cls,
                    "description": ENV_CLASS_DESCRIPTION.get(cls, "Popis není k dispozici.")
                } for cls in sorted(data["environment_classes"])],
                "workability_classes": sorted(data["workability_classes"]),
                "smeta_mentions": data["smeta_mentions"]
            })

        logging.info(f"✅ Анализ завершён. Найдено {len(result)} марок бетона.")
        return {"concrete_summary": result}

    except Exception as e:
        logging.error(f"❌ Ошибка при анализе: {e}")
        return {"error": str(e)}
