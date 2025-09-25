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
        # Загружаем базу знаний
        try:
            with open(knowledge_base_path, "r", encoding="utf-8") as f:
                self.knowledge_base = json.load(f)
            logger.info("📚 Knowledge-base загружен успешно")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить knowledge-base: {e}")
            self.knowledge_base = self._create_default_kb()

        # Извлекаем допустимые марки из базы знаний
        self.allowed_grades = set(self._extract_valid_grades_from_kb(self.knowledge_base))
        logger.info(f"🎯 Загружено {len(self.allowed_grades)} допустимых марок бетона")

        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        self.claude_client = get_claude_client() if settings.is_claude_enabled() else None

        # Строгий паттерн для поиска марок бетона (только стандартные форматы)
        self.concrete_pattern = r'\b(?:LC|C)\d{1,3}/\d{1,3}\b'

        # Контекстные слова для фильтрации (чешские термины)
        self.context_keywords = [
            'beton', 'betonu', 'betonem', 'betony', 'betonové', 'betonových',
            'třída', 'třídy', 'třídu', 'třídě',
            'stupeň', 'stupně', 'stupni',
            'odolnost', 'odolnosti',
            'pevnost', 'pevnosti',
            'XC1', 'XC2', 'XC3', 'XC4',
            'XA1', 'XA2', 'XA3',
            'XF1', 'XF2', 'XF3', 'XF4',
            'XD1', 'XD2', 'XD3',
            'XM1', 'XM2', 'XM3'
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

    def _extract_valid_grades_from_kb(self, kb: Dict) -> List[str]:
        """Извлекает допустимые марки бетона из базы знаний"""
        grades = []
        
        # Стандартные классы прочности
        standard_classes = kb.get("strength_classes", {}).get("standard", {})
        if standard_classes:
            grades.extend(standard_classes.keys())
        
        # UHPC классы
        uhpc_classes = kb.get("strength_classes", {}).get("uhpc", {})
        if uhpc_classes:
            grades.extend(uhpc_classes.keys())
        
        # Легкий бетон
        lightweight_classes = kb.get("concrete_types_by_density", {}).get("lehký_beton", {}).get("strength_classes", [])
        if lightweight_classes:
            grades.extend(lightweight_classes)
        
        # Нормализуем все марки
        normalized_grades = []
        for grade in grades:
            normalized = self._normalize_concrete_grade(grade)
            if normalized and self._is_valid_grade_format(normalized):
                normalized_grades.append(normalized)
        
        return normalized_grades

    def _create_default_kb(self) -> Dict:
        """Создает минимальную базу знаний по умолчанию"""
        return {
            "strength_classes": {
                "standard": {
                    "C12/15": {"fck": 12, "fcm": 20},
                    "C16/20": {"fck": 16, "fcm": 24},
                    "C20/25": {"fck": 20, "fcm": 28},
                    "C25/30": {"fck": 25, "fcm": 33},
                    "C30/37": {"fck": 30, "fcm": 38},
                    "C35/45": {"fck": 35, "fcm": 43},
                    "C40/50": {"fck": 40, "fcm": 48},
                    "C45/55": {"fck": 45, "fcm": 53},
                    "C50/60": {"fck": 50, "fcm": 58}
                },
                "uhpc": {
                    "C80/95": {"fck": 80, "fcm": 88},
                    "C90/105": {"fck": 90, "fcm": 98}
                }
            },
            "concrete_types_by_density": {
                "lehký_beton": {
                    "strength_classes": ["LC12/13", "LC16/18", "LC20/22", "LC25/28", "LC30/33", "LC35/38", "LC40/44", "LC45/50", "LC50/55", "LC55/60", "LC60/66", "LC70/77", "LC80/88"]
                }
            },
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

    def _is_valid_grade_format(self, grade: str) -> bool:
        """Проверяет корректность формата марки бетона"""
        if not grade or len(grade) > 8:
            return False
        
        if '/' not in grade:
            return False
        
        # Проверяем на слишком большие числа
        if re.match(r'C\d{4,}', grade):
            return False
        
        # Проверяем правильный формат
        if not re.match(r'^(?:LC|C)\d{1,3}/\d{1,3}$', grade):
            return False
        
        return True

    def _has_concrete_context(self, text: str, start_pos: int, end_pos: int) -> bool:
        """Проверяет наличие контекстных слов рядом с маркой бетона"""
        context_window = 50
        context_start = max(0, start_pos - context_window)
        context_end = min(len(text), end_pos + context_window)
        context = text[context_start:context_end].lower()
        
        # Создаем паттерн для поиска контекстных слов
        keywords_pattern = '|'.join(re.escape(keyword.lower()) for keyword in self.context_keywords)
        
        return bool(re.search(rf'\b({keywords_pattern})\b', context, re.IGNORECASE))

    def _local_concrete_analysis(self, text: str) -> Dict[str, Any]:
        """Улучшенный локальный анализ текста на наличие марок бетона"""
        all_matches = []
        
        # Используем строгий паттерн для поиска марок
        for match in re.finditer(self.concrete_pattern, text, re.IGNORECASE):
            grade = self._normalize_concrete_grade(match.group().strip())
            
            # Фильтр 1: Марка должна быть в whitelist из базы знаний
            if grade not in self.allowed_grades:
                continue
            
            start_pos, end_pos = match.start(), match.end()
            
            # Фильтр 2: Проверяем контекст (наличие ключевых слов)
            if not self._has_concrete_context(text, start_pos, end_pos):
                continue
            
            # Фильтр 3: Дополнительная проверка формата
            if not self._is_valid_grade_format(grade):
                continue
            
            # Извлекаем расширенный контекст для анализа
            context_window = 100
            context_start = max(0, start_pos - context_window)
            context_end = min(len(text), end_pos + context_window)
            context = text[context_start:context_end]
            
            # Определяем тип конструктивного элемента
            location = self._identify_structural_element(context)
            
            all_matches.append(ConcreteMatch(
                grade=grade,
                context=context.strip(),
                location=location,
                confidence=0.95,  # Высокая уверенность благодаря строгой фильтрации
                method='regex_enhanced',
                coordinates=None
            ))
        
        # Дедупликация с сохранением лучших совпадений
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
            'analysis_method': 'local_enhanced',
            'total_matches': len(unique_matches),
            'success': True,
            'allowed_grades_count': len(self.allowed_grades)
        }

    def _normalize_concrete_grade(self, grade: str) -> str:
        """Нормализует обозначение марки бетона"""
        if not grade:
            return ""
        
        # Базовая нормализация
        normalized = grade.upper().strip().replace(" ", "")
        
        # Убираем лишние символы
        normalized = re.sub(r'[^\w/]', '', normalized)
        
        return normalized

    def _identify_structural_element(self, context: str) -> str:
        """Определяет тип конструктивного элемента из контекста"""
        context_upper = context.upper()
        
        # Точное совпадение
        for element, info in self.structural_elements.items():
            if element in context_upper:
                return f"{element} ({info['en']})"
        
        # Частичное совпадение
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
        
        # Локальный анализ (теперь улучшенный)
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
        except Exception in e:
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
