# tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app   # исправлено на app.main

client = TestClient(app)

def test_analyze_concrete_endpoint():
    # Заглушки (замени на реальные файлы в tests/data/)
    with open("tests/data/tech_sample.pdf", "rb") as pdf_file, \
         open("tests/data/smeta_sample.xml", "rb") as xml_file:

        files = [
            ("docs", ("sample.pdf", pdf_file, "application/pdf")),
            ("smeta", ("smeta.xml", xml_file, "application/xml"))
        ]

        response = client.post("/analyze/concrete", files=files)  # исправлен путь
        assert response.status_code == 200
        data = response.json()
        assert "concrete_summary" in data
