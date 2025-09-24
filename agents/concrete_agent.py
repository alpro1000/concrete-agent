"""
Улучшенный ConcreteAgentHybrid — агент для комплексного анализа бетонов.
Возможности:
- OCR для чертежей с распознаванием марок и мест применения
- Расширенные regex для всех форматов обозначений
- Интеграция с knowledge base
- Парсинг XML смет с кодами
- Улучшение результатов через Claude
"""

import re
import os
import json
import logging
import pdfplumber
import pytesseract
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from xml.etree import ElementTree as ET
from PIL import Image, ImageEnhance
from dataclasses import dataclass

from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from utils.claude_client import get_claude_client
from config.settings import settings
from outputs.save_report import save_merged_report

logger = logging.getLogger(__name__)

@dataclass
class ConcreteMatch:
    """Структура для найденной марки бетона"""
    grade: str
    context: str
    location: str
    confidence: float
    method: str
    coordinates: Optional[Tuple[int, int, int, int]] = None

@dataclass 
class StructuralElement:
    """Структура для конструктивного элемента"""
    name: str
    concrete_grade: Optional[str]
    location: str
    context: str

class ConcreteAgentHybrid:
    def __init__(self, knowledge_base_path="concrete_knowledge_base_v3.json"):
        # Загружаем базу знаний
        try:
            with open(knowledge_base_path, "r", encoding="utf-8") as f:
                self.knowledge_base = json.load(f)
            logger.info("📚 Knowledge-base загружен успешно")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить knowledge-base: {e}")
            self.knowledge_base = self._create_default_kb()

        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        self.claude_client = get_claude_client() if settings.is_claude_enabled() else None

        # Расширенные паттерны для поиска марок бетона
        self.concrete_patterns = [
            r'\bC\d{1,2}/\d{1,2}(?:\s*[-–]\s*[XO][CDFASM]?\d*(?:\s*,\s*[XO][CDFASM]?\d*)*)*\b',
            r'\b[BC]\s*\d{1,2}(?:/\d{1,2})?\b',
            r'\bLC\s*\d{1,2}/\d{1,2}\b',
            r'(?i)(?:beton[uá]?\s+)?(?:tříd[ayě]\s+)?(\d{2}/\d{2}|\d{2,3})\b',
            r'(?i)(?:betony?|betonové[j]?)\s+(?:tříd[yě]\s+)?([BC]?\d{1,2}(?:/\d{1,2})?)',
            r'\b(?:vysokopevnostn[íý]|lehk[ýá]|těžk[ýá])\s+beton\s+([BC]?\d{1,2}(?:/\d{1,2})?)\b',
        ]

        # Конструктивные элементы (чешские термины)
        self.structural_elements = {
            'OPĚRA': {'en': 'abutment', 'applications': ['XC4', 'XD1', 'XF2']},
            'PILÍŘ': {'en': 'pier', 'applications': ['XC4', 'XD3', 'XF4']},
            'ŘÍMSA': {'en': 'cornice', 'applications': ['XC4', 'XD3', 'XF4']},
            'MOSTOVKA': {'en': 'deck', 'applications': ['XC4', 'XD3', 'XF4']},
            'ZÁKLAD': {'en': 'foundation', 'applications': ['XC1', 'XC2', 'XA1']},
            'VOZOVKA': {'en': 'roadway', 'applications': ['XF2', 'XF4', 'XD1']},
            'GARÁŽ': {'en': 'garage', 'applications': ['XD1']},
            'STĚNA': {'en': 'wall', 'applications': ['XC1', 'XC3', 'XC4']},
            'SLOUP': {'en': 'column', 'applications': ['XC1', 'XC3']},
            'SCHODIŠTĚ': {'en': 'stairs', 'applications': ['XC1', 'XC3']},
            'PODKLADNÍ': {'en': 'subgrade', 'applications': ['X0', 'XC1']},
            'NOSNÁ': {'en': 'load-bearing', 'applications': ['XC1', 'XC3']},
            'VĚNEC': {'en': 'tie-beam', 'applications': ['XC2', 'XF1']},
            'DESKA': {'en': 'slab', 'applications': ['XC1', 'XC2']},
            'PREFABRIKÁT': {'en': 'precast', 'applications': ['XC1', 'XC3']},
            'MONOLITICKÝ': {'en': 'monolithic', 'applications': ['XC1', 'XC2']},
        }

        # Коды смет и их соответствия
        self.smeta_codes = {
            '801': 'Prostý beton',
            '802': 'Železobeton monolitický',
            '803': 'Železobeton prefabrikovaný',
            '811': 'Betony speciální',
            '271': 'Konstrukce betonové a železobetonové',
            'HSV': 'Hlavní stavební výroba',
            'PSV': 'Přidružená stavební výroba',
        }

    def _create_default_kb(self) -> Dict:
        """Создает минимальную базу знаний по умолчанию"""
        return {
            "environment_classes": {
                "XC1": {"description": "suché nebo stále mokré", "applications": ["interiér", "základy"]},
                "XC2": {"description": "mokré, občas suché", "applications": ["základy", "spodní stavba"]},
                "XC3": {"description": "středně mokré", "applications": ["kryté prostory"]},
                "XC4": {"description": "střídavě mokré a suché", "applications": ["vnější povrchy"]},
                "XD1": {"description": "chloridy - mírné", "applications": ["garáže", "parkoviště"]},
                "XD3": {"description": "chloridy - silné", "applications": ["mosty", "vozovky"]},
                "XF1": {"description": "mráz - mírný", "applications": ["vnější svislé plochy"]},
                "XF2": {"description": "mráz + soli", "applications": ["silniční konstrukce"]},
                "XF4": {"description": "mráz + soli - extrémní", "applications": ["mostovky", "vozovky"]},
                "XA1": {"description": "chemicky agresivní - slabě", "applications": ["základy", "septiky"]},
            }
        }

    # Все остальные методы остаются теми же...
    # [Здесь продолжение всех методов из оригинального файла]

# ==============================
# 🔧 Глобальные функции
# ==============================

_hybrid_agent = None

def get_hybrid_agent() -> ConcreteAgentHybrid:
    """Получение глобального экземпляра гибридного агента"""
    global _hybrid_agent
    if _hybrid_agent is None:
        _hybrid_agent = ConcreteAgentHybrid()
        logger.info("🤖 ConcreteAgentHybrid инициализирован")
    return _hybrid_agent

# ==============================
# 🚀 API-совместимые функции
# ==============================

async def analyze_concrete(doc_paths: List[str], smeta_path: Optional[str] = None,
                           use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
    """
    Главная функция для анализа бетона - совместима с существующим API
    """
    agent = get_hybrid_agent()
    
    try:
        result = await agent.analyze(doc_paths, smeta_path, use_claude, claude_mode)
        
        # Сохраняем результат
        try:
            save_merged_report(result, "outputs/concrete_analysis_report.json")
            logger.info("💾 Отчет сохранен в outputs/concrete_analysis_report.json")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить отчёт: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в analyze_concrete: {e}")
        return {
            "error": str(e),
            "success": False,
            "analysis_method": "error",
            "concrete_summary": []
        }
