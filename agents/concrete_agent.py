from parsers.doc_parser import extract_text_from_docs
from parsers.smeta_parser import extract_smeta_positions
import re

CONCRETE_REGEX = r"(C\d{1,2}/\d{1,2}( XF\d)?|B\d{1,2})"

def analyze_concrete(doc_paths, smeta_path):
    doc_text = extract_text_from_docs(doc_paths)
    smeta = extract_smeta_positions(smeta_path)
    matches = re.findall(CONCRETE_REGEX, doc_text)
    grades = set(m[0] for m in matches)

    result = {}
    for grade in grades:
        used_in = []
        if "základ" in doc_text.lower():
            used_in.append("základy")
        if "věnec" in doc_text.lower():
            used_in.append("věnec")
        if "schodiště" in doc_text.lower():
            used_in.append("schodiště")

        smeta_mentions = [
            {"row": i+1, "description": row["name"]}
            for i, row in enumerate(smeta)
            if grade in row["name"]
        ]

        result[grade] = {
            "used_in": used_in,
            "mentioned_in_docs": True,
            "found_in_smeta": smeta_mentions
        }

    return result
