"""
Унифицированный ConcreteAgent - единственный агент для анализа бетона
agents/concrete_agent.py - ФИНАЛЬНАЯ ВЕРСИЯ
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# Централизованные импорты парсеров
try:
    from services.doc_parser import DocParser
except ImportError:
    from parsers.doc_parser import DocParser

from parsers.smeta_parser import SmetaParser

# Централизованные сервисы
try:
    from app.core.llm_service import get_llm_service
    from app.core.prompt_loader import get_prompt_loader
    CENTRALIZED_LLM_AVAILABLE = True
except ImportError:
    CENTRALIZED_LLM_AVAILABLE = False
    try:
        from utils.claude_client import get_claude_client
    except ImportError:
        get_claude_client = None

# Утилиты
from utils.czech_preprocessor import get_czech_preprocessor
from utils.volume_analyzer import get_volume_analyzer
from utils.report_generator import get_report_generator
from utils.knowledge_base_service import get_knowledge_service

# Вспомогательные агенты
try:
    from agents.concrete_volume_agent import get_concrete_volume_agent
except ImportError:
    get_concrete_volume_agent = None

# Сохранение отчетов
try:
    from outputs.save_report import save_merged_report
except ImportError:
    save_merged_report = None

logger = logging.getLogger(__name__)

@dataclass
class ConcreteGrade:
    """Унифицированная структура для найденной марки бетона"""
    grade: str
    exposure_classes: List[str]
    context: str
    location: str
    confidence: float
    source_document: str
    line_number: Optional[int] = None
    volume_m3: Optional[float] = None
    cost: Optional[float] = None
    method: str = "regex"

class UnifiedConcreteAgent:
    """Единый агент для всех операций с бетоном"""
    
    def __init__(self, knowledge_base_path: str = "knowledge_base/complete-concrete-knowledge-base.json"):
        logger.info("🏗️ Инициализация UnifiedConcreteAgent...")
        
        # Базовые сервисы
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        
        # Утилиты и сервисы
        self.knowledge_service = get_knowledge_service()
        self.czech_preprocessor = get_czech_preprocessor()
        self.volume_analyzer = get_volume_analyzer()
        self.report_generator = get_report_generator()
        
        # Опциональный volume agent
        self.volume_agent = get_concrete_volume_agent() if get_concrete_volume_agent else None
        
        # LLM сервисы
        self._init_llm_services()
        
        # База знаний
        self.allowed_grades = set(self.knowledge_service.get_all_concrete_grades())
        self.context_keywords = list(self.knowledge_service.get_context_keywords())
        logger.info(f"✅ Загружено {len(self.allowed_grades)} допустимых марок бетона")
        
        # Legacy база знаний для обратной совместимости
        self._load_legacy_knowledge_base(knowledge_base_path)
        
        # Паттерны для поиска
        self._init_patterns()
        
        # Конструктивные элементы
        self._init_structural_elements()
        
        logger.info("✅ UnifiedConcreteAgent инициализирован успешно")
    
    def _init_llm_services(self):
        """Инициализация LLM сервисов"""
        if CENTRALIZED_LLM_AVAILABLE:
            self.llm_service = get_llm_service()
            self.prompt_loader = get_prompt_loader()
            self.use_centralized_llm = True
            logger.info("✅ Используется централизованный LLM сервис")
        else:
            if get_claude_client:
                self.claude_client = get_claude_client()
                self.use_centralized_llm = False
                logger.warning("⚠️ Используется legacy Claude client")
            else:
                self.claude_client = None
                self.use_centralized_llm = False
                logger.warning("⚠️ LLM сервисы недоступны")
    
    def _load_legacy_knowledge_base(self, path: str):
        """Загрузка legacy базы знаний"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.knowledge_base = json.load(f)
            logger.info("📚 Legacy knowledge-base загружен")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить legacy KB: {e}")
            self.knowledge_base = self._create_default_kb()
    
    def _init_patterns(self):
        """Инициализация регулярных выражений"""
        # Основной паттерн для марок бетона
        self.concrete_pattern = r'\b(?:LC|C)\d{1,3}/\d{1,3}\b'
        
        # Расширенные паттерны
        self.concrete_patterns = [
            r'(?i)(?:beton(?:u|em|y|ové|ová)?|betónová?)\s+(?:třídy?\s+)?((?:LC)?C\d{1,3}/\d{1,3})',
            r'(?i)\b((?:LC)?C\d{1,3}/\d{1,3})\b',
            r'(?i)(?:beton(?:u|em|y)?)\s+(?:třídy?\s+)?(B\d{1,2})',
            r'(?i)\b(B\d{1,2})\b(?=\s|$|[,.])',
        ]
        
        # Паттерны для классов воздействия
        self.exposure_patterns = [
            r'\b(X[CDFASM]\d*)\b',
            r'\b(XO)\b'
        ]
    
    def _init_structural_elements(self):
        """Инициализация словаря конструктивных элементов"""
        self.structural_elements = {
            'OPĚRA': {'en': 'abutment', 'applications': ['XC4', 'XD1', 'XF2']},
            'PILÍŘ': {'en': 'pier', 'applications': ['XC4', 'XD3', 'XF4']},
            'ŘÍMSA': {'en': 'cornice', 'applications': ['XC4', 'XD3', 'XF4']},
            'MOSTOVKA': {'en': 'deck', 'applications': ['XC4', 'XD3', 'XF4']},
            'ZÁKLAD': {'en': 'foundation', 'applications': ['XC1', 'XC2', 'XA1']},
            'VOZOVKA': {'en': 'roadway', 'applications': ['XF2', 'XF4', 'XD1']},
            'STĚNA': {'en': 'wall', 'applications': ['XC1', 'XC3', 'XC4']},
            'DESKA': {'en': 'slab', 'applications': ['XC1', 'XC2']},
        }
    
    def _create_default_kb(self) -> Dict:
        """Создает минимальную базу знаний"""
        return {
            "strength_classes": {
                "standard": {
                    "C12/15": {"fck": 12, "fcm": 20},
                    "C16/20": {"fck": 16, "fcm": 24},
                    "C20/25": {"fck": 20, "fcm": 28},
                    "C25/30": {"fck": 25, "fcm": 33},
                    "C30/37": {"fck": 30, "fcm": 38},
                }
            }
        }
    
    def _parse_document(self, doc_path: str) -> str:
        """Унифицированный метод парсинга документа"""
        try:
            # Используем doc_parser.parse() напрямую
            text = self.doc_parser.parse(doc_path)
            if text and text.strip():
                return text
            else:
                logger.warning(f"⚠️ Пустой результат парсинга для {doc_path}")
                return ""
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {doc_path}: {e}")
            return ""
    
    def _extract_grades_from_text(self, text: str, source_document: str) -> List[ConcreteGrade]:
        """Извлекает марки бетона из текста"""
        if not text:
            return []
        
        # Предобработка чешского текста
        preprocessed = self.czech_preprocessor.preprocess_document_text(text)
        fixed_text = preprocessed['fixed_text']
        logger.info(f"🇨🇿 Применено {preprocessed['changes_count']} исправлений диакритики")
        
        grades = []
        lines = fixed_text.split('\n')
        
        for line_num, line in enumerate(lines):
            # Поиск марок бетона
            for match in re.finditer(self.concrete_pattern, line, re.IGNORECASE):
                grade = self._normalize_concrete_grade(match.group())
                
                # Валидация марки
                if not self._is_valid_grade(grade):
                    continue
                
                # Получаем контекст
                context = self._get_line_context(lines, line_num)
                
                # Извлекаем классы воздействия
                exposure_classes = self._extract_exposure_classes(context)
                
                # Определяем конструктивный элемент
                location = self.czech_preprocessor.identify_construction_element_enhanced(context)
                
                # Создаем объект марки
                concrete_grade = ConcreteGrade(
                    grade=grade,
                    exposure_classes=exposure_classes,
                    context=context[:200],
                    location=location,
                    confidence=self._calculate_confidence(grade, context),
                    source_document=source_document,
                    line_number=line_num + 1,
                    method='regex_enhanced'
                )
                
                grades.append(concrete_grade)
        
        return grades
    
    def _normalize_concrete_grade(self, grade: str) -> str:
        """Нормализует обозначение марки бетона"""
        if not grade:
            return ""
        return grade.upper().strip().replace(" ", "")
    
    def _is_valid_grade(self, grade: str) -> bool:
        """Проверяет валидность марки"""
        # Проверка формата
        if not re.match(r'^(?:LC|C)\d{1,3}/\d{1,3}$', grade):
            if not re.match(r'^B\d{1,2}$', grade):
                return False
        
        # Проверка в базе знаний
        return grade in self.allowed_grades or self.knowledge_service.is_valid_concrete_grade(grade)
    
    def _extract_exposure_classes(self, context: str) -> List[str]:
        """Извлекает классы воздействия"""
        classes = []
        for pattern in self.exposure_patterns:
            matches = re.findall(pattern, context)
            classes.extend(matches)
        return list(set(classes))
    
    def _calculate_confidence(self, grade: str, context: str) -> float:
        """Вычисляет уверенность в марке"""
        confidence = 0.5
        
        if grade in self.allowed_grades:
            confidence += 0.3
        
        context_lower = context.lower()
        for keyword in self.context_keywords:
            if keyword in context_lower:
                confidence += 0.1
                break
        
        if self._extract_exposure_classes(context):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _get_line_context(self, lines: List[str], line_num: int, window: int = 2) -> str:
        """Получает контекст вокруг строки"""
        start = max(0, line_num - window)
        end = min(len(lines), line_num + window + 1)
        return ' '.join(lines[start:end]).strip()
    
    async def analyze(self, doc_paths: List[str], 
                     smeta_path: Optional[str] = None,
                     use_llm: bool = False,
                     include_volumes: bool = False) -> Dict[str, Any]:
        """
        Главный метод анализа
        
        Args:
            doc_paths: Список документов для анализа
            smeta_path: Путь к смете (опционально)
            use_llm: Использовать ли LLM для улучшения анализа
            include_volumes: Включить ли анализ объемов
        """
        logger.info(f"🚀 Запуск анализа: {len(doc_paths)} документов")
        
        all_grades = []
        all_text = ""
        processed_docs = []
        
        # Обработка основных документов
        for doc_path in doc_paths:
            try:
                text = self._parse_document(doc_path)
                if text:
                    all_text += text + "\n"
                    grades = self._extract_grades_from_text(text, doc_path)
                    all_grades.extend(grades)
                    
                    processed_docs.append({
                        'file': Path(doc_path).name,
                        'text_length': len(text),
                        'grades_found': len(grades)
                    })
                    
            except Exception as e:
                logger.error(f"❌ Ошибка обработки {doc_path}: {e}")
                processed_docs.append({
                    'file': Path(doc_path).name,
                    'error': str(e)
                })
        
        # Обработка сметы
        smeta_data = []
        if smeta_path:
            try:
                smeta_data = self.smeta_parser.parse(smeta_path)
                if smeta_data:
                    # Извлекаем марки из сметы
                    smeta_text = self._extract_text_from_smeta(smeta_data)
                    if smeta_text:
                        smeta_grades = self._extract_grades_from_text(smeta_text, smeta_path)
                        all_grades.extend(smeta_grades)
                    logger.info(f"📊 Обработано {len(smeta_data)} позиций сметы")
            except Exception as e:
                logger.error(f"❌ Ошибка обработки сметы: {e}")
        
        # Дедупликация марок
        unique_grades = self._deduplicate_grades(all_grades)
        
        # Базовый результат
        result = {
            'success': True,
            'concrete_summary': [self._grade_to_dict(g) for g in unique_grades],
            'total_grades_found': len(unique_grades),
            'unique_grades': list(set(g.grade for g in unique_grades)),
            'processed_documents': processed_docs,
            'analysis_method': 'local_enhanced',
            'smeta_items': len(smeta_data)
        }
        
        # Добавляем анализ объемов если запрошено
        if include_volumes and self.volume_agent:
            try:
                volumes = await self.volume_agent.analyze_volumes_from_documents(doc_paths, smeta_path)
                result['volumes'] = volumes
                result['volume_summary'] = self.volume_agent.create_volume_summary(volumes)
                logger.info(f"📊 Найдено объемов: {len(volumes)}")
            except Exception as e:
                logger.error(f"❌ Ошибка анализа объемов: {e}")
        
        # Улучшение через LLM если запрошено
        if use_llm and self._is_llm_available():
            try:
                llm_result = await self._enhance_with_llm(all_text, smeta_data)
                if llm_result.get('success'):
                    result['llm_enhancement'] = llm_result
                    result['analysis_method'] = 'hybrid_llm_enhanced'
            except Exception as e:
                logger.error(f"❌ Ошибка LLM анализа: {e}")
        
        # Сохраняем отчет если доступна функция
        if save_merged_report:
            try:
                save_merged_report(result, "outputs/concrete_analysis_report.json")
                logger.info("💾 Отчет сохранен")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось сохранить отчет: {e}")
        
        return result
    
    def _extract_text_from_smeta(self, smeta_data: List[Dict]) -> str:
        """Извлекает текст из структурированных данных сметы"""
        text_parts = []
        for row in smeta_data:
            if isinstance(row, dict):
                desc = row.get('description', '')
                if desc:
                    text_parts.append(desc)
        return '\n'.join(text_parts)
    
    def _deduplicate_grades(self, grades: List[ConcreteGrade]) -> List[ConcreteGrade]:
        """Удаляет дубликаты марок"""
        seen = {}
        for grade in grades:
            key = f"{grade.grade}_{grade.location}"
            if key not in seen or grade.confidence > seen[key].confidence:
                seen[key] = grade
        return list(seen.values())
    
    def _grade_to_dict(self, grade: ConcreteGrade) -> Dict[str, Any]:
        """Преобразует объект марки в словарь"""
        return {
            'grade': grade.grade,
            'exposure_classes': grade.exposure_classes,
            'location': grade.location,
            'context': grade.context,
            'confidence': round(grade.confidence, 2),
            'source_document': grade.source_document,
            'line_number': grade.line_number,
            'method': grade.method
        }
    
    def _is_llm_available(self) -> bool:
        """Проверяет доступность LLM"""
        if self.use_centralized_llm:
            return self.llm_service is not None
        else:
            return self.claude_client is not None
    
    async def _enhance_with_llm(self, text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """Улучшение анализа через LLM"""
        if self.use_centralized_llm:
            return await self._centralized_llm_analysis(text, smeta_data)
        elif self.claude_client:
            return await self._legacy_claude_analysis(text, smeta_data)
        return {'success': False, 'error': 'No LLM available'}
    
    async def _centralized_llm_analysis(self, text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """Анализ через централизованный LLM сервис"""
        try:
            system_prompt = self.prompt_loader.get_system_prompt("concrete")
            
            # Формируем промпт
            user_prompt = f"""
            Analyze this construction document for concrete grades and specifications.
            Find all concrete grades (C25/30, LC20/25, etc.) with:
            - Exposure classes (XC, XF, XD, etc.)
            - Structural elements
            - Volumes if mentioned
            
            Document text (first 5000 chars):
            {text[:5000]}
            
            Return JSON with found concrete grades.
            """
            
            response = await self.llm_service.run_prompt(
                provider='claude',
                prompt=user_prompt,
                system_prompt=system_prompt,
                model='sonnet'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Centralized LLM error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _legacy_claude_analysis(self, text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """Legacy анализ через Claude client"""
        try:
            result = await self.claude_client.analyze_concrete_with_claude(text, smeta_data)
            return {
                'success': True,
                'concrete_grades': result.get('claude_analysis', {}).get('concrete_grades', [])
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_summary(self, grades: List[ConcreteGrade]) -> Dict[str, Any]:
        """Создает сводку по найденным маркам"""
        if not grades:
            return {
                'total_found': 0,
                'unique_grades': [],
                'by_document': {},
                'by_element': {}
            }
        
        unique = list(set(g.grade for g in grades))
        
        by_doc = {}
        for g in grades:
            doc = g.source_document
            if doc not in by_doc:
                by_doc[doc] = []
            by_doc[doc].append(g.grade)
        
        by_element = {}
        for g in grades:
            elem = g.location or 'Unknown'
            if elem not in by_element:
                by_element[elem] = []
            by_element[elem].append(g.grade)
        
        return {
            'total_found': len(grades),
            'unique_grades': unique,
            'by_document': by_doc,
            'by_element': by_element
        }
    
    def save_comprehensive_reports(self, analysis_result: Dict[str, Any], 
                                   output_dir: str = "outputs", 
                                   language: str = "cz") -> Dict[str, str]:
        """
        Сохраняет все виды отчетов
        """
        saved_files = {}
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Генератор отчетов
        generator = get_report_generator(language)
        
        # Markdown отчет
        markdown_file = output_path / f"concrete_analysis_report_{language}.md"
        try:
            if hasattr(generator, 'save_markdown_report') and generator.save_markdown_report(analysis_result, str(markdown_file)):
                saved_files['markdown'] = str(markdown_file)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить Markdown отчет: {e}")
        
        # JSON данные для Excel
        json_file = output_path / f"concrete_analysis_data_{language}.json"
        try:
            if hasattr(generator, 'save_json_data') and generator.save_json_data(analysis_result, str(json_file)):
                saved_files['json'] = str(json_file)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить JSON данные: {e}")
        
        # Оригинальный JSON отчет
        json_report_file = output_path / "concrete_analysis_report.json"
        if save_merged_report:
            try:
                save_merged_report(analysis_result, str(json_report_file))
                saved_files['json_report'] = str(json_report_file)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось сохранить JSON отчет: {e}")
        
        logger.info(f"💾 Сохранено {len(saved_files)} файлов отчетов")
        return saved_files


# ==============================
# 🔧 Глобальный экземпляр
# ==============================

_concrete_agent = None

def get_concrete_agent() -> UnifiedConcreteAgent:
    """Получение глобального экземпляра агента"""
    global _concrete_agent
    if _concrete_agent is None:
        _concrete_agent = UnifiedConcreteAgent()
        logger.info("✅ UnifiedConcreteAgent инициализирован (singleton)")
    return _concrete_agent

# Обратная совместимость с ConcreteAgentHybrid
def get_hybrid_agent() -> UnifiedConcreteAgent:
    """Получение глобального экземпляра агента (обратная совместимость)"""
    return get_concrete_agent()

# ==============================
# 🚀 API функции для обратной совместимости
# ==============================

async def analyze_concrete(doc_paths: List[str], 
                          smeta_path: Optional[str] = None,
                          use_claude: bool = True,
                          claude_mode: str = "enhancement") -> Dict[str, Any]:
    """
    API функция для обратной совместимости
    Мапит старые параметры на новые
    """
    agent = get_hybrid_agent()  # Используем обратную совместимость
    
    # Мапинг старых параметров
    use_llm = use_claude
    include_volumes = True  # По умолчанию включаем объемы
    
    result = await agent.analyze(
        doc_paths=doc_paths,
        smeta_path=smeta_path,
        use_llm=use_llm,
        include_volumes=include_volumes
    )
    
    # Сохраняем результат если доступна функция
    if save_merged_report:
        try:
            save_merged_report(result, "outputs/concrete_analysis_report.json")
            logger.info("💾 Отчет сохранен в outputs/concrete_analysis_report.json")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить отчёт: {e}")
    
    return result

async def analyze_concrete_with_volumes(doc_paths: List[str],
                                       smeta_path: Optional[str] = None,
                                       use_claude: bool = True,
                                       claude_mode: str = "enhancement",
                                       language: str = "cz") -> Dict[str, Any]:
    """
    API функция с объемами для обратной совместимости
    """
    agent = get_hybrid_agent()  # Используем обратную совместимость
    
    # Устанавливаем язык для отчетов
    agent.report_generator = get_report_generator(language)
    
    result = await agent.analyze(
        doc_paths=doc_paths,
        smeta_path=smeta_path,
        use_llm=use_claude,
        include_volumes=True
    )
    
    # Добавляем метаданные языка
    result['report_language'] = language
    
    # Сохранение отчетов если доступны функции сохранения
    if hasattr(agent, 'save_comprehensive_reports'):
        try:
            saved_files = agent.save_comprehensive_reports(result, "outputs", language)
            result['saved_reports'] = saved_files
            
            # Логирование результатов
            concrete_count = len(result.get('concrete_summary', []))
            volume_count = result.get('volume_entries_found', 0)
            
            logger.info(f"✅ Анализ завершен:")
            logger.info(f"   - Найдено марок бетона: {concrete_count}")
            logger.info(f"   - Найдено объемов: {volume_count}")
            logger.info(f"   - Сохранено отчетов: {len(saved_files)}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить отчеты: {e}")
    
    return result

# ==============================
# 🧪 Тестирование
# ==============================

async def test_unified_agent():
    """Тестовая функция"""
    print("🧪 Тестирование UnifiedConcreteAgent")
    print("=" * 50)
    
    agent = get_concrete_agent()
    
    # Тестовый текст
    test_text = """
    MOSTNÍ OPĚRA ZE ŽELEZOBETONU C30/37 XD2 XF1
    Použitý beton: C25/30 XC2
    Základová deska - monolitický beton C20/25
    """
    
    # Тестовое извлечение
    grades = agent._extract_grades_from_text(test_text, "test.pdf")
    summary = agent.create_summary(grades)
    
    print(f"✅ Найдено марок: {summary['total_found']}")
    print(f"📋 Уникальные марки: {summary['unique_grades']}")
    
    for grade in grades:
        print(f"\n  • {grade.grade}")
        print(f"    Классы: {', '.join(grade.exposure_classes)}")
        print(f"    Элемент: {grade.location}")
        print(f"    Уверенность: {grade.confidence:.2%}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_unified_agent())