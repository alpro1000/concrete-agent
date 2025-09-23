import os
import pytest
import asyncio
from agents.concrete_agent import analyze_concrete
from tests.generate_test_data import ensure_test_data

@pytest.fixture(scope="session", autouse=True)
def prepare_test_data():
    """Автоматически создаёт тестовые файлы перед тестами"""
    ensure_test_data()
    return {
        "doc_paths": ["tests/test_data/tech_sample.pdf"],
        "smeta_path": "tests/test_data/smeta_sample.xml"
    }

def test_analyze_concrete(prepare_test_data):
    data = prepare_test_data
    result = asyncio.run(analyze_concrete(data["doc_paths"], data["smeta_path"]))

    assert "concrete_summary" in result
    assert isinstance(result["concrete_summary"], list)

    # Проверим, что есть хотя бы одна марка бетона
    assert any("grade" in item for item in result["concrete_summary"])
