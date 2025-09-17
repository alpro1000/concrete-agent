from docx import Document
from pdfminer.high_level import extract_text as extract_pdf_text
import os

def extract_text_from_docs(paths):
    content = []
    for p in paths:
        if p.endswith(".pdf"):
            content.append(extract_pdf_text(p))
        elif p.endswith(".docx"):
            doc = Document(p)
            content.append("\n".join([p.text for p in doc.paragraphs]))
        elif p.endswith(".txt"):
            with open(p, "r", encoding="utf-8") as f:
                content.append(f.read())
    return "\n".join(content)
