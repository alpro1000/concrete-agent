from pdfminer.high_level import extract_text

def parse_pdf(path: str) -> str:
    return extract_text(path)
