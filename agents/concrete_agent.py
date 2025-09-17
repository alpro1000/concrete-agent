from parsers.doc_parser import extract_text_from_docs
from parsers.smeta_parser import extract_smeta_positions
import re

# Регулярные выражения
CONCRETE_REGEX = r"(C\d{1,2}/\d{1,2}( XF\d)?|B\d{1,2})"
ENV_CLASSES_REGEX = r"\b(XO|XC[1-4]|XD[1-3]|XS[1-3]|XF[1-4]|XA[1-3])\b"
WORKABILITY_REGEX = r"\bS[1-5]\b"

# Словарь описаний классов среды (по-чешски)
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


def analyze_concrete(doc_paths, smeta_path):
    doc_text = extract_text_from_docs(doc_paths)
    smeta = extract_smeta_positions(smeta_path)

    # Найти марки бетона
    concrete_matches = re.findall(CONCRETE_REGEX, doc_text)
    concrete_grades = set(m[0] for m in concrete_matches)

    # Найти классы среды и подвижности
    env_classes = set(re.findall(ENV_CLASSES_REGEX, doc_text))
    workability_classes = set(re.findall(WORKABILITY_REGEX, doc_text))

    result = {}

    for grade in concrete_grades:
        used_in = []
        if "základ" in doc_text.lower():
            used_in.append("základy")
        if "věnec" in doc_text.lower():
            used_in.append("věnec")
        if "schodiště" in doc_text.lower():
            used_in.append("schodiště")

        smeta_mentions = [{
            "row": i + 1,
            "description": str(row.get("name", ""))
        } for i, row in enumerate(smeta) if isinstance(row.get("name"), str) and grade in row["name"]]

        result[grade] = {
            "used_in": used_in,
            "mentioned_in_docs": True,
            "found_in_smeta": smeta_mentions
        }

    # Формируем вывод
    env_output = [{
        "code": env,
        "description": ENV_CLASS_DESCRIPTION.get(env, "Popis není k dispozici.")
    } for env in sorted(env_classes)]

    return {
        "concrete_grades": result,
        "environment_classes": env_output,
        "workability_classes": sorted(workability_classes)
    }

