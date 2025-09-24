"""
Улучшенный ConcreteAgentHybrid — агент для комплексного анализа бетонов.
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
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
    def __init__(self, knowledge_base_path="knowledge_base/complete-concrete-knowledge-base.json"):
        self.kb_path = knowledge_base_path
        self.knowledge_base = self._load_knowledge_base()
        self.allowed_grades = set(self._extract_valid_grades_from_kb(self.knowledge_base))

    def _load_knowledge_base(self) -> Dict:
        with open(self.kb_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_valid_grades_from_kb(self, kb: Dict) -> List[str]:
        grades = []
        grades.extend(kb.get("strength_classes", {}).get("standard", {}).keys())
        grades.extend(kb.get("strength_classes", {}).get("uhpc", {}).keys())
        grades.extend(kb.get("concrete_types_by_density", {}).get("lehký_beton", {}).get("strength_classes", []))
        return grades

    def _normalize_concrete_grade(self, raw: str) -> str:
        return raw.upper().replace(" ", "").strip()

    def _local_concrete_analysis(self, text: str) -> List[ConcreteMatch]:
        results = []
        pattern = r'\b(?:LC|C)\d{1,3}/\d{1,3}\b'
        matches = re.finditer(pattern, text)
        for match in matches:
            grade = self._normalize_concrete_grade(match.group())
            if grade not in self.allowed_grades:
                continue
            context_window = 50
            start, end = match.start(), match.end()
            context = text[max(0, start - context_window):min(len(text), end + context_window)]
            if not re.search(r'\b(beton(u|em|y)?|třída|stupeň|XC\d|XF\d|XD\d|XA\d|XM\d)\b', context, re.IGNORECASE):
                continue
            if len(grade) > 8 or '/' not in grade or re.match(r'C\d{4,}', grade):
                continue
            results.append(ConcreteMatch(
                grade=grade,
                context=context,
                location="text",
                confidence=0.95,
                method="regex"
            ))
        return results

    def __init__(self, knowledge_base_path="knowledge_base/complete-concrete-knowledge-base.json"):
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

    def _local_concrete_analysis(self, text: str) -> Dict[str, Any]:
        """Локальный анализ текста на наличие марок бетона"""
        all_matches = []
        
        for pattern in self.concrete_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                grade = self._normalize_concrete_grade(match.group().strip())
                context = text[max(0, match.start()-100):match.end()+100]
                location = self._identify_structural_element(context)
                
                all_matches.append(ConcreteMatch(
                    grade=grade,
                    context=context.strip(),
                    location=location,
                    confidence=0.9,
                    method='regex',
                    coordinates=None
                ))
        
        # Дедупликация
        unique_matches = {}
        for match in all_matches:
            key = match.grade
            if key not in unique_matches or match.confidence > unique_matches[key].confidence:
                unique_matches[key] = match
        
        return {
            'concrete_summary': [
                {
                    'grade': match.grade,
                    'location': match.location,
                    'context': match.context[:200],
                    'confidence': match.confidence,
                    'method': match.method
                }
                for match in unique_matches.values()
            ],
            'analysis_method': 'local',
            'total_matches': len(unique_matches),
            'success': True
        }

    def _normalize_concrete_grade(self, grade: str) -> str:
        """Нормализует обозначение марки бетона"""
        normalized = re.sub(r'\s+', '', grade.upper())
        normalized = re.sub(r'^B(\d+)$', r'C\1/\1', normalized)  # B20 -> C20/25
        normalized = re.sub(r'^(\d+)$', r'C\1', normalized)       # 30 -> C30
        return normalized

    def _identify_structural_element(self, context: str) -> str:
        """Определяет тип конструктивного элемента из контекста"""
        context_upper = context.upper()
        
        for element, info in self.structural_elements.items():
            if element in context_upper:
                return f"{element} ({info['en']})"
        
        for element, info in self.structural_elements.items():
            if any(part in context_upper for part in element.split()):
                return f"{element} ({info['en']}) - частичное совпадение"
        
        return "неопределено"

    async def _claude_concrete_analysis(self, text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """Анализ через Claude с расширенным контекстом"""
        if not self.claude_client:
            return {"success": False, "error": "Claude client not available"}
        
        try:
            result = await self.claude_client.analyze_concrete_with_claude(text, smeta_data)
            
            return {
                'concrete_summary': result.get('claude_analysis', {}).get('concrete_grades', []),
                'analysis_method': 'claude_enhanced',
                'success': True,
                'tokens_used': result.get('tokens_used', 0),
                'raw_response': result.get('raw_response', '')
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка Claude анализа: {e}")
            return {"success": False, "error": str(e)}

    async def analyze(self, doc_paths: List[str], smeta_path: Optional[str] = None,
                      use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
        """
        Комплексный анализ документов с использованием всех возможностей
        """
        logger.info(f"🏗️ Запуск комплексного анализа (режим: {claude_mode})")
        
        all_text = ""
        processed_docs = []
        
        # Обрабатываем каждый документ
        for doc_path in doc_paths:
            try:
                text = self.doc_parser.parse(doc_path)
                all_text += text + "\n"
                
                processed_docs.append({
                    'file': Path(doc_path).name,
                    'type': 'Document',
                    'text_length': len(text)
                })
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки {doc_path}: {e}")
                processed_docs.append({'file': Path(doc_path).name, 'error': str(e)})
        
        # Обрабатываем смету
        smeta_data = []
        if smeta_path:
            try:
                smeta_result = self.smeta_parser.parse(smeta_path)
                smeta_data = smeta_result.get('items', [])
                logger.info(f"📊 Смета обработана: {len(smeta_data)} позиций")
            except Exception as e:
                logger.error(f"❌ Ошибка обработки сметы: {e}")
        
        # Локальный анализ
        local_result = self._local_concrete_analysis(all_text)
        
        # Интеграция с Claude
        final_result = local_result.copy()
        
        if use_claude and self.claude_client:
            claude_result = await self._claude_concrete_analysis(all_text, smeta_data)
            
            if claude_mode == "primary" and claude_result.get("success"):
                final_result = claude_result
            elif claude_mode == "enhancement" and claude_result.get("success"):
                final_result.update({
                    'claude_analysis': claude_result,
                    'analysis_method': 'hybrid_enhanced',
                    'total_tokens_used': claude_result.get('tokens_used', 0)
                })
        
        # Добавляем метаданные
        final_result.update({
            'processed_documents': processed_docs,
            'smeta_items': len(smeta_data),
            'processing_time': 'completed',
            'knowledge_base_version': '3.0'
        })
        
        return final_result

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
