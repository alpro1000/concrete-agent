import difflib
from parsers.doc_parser import extract_text_from_docs
from parsers.smeta_parser import extract_smeta_positions

def compare_docs(old_paths, new_paths):
    old_text = extract_text_from_docs(old_paths)
    new_text = extract_text_from_docs(new_paths)

    diff = list(difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile='Old Version',
        tofile='New Version',
        lineterm=''
    ))

    return {"document_diff": diff}

def compare_smeta(old_smeta_path, new_smeta_path):
    old_positions = extract_smeta_positions(old_smeta_path)
    new_positions = extract_smeta_positions(new_smeta_path)

    changes = []
    for i, (old, new) in enumerate(zip(old_positions, new_positions)):
        if old != new:
            changes.append({
                "row": i + 1,
                "old": old,
                "new": new
            })

    return {"smeta_diff": changes}
