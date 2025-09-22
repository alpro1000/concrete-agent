# tests/test_concrete_agent.py
from agents.concrete_agent import analyze_concrete

def test_basic_concrete_analysis():
    doc_paths = ["tests/data/tech_sample.pdf"]  # Используй свой тестовый файл
    smeta_path = "tests/data/smeta_sample.xml"  # Используй свою XML-смету

    result = analyze_concrete(doc_paths, smeta_path)
    assert "concrete_summary" in result
    assert isinstance(result["concrete_summary"], list)
    assert any("grade" in c for c in result["concrete_summary"])
