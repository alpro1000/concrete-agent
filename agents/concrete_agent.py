"""
Агент для анализа бетонных конструкций
"""
import os
import re
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ConcreteAgent:
    """Агент для анализа марок бетона в строительных документах"""
    
    def __init__(self):
        # Паттерны для поиска марок бетона
        self.concrete_patterns = [
            r'\b[BC]\s*\d{1,2}(?:/\d{1,2})?\s*(?:XC|XF|XD|XS|XA|XO)\d?\b',  # B25/30 XC1
            r'\b[BC]\s*\d{1,2}(?:/\d{1,2})?\b',  # B25, C25/30
            r'\bbeton\s+[BC]\s*\d{1,2}(?:/\d{1,2})?\b',  # beton C25/30
            r'\b[BC]\d{1,2}(?:/\d{1,2})?\s+XC\d\b',  # C25/30 XC1
        ]
        
        # Паттерны для определения применения
        self.usage_patterns = {
            'základy': r'\bzáklady?\b|\bzákladové?\b|\bfundament\b',
            'věnce': r'\bvěnce?\b|\bvěnec\b|\bkronšteiny?\b',
            'stropy': r'\bstropy?\b|\bstrop\b|\bdeck\b',
            'stěny': r'\bstěny?\b|\bstěna\b|\bwall\b',
            'sloupy': r'\bsloup\w*\b|\bpillar\b|\bcolumn\b',
            'schodiště': r'\bschodiště\b|\bstairs\b|\bsteps\b',
        }

    def analyze_concrete(self, text: str, smeta_data: Dict = None) -> Dict[str, Any]:
        """
        Основная функция анализа бетона
        """
        logger.info("🏗️ Начинаем анализ бетонных марок")
        # agents/concrete_agent.py

agent_instance = ConcreteAgent()

async def analyze_concrete(doc_paths: list[str], smeta_path: str) -> dict:
    """
    Обёртка для вызова ConcreteAgent из FastAPI.
    """
    text = ""
    for path in doc_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text += f.read() + "\n"
        except Exception as e:
            logger.error(f"❌ Ошибка при чтении {path}: {e}")

    smeta_data = {}
    try:
        with open(smeta_path, "r", encoding="utf-8", errors="ignore") as f:
            smeta_data["content"] = f.read()
    except Exception as e:
        logger.error(f"❌ Ошибка при чтении сметы {smeta_path}: {e}")

    # Вызов метода из ConcreteAgent
    result = agent_instance.analyze_concrete(text, smeta_data)
    result["analysis_method"] = "concrete_agent"
    return result

