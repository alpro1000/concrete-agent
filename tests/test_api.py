import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.generate_test_data import ensure_test_data

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def prepare_test_data():
    """Генерация тестовых файлов"""
    return ensure_test_data()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_analyze_concrete_api(prepare_test_data):
    files = [
        ("docs", ("tech_sample.pdf", open("tests/test_data/tech_sample.pdf", "rb"), "application/pdf")),
        ("smeta", ("smeta_sample.xml", open("tests/test_data/smeta_sample.xml", "rb"), "application/xml")),
    ]
    response = client.post("/analyze/concrete", files=files)
    assert response.status_code == 200
    data = response.json()

    assert "concrete_summary" in data
    assert isinstance(data["concrete_summary"], list)
