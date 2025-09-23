# tests/test_concrete_agent.py
import asyncio
import pytest
from agents.concrete_agent import analyze_concrete

@pytest.mark.asyncio
async def test_basic_concrete_analysis():
    # Заглушки (замени на реальные файлы в tests/data/)
    doc_paths = ["tests/data/tech_sample.pdf"]
    smeta_path = "tests/data/smeta_sample.xml"

    result = await analyze_concrete(doc_paths, smeta_path)

    assert "concrete_summary" in result
    assert isinstance(result["concrete_summary"], list)
    assert any("grade" in c for c in result["concrete_summary"])
