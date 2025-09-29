"""
Улучшенный ConcreteAgentHybrid — агент для комплексного анализа бетонов.
agents/concrete_agent.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from services.doc_parser import DocParser
except ImportError:
    # Fallback to old location with warning
    import warnings
    warnings.warn("parsers.doc_parser is deprecated. Use services.doc_parser instead.", DeprecationWarning)
    from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from services.doc_parser import parse_document  # New unified parser

# Import centralized services  
try:
    from app.core.llm_service import get_llm_service
    from app.core.prompt_loader import get_prompt_loader
    CENTRALIZED_LLM_AVAILABLE = True
except ImportError:
    CENTRALIZED_LLM_AVAILABLE = False
    # Fallback to old client
    from utils.claude_client import get_claude_client

from config.settings import settings
from outputs.save_report import save_merged_report
from utils.czech_preprocessor import get_czech_preprocessor
from utils.volume_analyzer import get_volume_analyzer
from utils.report_generator import get_report_generator
from utils.knowledge_base_service import get_knowledge_service
from agents.concrete_volume_agent import get_concrete_volume_agent

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
        # Инициализируем новые сервисы
        self.knowledge_service = get_knowledge_service()
        self.volume_agent = get_concrete_volume_agent()
        self.volume_analyzer = get_volume_analyzer()  # Для обратной совместимости
        self.report_generator = get_report_generator()
        self.czech_preprocessor = get_czech_preprocessor()
        
        # Получаем допустимые марки из нового сервиса
        self.allowed_grades = set(self.knowledge_service.get_all_concrete_grades())
        logger.info(f"🎯 Загружено {len(self.allowed_grades)} допустимых марок бетона")
        
        # Получаем контекстные ключевые слова
        self.context_keywords = list(self.knowledge_service.get_context_keywords())
        
        # Загружаем базу знаний (для обратной совместимости)
        try:
            with open(knowledge_base_path, "r", encoding="utf-8") as f:
                self.knowledge_base = json.load(f)
            logger.info("📚 Legacy knowledge-base загружен успешно")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить legacy knowledge-base: {e}")
            self.knowledge_base = self._create_default_kb()

        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        
        # Initialize LLM services
        if CENTRALIZED_LLM_AVAILABLE:
            self.llm_service = get_llm_service()
            self.prompt_loader = get_prompt_loader()
            self.use_centralized_llm = True
            logger.info("✅ Using centralized LLM service")
        else:
            self.claude_client = get_claude_client()  # Fallback to old client
            self.use_centralized_llm = False
            logger.warning("⚠️ Using legacy Claude client - update recommended")

        # Строгий паттерн для поиска марок бетона (только стандартные форматы)
        self.concrete_pattern = r'\b(?:LC|C)\d{1,3}/\d{1,3}\b'

        # Расширенные чешские ключевые слова
        self.context_keywords = [
            # Основные термины с диакритикой
            'beton', 'betonu', 'betonem', 'betony', 'betonové', 'betonových', 'betonářsk',
            'třída', 'třídy', 'třídu', 'třídě', 'tříd',
            'stupeň', 'stupně', 'stupni',
            'odolnost', 'odolnosti',
            'pevnost', 'pevnosti',
            
            # Коды воздействия
            'XC1', 'XC2', 'XC3', 'XC4',
            'XA1', 'XA2', 'XA3', 
            'XF1', 'XF2', 'XF3', 'XF4',
            'XD1', 'XD2', 'XD3',
            'XM1', 'XM2', 'XM3', 'X0',
            
            # Конструктивные элементы (с исправленной диакритикой)
            'dřík', 'základová', 'část', 'piloty', 'vrtané',
            'říms', 'opěrná', 'zeď', 'konstrukce', 'nosná',
            'podkladní', 'vrstva', 'výztuž', 'ocel',
            'izolace', 'vodotěsn', 'drenážn', 'štěrkodrt',
            'železobetonová', 'monolitický', 'prefabrikát'
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

        # Добавить препроцессор чешского текста
        self.czech_preprocessor = get_czech_preprocessor()

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
        """Улучшенный локальный анализ с предобработкой чешского текста"""
        
        # НОВОЕ: Предобработка чешского текста
        preprocessed = self.czech_preprocessor.preprocess_document_text(text)
        fixed_text = preprocessed['fixed_text']
        
        logger.info(f"🇨🇿 Применено {preprocessed['changes_count']} исправлений диакритики")
        
        all_matches = []
        
        # Используем ИСПРАВЛЕННЫЙ текст для поиска
        for match in re.finditer(self.concrete_pattern, fixed_text, re.IGNORECASE):
            grade = self._normalize_concrete_grade(match.group().strip())
            
            # Фильтр 1: Марка должна быть в whitelist из базы знаний
            if grade not in self.allowed_grades:
                continue
            
            start_pos, end_pos = match.start(), match.end()
            
            # УЛУЧШЕННОЕ извлечение контекста с бОльшим окном (150 символов)
            context = self.czech_preprocessor.enhance_context_window(
                fixed_text, start_pos, end_pos, window_size=150
            )
            
            # Фильтр 2: Проверяем контекст (наличие ключевых слов)
            if not self._has_concrete_context(context, 0, len(context)):
                continue
            
            # Фильтр 3: Дополнительная проверка формата
            if not self._is_valid_grade_format(grade):
                continue
            
            # УЛУЧШЕННОЕ определение конструктивного элемента
            location = self.czech_preprocessor.identify_construction_element_enhanced(context)
            
            all_matches.append(ConcreteMatch(
                grade=grade,
                context=context.strip(),
                location=location,
                confidence=0.95,
                method='regex_enhanced_czech',
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
            'analysis_method': 'local_enhanced_czech',
            'total_matches': len(unique_matches),
            'success': True,
            'allowed_grades_count': len(self.allowed_grades),
            'czech_preprocessing': {
                'diacritic_fixes': preprocessed['changes_count'],
                'original_length': preprocessed['original_length'],
                'fixed_length': preprocessed['fixed_length']
            }
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
        """Определяет тип конструктивного элемента с использованием чешского препроцессора"""
        return self.czech_preprocessor.identify_construction_element_enhanced(context)

    def _analyze_volumes_from_documents(self, doc_paths: List[str], smeta_path: Optional[str] = None) -> List:
        """Анализирует объемы бетона из документов и смет"""
        all_volumes = []
        
        # Анализируем основные документы
        for doc_path in doc_paths:
            try:
                # Use unified parser with MinerU integration
                result = parse_document(doc_path)
                if result["success"] and result["results"]:
                    # Extract text content from parse results
                    text = ""
                    for parse_result in result["results"]:
                        content = parse_result.content
                        if isinstance(content, str):
                            text += content + "\n"
                        elif isinstance(content, dict):
                            # Handle structured content from MinerU
                            text += content.get("text", str(content)) + "\n"
                        else:
                            text += str(content) + "\n"
                    
                    if text.strip():
                        volumes = self.volume_analyzer.analyze_volumes_from_text(
                            text, Path(doc_path).name
                        )
                        all_volumes.extend(volumes)
                        logger.info(f"📊 Найдено объемов в {Path(doc_path).name}: {len(volumes)} (parser: {result['results'][0].parser_used if result['results'] else 'unknown'})")
            except Exception as e:
                logger.error(f"❌ Ошибка анализа объемов в {doc_path}: {e}")
        
        # Анализируем смету, если есть
        if smeta_path and os.path.exists(smeta_path):
            try:
                # Use unified parser for smeta as well
                result = parse_document(smeta_path)
                if result["success"] and result["results"]:
                    smeta_text = ""
                    for parse_result in result["results"]:
                        content = parse_result.content
                        if isinstance(content, str):
                            smeta_text += content + "\n"
                        elif isinstance(content, (list, dict)):
                            # Handle structured smeta data
                            smeta_text += str(content) + "\n"
                        else:
                            smeta_text += str(content) + "\n"
                    
                    if smeta_text.strip():
                        smeta_volumes = self.volume_analyzer.analyze_volumes_from_text(
                            smeta_text, Path(smeta_path).name
                        )
                        all_volumes.extend(smeta_volumes)
                    logger.info(f"📊 Найдено объемов в смете: {len(smeta_volumes)}")
            except Exception as e:
                logger.error(f"❌ Ошибка анализа сметы {smeta_path}: {e}")
        
        return all_volumes

    async def analyze_with_volumes(self, doc_paths: List[str], smeta_path: Optional[str] = None,
                                   use_claude: bool = True, claude_mode: str = "enhancement",
                                   language: str = "cz") -> Dict[str, Any]:
        """
        Расширенный анализ с извлечением объемов и генерацией отчетов
        """
        logger.info(f"🏗️ Запуск комплексного анализа с объемами (язык: {language})")
        
        # Основной анализ марок бетона
        concrete_analysis = await self.analyze(doc_paths, smeta_path, use_claude, claude_mode)
        
        # Анализ объемов с использованием нового агента
        volumes = await self.volume_agent.analyze_volumes_from_documents(doc_paths, smeta_path)
        logger.info(f"📊 Новый анализ объемов: найдено {len(volumes)} позиций")
        
        # Создаем сводку по объемам
        volume_summary = self.volume_agent.create_volume_summary(volumes)
        
        # Интеграция результатов с валидацией
        enhanced_result = self._merge_concrete_and_volumes(concrete_analysis, volumes, volume_summary)
        logger.info("🔗 Результаты объединены с валидацией через базу знаний")
        
        # Установка языка для отчетов
        self.report_generator = get_report_generator(language)
        
        # Добавляем метаданные
        enhanced_result.update({
            'volume_entries_found': len(volumes),
            'volume_summary': volume_summary,
            'report_language': language,
            'analysis_type': 'complete_with_volumes_v2'
        })
        
        return enhanced_result

    def _merge_concrete_and_volumes(self, concrete_analysis: Dict[str, Any], 
                                   volumes: List, volume_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Объединяет результаты анализа марок и объемов с валидацией
        """
        enhanced_result = concrete_analysis.copy()
        
        # Добавляем сводку по объемам
        enhanced_result['volume_summary'] = volume_summary
        
        # Улучшаем информацию о каждой найденной марке
        enhanced_summary = []
        for concrete_item in concrete_analysis.get('concrete_summary', []):
            grade = concrete_item['grade']
            enhanced_item = concrete_item.copy()
            
            # Ищем объемы для этой марки
            grade_volumes = [v for v in volumes if hasattr(v, 'concrete_grade') and v.concrete_grade == grade]
            
            if grade_volumes:
                total_volume = sum(v.volume_m3 for v in grade_volumes)
                total_cost = sum(v.total_cost or 0 for v in grade_volumes)
                
                enhanced_item.update({
                    'total_volume_m3': round(total_volume, 2),
                    'total_cost': round(total_cost, 2) if total_cost > 0 else None,
                    'volume_entries_count': len(grade_volumes),
                    'construction_elements': list(set(v.construction_element for v in grade_volumes))
                })
                
                # Валидация через базу знаний
                for element in enhanced_item['construction_elements']:
                    validation = self.knowledge_service.validate_analysis_result(grade, element)
                    if not validation['valid'] or validation['warnings']:
                        if 'validation_warnings' not in enhanced_item:
                            enhanced_item['validation_warnings'] = []
                        enhanced_item['validation_warnings'].extend(validation['warnings'])
                        
                        if validation['recommendations']:
                            if 'recommendations' not in enhanced_item:
                                enhanced_item['recommendations'] = []
                            enhanced_item['recommendations'].extend(validation['recommendations'])
            
            enhanced_summary.append(enhanced_item)
        
        enhanced_result['concrete_summary'] = enhanced_summary
        return enhanced_result

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
        if generator.save_markdown_report(analysis_result, str(markdown_file)):
            saved_files['markdown'] = str(markdown_file)
        
        # JSON данные для Excel
        json_file = output_path / f"concrete_analysis_data_{language}.json"
        if generator.save_json_data(analysis_result, str(json_file)):
            saved_files['json'] = str(json_file)
        
        # Оригинальный JSON отчет
        json_report_file = output_path / "concrete_analysis_report.json"
        try:
            save_merged_report(analysis_result, str(json_report_file))
            saved_files['json_report'] = str(json_report_file)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить JSON отчет: {e}")
        
        logger.info(f"💾 Сохранено {len(saved_files)} файлов отчетов")
        return saved_files
    
    def _is_llm_available(self) -> bool:
        """Check if LLM service is available (centralized or legacy)"""
        if self.use_centralized_llm:
            return self.llm_service is not None
        else:
            return self.claude_client and self.claude_client.is_available

    async def _claude_concrete_analysis(self, text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """Анализ через Claude с расширенным контекстом"""
        if self.use_centralized_llm:
            return await self._centralized_llm_analysis(text, smeta_data)
        else:
            # Legacy fallback
            if not self.claude_client or not self.claude_client.is_available:
                logger.info("Claude API недоступен - пропускаем анализ с Claude")
                return {
                    "success": False, 
                    "error": "Claude API недоступен - проверьте ANTHROPIC_API_KEY",
                    "error_type": "api_unavailable"
                }
            
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
    
    async def _centralized_llm_analysis(self, text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """Analysis using centralized LLM service"""
        try:
            # Get system prompt from centralized prompt loader
            system_prompt = self.prompt_loader.get_system_prompt("concrete")
            prompt_config = self.prompt_loader.get_prompt_config("concrete")
            
            provider = prompt_config.get("provider", "claude")
            model = prompt_config.get("model")
            
            # Prepare context with smeta data
            smeta_context = ""
            if smeta_data:
                smeta_context = "\n\n=== СМЕТА ДАННЫЕ ===\n"
                for item in smeta_data[:10]:  # Limit to avoid token overflow
                    if isinstance(item, dict):
                        desc = item.get('description', '')
                        qty = item.get('quantity', item.get('qty', ''))
                        unit = item.get('unit', '')
                        smeta_context += f"- {desc} ({qty} {unit})\n"
            
            user_prompt = f"""
            Анализируй данный документ на предмет марок бетона и конструктивных элементов.
            
            Документ:
            {text[:10000]}  # Limit text length
            
            {smeta_context}
            
            Найди все марки бетона в формате C25/30, C30/37 и т.д., с указанием:
            - Классы воздействия (XC1, XF1, и т.д.)
            - Конструктивные элементы (стены, фундамент, перекрытия)
            - Объемы (если указаны)
            
            Верни результат в JSON формате.
            """
            
            response = await self.llm_service.run_prompt(
                provider=provider,
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=model
            )
            
            if response.get("success"):
                content = response.get("content", "")
                
                # Try to parse JSON from response
                try:
                    import json
                    if content.strip().startswith('{'):
                        analysis_data = json.loads(content)
                    else:
                        # Extract JSON if wrapped in text
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            analysis_data = json.loads(json_match.group())
                        else:
                            analysis_data = {"raw_text": content}
                    
                    return {
                        'concrete_summary': analysis_data.get('concrete_grades', []),
                        'analysis_method': 'centralized_llm_enhanced',
                        'success': True,
                        'tokens_used': response.get('usage', {}).get('total_tokens', 0),
                        'raw_response': content,
                        'provider': provider,
                        'model': model
                    }
                    
                except json.JSONDecodeError:
                    # Return raw response if JSON parsing fails
                    return {
                        'concrete_summary': [],
                        'analysis_method': 'centralized_llm_text',
                        'success': True,
                        'tokens_used': response.get('usage', {}).get('total_tokens', 0),
                        'raw_response': content,
                        'provider': provider,
                        'model': model
                    }
            else:
                logger.error(f"❌ LLM service failed: {response.get('error')}")
                return {"success": False, "error": response.get('error', 'Unknown error')}
                
        except Exception as e:
            logger.error(f"❌ Centralized LLM analysis error: {e}")
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
                # Use unified parser with MinerU integration
                result = parse_document(doc_path)
                if result["success"] and result["results"]:
                    text = ""
                    for parse_result in result["results"]:
                        content = parse_result.content
                        if isinstance(content, str):
                            text += content + "\n"
                        elif isinstance(content, dict):
                            # Handle structured content from MinerU
                            text += content.get("text", str(content)) + "\n"
                        else:
                            text += str(content) + "\n"
                    
                    all_text += text + "\n"
                    
                    processed_docs.append({
                        'file': Path(doc_path).name,
                        'type': 'Document',
                        'text_length': len(text),
                        'parser_used': result["results"][0].parser_used if result["results"] else "unknown"
                    })
                else:
                    processed_docs.append({
                        'file': Path(doc_path).name, 
                        'error': result.get("error", "Unknown parsing error")
                    })
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки {doc_path}: {e}")
                processed_docs.append({'file': Path(doc_path).name, 'error': str(e)})
        
        # Обрабатываем смету
        smeta_data = []
        if smeta_path:
            try:
                # Use unified parser for smeta
                result = parse_document(smeta_path)
                if result["success"] and result["results"]:
                    for parse_result in result["results"]:
                        content = parse_result.content
                        if isinstance(content, list):
                            # Structured smeta data from parser
                            smeta_data.extend(content)
                        elif isinstance(content, dict) and "items" in content:
                            # Legacy format with items key
                            smeta_data.extend(content["items"])
                        elif isinstance(content, dict):
                            # Single structured item
                            smeta_data.append(content)
                    
                    logger.info(f"📊 Смета обработана: {len(smeta_data)} позиций (parser: {result['results'][0].parser_used if result['results'] else 'unknown'})")
                else:
                    logger.error(f"❌ Ошибка обработки сметы: {result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"❌ Ошибка обработки сметы: {e}")
        
        # Локальный анализ (теперь улучшенный с чешской предобработкой)
        local_result = self._local_concrete_analysis(all_text)
        
        # Интеграция с Claude
        final_result = local_result.copy()
        
        if use_claude and self._is_llm_available():
            claude_result = await self._claude_concrete_analysis(all_text, smeta_data)
            
            if claude_mode == "primary" and claude_result.get("success"):
                final_result = claude_result
            elif claude_mode == "enhancement" and claude_result.get("success"):
                final_result.update({
                    'claude_analysis': claude_result,
                    'analysis_method': 'hybrid_enhanced_czech',
                    'total_tokens_used': claude_result.get('tokens_used', 0)
                })
        elif use_claude:
            # Claude was requested but is not available
            logger.warning("Claude анализ запрошен, но LLM сервис недоступен")
            final_result.update({
                'claude_unavailable': True,
                'claude_error': 'LLM сервис недоступен - проверьте API ключи'
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

async def analyze_concrete_with_volumes(doc_paths: List[str], smeta_path: Optional[str] = None,
                                        use_claude: bool = True, claude_mode: str = "enhancement",
                                        language: str = "cz") -> Dict[str, Any]:
    """
    Главная функция для полного анализа бетона с объемами и отчетами
    
    Args:
        doc_paths: Список путей к документам
        smeta_path: Путь к смете или výkaz výměr (опционально)
        use_claude: Использовать ли Claude AI
        claude_mode: Режим Claude ("enhancement" или "primary")
        language: Язык отчетов ("cz", "en", "ru")
        
    Returns:
        Полный анализ с объемами и сохранением отчетов
    """
    agent = get_hybrid_agent()
    
    try:
        # Полный анализ с объемами
        result = await agent.analyze_with_volumes(
            doc_paths, smeta_path, use_claude, claude_mode, language
        )
        
        # Сохранение отчетов
        saved_files = agent.save_comprehensive_reports(result, "outputs", language)
        result['saved_reports'] = saved_files
        
        # Логирование результатов
        concrete_count = len(result.get('concrete_summary', []))
        volume_count = result.get('volume_entries_found', 0)
        
        logger.info(f"✅ Анализ завершен:")
        logger.info(f"   - Найдено марок бетона: {concrete_count}")
        logger.info(f"   - Найдено объемов: {volume_count}")
        logger.info(f"   - Сохранено отчетов: {len(saved_files)}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в analyze_concrete_with_volumes: {e}")
        return {
            "error": str(e),
            "success": False,
            "analysis_method": "error",
            "concrete_summary": []
        }
