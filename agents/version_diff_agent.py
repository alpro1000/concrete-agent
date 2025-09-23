import difflib
import logging
from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser

logger = logging.getLogger(__name__)

def compare_docs(old_paths: list[str], new_paths: list[str]) -> dict:
    """
    Сравнение текстов документов (PDF/DOCX).
    """
    parser = DocParser()

    old_text = ""
    new_text = ""

    for path in old_paths:
        try:
            old_text += parser.parse(path) + "\n"
        except Exception as e:
            logger.error(f"Ошибка чтения старого документа {path}: {e}")

    for path in new_paths:
        try:
            new_text += parser.parse(path) + "\n"
        except Exception as e:
            logger.error(f"Ошибка чтения нового документа {path}: {e}")

    diff = list(difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile="Old Version",
        tofile="New Version",
        lineterm=""
    ))

    return {"document_diff": diff}


def compare_smeta(old_smeta_path: str, new_smeta_path: str) -> dict:
    """
    Сравнение позиций в сметах (Excel).
    """
    parser = SmetaParser()

    try:
        old_positions = parser.parse(old_smeta_path)
    except Exception as e:
        logger.error(f"Ошибка парсинга старой сметы {old_smeta_path}: {e}")
        old_positions = []

    try:
        new_positions = parser.parse(new_smeta_path)
    except Exception as e:
        logger.error(f"Ошибка парсинга новой сметы {new_smeta_path}: {e}")
        new_positions = []

    changes = []
    for i, (old, new) in enumerate(zip(old_positions, new_positions)):
        if old != new:
            changes.append({
                "row": i + 1,
                "old": old,
                "new": new
            })

    return {"smeta_diff": changes}
