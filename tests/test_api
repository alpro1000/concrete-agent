# tests/test_api.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_analyze_concrete_endpoint():
    files = [
        ("docs", ("sample.pdf", open("tests/data/tech_sample.pdf", "rb"), "application/pdf")),
        ("smeta", ("smeta.xml", open("tests/data/smeta_sample.xml", "rb"), "application/xml"))
    ]
    response = client.post("/analyze_concrete", files=files)
    assert response.status_code == 200
    assert "concrete_summary" in response.json()
