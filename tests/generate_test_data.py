import os
from fpdf import FPDF

# Папка с тестовыми данными
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")

def ensure_test_data():
    """
    Создаёт тестовые файлы (PDF и XML) если их ещё нет.
    Возвращает словарь с путями к файлам.
    """
    os.makedirs(TEST_DATA_DIR, exist_ok=True)

    # === 1. PDF-документ ===
    pdf_path = os.path.join(TEST_DATA_DIR, "tech_sample.pdf")
    if not os.path.exists(pdf_path):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        # Use ASCII-safe text to avoid Unicode issues
        pdf.multi_cell(
            0, 10,
            "Projektova dokumentace\n"
            "Pouzity beton: C25/30 XC2 XF1\n"
            "Pouzita vyztuz: Fe500\n"
        )
        pdf.output(pdf_path)
        print(f"✅ Сгенерирован {pdf_path}")
    else:
        print(f"ℹ️ Уже существует {pdf_path}")

    # === 2. XML-смета ===
    xml_path = os.path.join(TEST_DATA_DIR, "smeta_sample.xml")
    if not os.path.exists(xml_path):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<smeta>
  <row>
    <code>001</code>
    <description>Monoliticka zakladova deska C25/30</description>
    <qty>10</qty>
    <unit>m3</unit>
  </row>
  <row>
    <code>002</code>
    <description>Zelezobetorovy venec C25/30</description>
    <qty>5</qty>
    <unit>m3</unit>
  </row>
</smeta>
"""
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"✅ Сгенерирован {xml_path}")
    else:
        print(f"ℹ️ Уже существует {xml_path}")

    return {"pdf": pdf_path, "xml": xml_path}


if __name__ == "__main__":
    ensure_test_data()
