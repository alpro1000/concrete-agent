"""
🧱 Полный ConcreteAgentHybrid - Улучшенная версия с точным распознаванием
Решает проблемы:
1. Распознавание всего, что начинается на "C"
2. Плохое распознавание чешского языка
3. Сохраняет всю функциональность оригинального агента
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

# Импорты из оригинального проекта
try:
    from parsers.doc_parser import DocParser
    from parsers.smeta_parser import SmetaParser
    from utils.claude_client import get_claude_client
    from config.settings import settings
    from outputs.save_report import save_merged_report
except ImportError:
    print("⚠️ Некоторые модули не найдены, работаем в автономном режиме")
    DocParser = None
    SmetaParser = None

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
    structural_element: Optional[str] = None
    exposure_class: Optional[str] = None
    position: Optional[Dict[str, int]] = None

@dataclass
class StructuralElement:
    """Структура для конструктивного элемента"""
    name: str
    concrete_grade: Optional[str]
    location: str
    context: str
    exposure_requirements: List[str]
    min_strength_required: Optional[str] = None

@dataclass
class AnalysisResult:
    """Результат анализа"""
    success: bool
    total_matches: int
    analysis_method: str
    processing_time: float
    concrete_summary: List[Dict[str, Any]]
    structural_elements: List[Dict[str, Any]]
    compliance_issues: List[str]
    recommendations: List[str]
    confidence_score: float

class CzechLanguageProcessor:
    """Процессор чешского языка для строительной терминологии"""
    
    def __init__(self):
        self.concrete_terms = {
            # Бетон во всех склонениях
            'beton': [
                'beton', 'betonu', 'betony', 'betonů', 'betonem', 'betonech',
                'betonová', 'betonové', 'betonový', 'betonovou', 'betonových',
                'betonovým', 'betonami', 'betonářský', 'betonářské'
            ],
            # Класс/степень
            'třída': [
                'třída', 'třídy', 'třídě', 'třídu', 'třídou', 'třídách', 
                'třídami', 'tříd', 'třídám', 'třídou'
            ],
            # Степень
            'stupeň': [
                'stupeň', 'stupně', 'stupni', 'stupněm', 'stupních', 
                'stupňů', 'stupňům', 'stupni'
            ],
            # Прочность
            'pevnost': [
                'pevnost', 'pevnosti', 'pevností', 'pevnostem', 'pevnostech',
                'pevnostní', 'pevnostním', 'pevnostních'
            ],
            # Качество
            'kvalita': [
                'kvalita', 'kvality', 'kvalitě', 'kvalitou', 'kvalit', 
                'kvalitách', 'kvalitní', 'kvalitním'
            ],
            # Конструкция
            'konstrukce': [
                'konstrukce', 'konstrukcí', 'konstrukcím', 'konstrukcemi', 
                'konstrukcích', 'konstrukční', 'konstrukčním'
            ],
            # Цемент
            'cement': [
                'cement', 'cementu', 'cementy', 'cementů', 'cementem', 
                'cementech', 'cementový', 'cementové'
            ],
            # Заливка
            'betonáž': [
                'betonáž', 'betonáže', 'betonáži', 'betonáží', 
                'betonování', 'betonovat'
            ],
            # Смесь
            'směs': [
                'směs', 'směsi', 'směsí', 'směsem', 'směsích', 
                'směsový', 'směsové'
            ],
            # Производство
            'výroba': [
                'výroba', 'výroby', 'výrobě', 'výrobu', 'výrobou',
                'výrobní', 'výrobník', 'vyrábět'
            ]
        }
        
        self.structural_elements = {
            'základ': ['základ', 'základy', 'základů', 'základem', 'základní', 'základová'],
            'pilíř': ['pilíř', 'pilíře', 'pilířů', 'pilířem', 'pilíři'],
            'sloup': ['sloup', 'sloupy', 'sloupů', 'sloupem', 'sloupu'],
            'stěna': ['stěna', 'stěny', 'stěn', 'stěnou', 'stěně'],
            'deska': ['deska', 'desky', 'desek', 'deskou', 'desce'],
            'nosník': ['nosník', 'nosníky', 'nosníků', 'nosníkem', 'nosníku'],
            'věnec': ['věnec', 'věnce', 'věnců', 'věncem', 'věnci'],
            'schodiště': ['schodiště', 'schodišť', 'schodištěm', 'schodišti'],
            'mostovka': ['mostovka', 'mostovky', 'mostovkou', 'mostovce'],
            'vozovka': ['vozovka', 'vozovky', 'vozovkou', 'vozovce'],
            'garáž': ['garáž', 'garáže', 'garáží', 'garážou', 'garážích'],
            'říms': ['říms', 'římsa', 'římsy', 'římsou', 'římsách']
        }

        self.exclusion_terms = {
            # Административные
            'admin': ['stránka', 'strana', 'str.', 'page', 'kapitola', 'oddíl', 'část', 'section'],
            # Коды и номера  
            'codes': ['kód', 'číslo', 'number', 'id', 'identifikátor', 'označení'],
            # Компании
            'companies': ['firma', 'společnost', 'company', 'spol.', 's.r.o.', 'a.s.'],
            # Даты и время
            'dates': ['datum', 'date', 'rok', 'year', 'měsíc', 'month', 'den', 'day'],
            # Цены и деньги
            'money': ['cena', 'price', 'cost', 'kč', 'koruna', 'euro', 'eur'],
            # Контакты
            'contacts': ['telefon', 'tel', 'phone', 'email', 'adresa', 'address']
        }

    def count_concrete_terms(self, text: str) -> int:
        """Подсчитывает количество найденных терминов для бетона"""
        text_lower = text.lower()
        count = 0
        
        for category, terms in self.concrete_terms.items():
            found = any(term in text_lower for term in terms)
            if found:
                count += 1
                
        return count

    def identify_structural_element(self, text: str) -> Optional[str]:
        """Определяет конструктивный элемент"""
        text_lower = text.lower()
        
        for element, variants in self.structural_elements.items():
            if any(variant in text_lower for variant in variants):
                return element.upper()
                
        return None

    def count_exclusion_terms(self, text: str) -> int:
        """Подсчитывает исключающие термины"""
        text_lower = text.lower()
        count = 0
        
        for category, terms in self.exclusion_terms.items():
            count += sum(1 for term in terms if term in text_lower)
                
        return count

    def is_valid_czech_context(self, text: str, threshold: int = 1) -> bool:
        """Проверяет валидность чешского контекста"""
        concrete_count = self.count_concrete_terms(text)
        exclusion_count = self.count_exclusion_terms(text)
        
        # Логика: минимум threshold терминов для бетона И не более 2 исключающих
        return concrete_count >= threshold and exclusion_count <= 2

class ConcreteGradeValidator:
    """Валидатор марок бетона на основе базы знаний"""
    
    def __init__(self, knowledge_base_path: str = "knowledge_base/complete-concrete-knowledge-base.json"):
        self.knowledge_base = self._load_knowledge_base(knowledge_base_path)
        self.valid_grades = self._extract_valid_grades()
        self.grade_mappings = self._build_grade_mappings()
        
    def _load_knowledge_base(self, path: str) -> Dict[str, Any]:
        """Загружает базу знаний"""
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить базу знаний: {e}")
            
        # Возвращаем минимальную структуру по умолчанию
        return {
            "concrete_knowledge_base": {
                "strength_classes": {
                    "standard": {
                        "C8/10": {"cylinder": 8, "cube": 10},
                        "C12/15": {"cylinder": 12, "cube": 15},
                        "C16/20": {"cylinder": 16, "cube": 20},
                        "C20/25": {"cylinder": 20, "cube": 25},
                        "C25/30": {"cylinder": 25, "cube": 30},
                        "C30/37": {"cylinder": 30, "cube": 37},
                        "C35/45": {"cylinder": 35, "cube": 45},
                        "C40/50": {"cylinder": 40, "cube": 50},
                        "C45/55": {"cylinder": 45, "cube": 55},
                        "C50/60": {"cylinder": 50, "cube": 60}
                    }
                }
            }
        }

    def _extract_valid_grades(self) -> Set[str]:
        """Извлекает все валидные марки из базы знаний"""
        valid_grades = set()
        
        kb = self.knowledge_base.get('concrete_knowledge_base', {})
        
        # Стандартные марки
        if 'strength_classes' in kb:
            classes = kb['strength_classes']
            if 'standard' in classes:
                valid_grades.update(classes['standard'].keys())
            if 'uhpc' in classes:
                valid_grades.update(classes['uhpc'].keys())
                
        # Легкие бетоны
        if 'concrete_types_by_density' in kb:
            density_types = kb['concrete_types_by_density']
            for concrete_type, data in density_types.items():
                if 'strength_classes' in data:
                    if isinstance(data['strength_classes'], dict):
                        valid_grades.update(data['strength_classes'].keys())
                    elif isinstance(data['strength_classes'], list):
                        valid_grades.update(data['strength_classes'])
        
        logger.info(f"Загружено {len(valid_grades)} валидных марок бетона")
        return valid_grades

    def _build_grade_mappings(self) -> Dict[str, str]:
        """Создает маппинг простых марок к полным"""
        mappings = {}
        
        # Стандартные соответствия
        standard_mappings = {
            'C8': 'C8/10', 'C12': 'C12/15', 'C16': 'C16/20', 'C20': 'C20/25',
            'C25': 'C25/30', 'C30': 'C30/37', 'C35': 'C35/45', 'C40': 'C40/50',
            'C45': 'C45/55', 'C50': 'C50/60', 'C55': 'C55/67', 'C60': 'C60/75',
            'C70': 'C70/85', 'C80': 'C80/95', 'C90': 'C90/105', 'C100': 'C100/115'
        }
        
        # Добавляем только те маппинги, где целевая марка существует в базе
        for simple, full in standard_mappings.items():
            if full in self.valid_grades:
                mappings[simple] = full
                
        return mappings

    def normalize_grade(self, grade: str) -> str:
        """Нормализует марку к стандартному формату"""
        grade = re.sub(r'\s+', '', grade.upper())
        return self.grade_mappings.get(grade, grade)

    def is_valid_grade(self, grade: str) -> bool:
        """Проверяет валидность марки"""
        normalized = self.normalize_grade(grade)
        return normalized in self.valid_grades

    def get_grade_info(self, grade: str) -> Dict[str, Any]:
        """Получает информацию о марке из базы знаний"""
        normalized = self.normalize_grade(grade)
        
        if not self.is_valid_grade(normalized):
            return {}
            
        kb = self.knowledge_base.get('concrete_knowledge_base', {})
        strength_classes = kb.get('strength_classes', {})
        
        # Поиск в стандартных марках
        if 'standard' in strength_classes and normalized in strength_classes['standard']:
            return strength_classes['standard'][normalized]
            
        return {}

class ImprovedRegexEngine:
    """Улучшенный движок регулярных выражений"""
    
    def __init__(self, validator: ConcreteGradeValidator):
        self.validator = validator
        self.patterns = self._build_patterns()
        self.exclusion_patterns = self._build_exclusion_patterns()
        
    def _build_patterns(self) -> List[str]:
        """Строит строгие regex-паттерны"""
        patterns = []
        
        # Паттерн 1: Точные совпадения с валидными марками
        if self.validator.valid_grades:
            escaped_grades = [re.escape(grade) for grade in self.validator.valid_grades]
            exact_pattern = '|'.join(escaped_grades)
            patterns.append(rf'\b({exact_pattern})\b')
        
        # Паттерн 2: Стандартный формат C##/## с ограничениями
        patterns.append(r'\bC([8-9]|[1-9][0-9]|1[0-7][0-9])/([1-9][0-9]|1[0-1][0-9])\b')
        
        # Паттерн 3: Легкие бетоны LC##/##
        patterns.append(r'\bLC([8-9]|[1-8][0-9])/([9]|[1-8][0-9])\b')
        
        # Паттерн 4: Простые марки C## (ограниченный диапазон)
        patterns.append(r'\bC([8-9]|[1-9][0-9]|1[0-7][0-9])(?!/\d)\b')
        
        # Паттерн 5: Марки с классами среды
        patterns.append(r'\bC\d{1,2}/\d{1,2}(?:\s*[-–]?\s*X[CDFASM]\d*(?:\s*,\s*X[CDFASM]\d*)*)?(?:\s*[-–]?\s*X[CDFASM]\d*)*\b')
        
        return patterns
        
    def _build_exclusion_patterns(self) -> List[str]:
        """Паттерны исключений"""
        return [
            r'C\d{4,}',                      # Длинные числа
            r'[Cc]z\d+',                     # CZ коды
            r'C\d+[A-Z]{3,}',               # Длинные буквенные суффиксы
            r'\bC(?:ad|AD)\b',               # CAD
            r'\bC(?:o|O)\.?\s*\d+',         # Номера компаний
            r'C[A-Z]\d+[A-Z]',              # Смешанные коды
            r'\bC\s?\d+\s?(?:kg|mm|cm|m|%)\b',  # С единицами измерения
            r'\bC\d+[-_]\d+[-_]\d+',        # Версии, даты
        ]

    def find_matches(self, text: str) -> List[Tuple[str, int, int]]:
        """Находит все совпадения в тексте"""
        matches = []
        seen_grades = set()
        
        for pattern in self.patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                grade = match.group().strip().upper()
                start, end = match.span()
                
                # Избегаем дубликатов
                if grade in seen_grades:
                    continue
                    
                # Проверяем исключения
                if self._is_excluded(grade, text, start, end):
                    continue
                    
                matches.append((grade, start, end))
                seen_grades.add(grade)
                
        return matches

    def _is_excluded(self, grade: str, text: str, start: int, end: int) -> bool:
        """Проверяет исключения"""
        # Проверяем паттерны исключений
        for exclusion in self.exclusion_patterns:
            if re.search(exclusion, grade, re.IGNORECASE):
                return True
        
        # Проверяем контекст (±300 символов)
        context_start = max(0, start - 300)
        context_end = min(len(text), end + 300)
        context = text[context_start:context_end].lower()
        
        # Исключаем, если слишком много "не-бетонных" терминов
        exclusion_terms = [
            'stránka', 'strana', 'page', 'kapitola', 'oddíl',
            'kód', 'číslo', 'number', 'firma', 'společnost',
            'datum', 'date', 'cena', 'price', 'telefon', 'email'
        ]
        
        exclusion_count = sum(1 for term in exclusion_terms if term in context)
        return exclusion_count >= 3

class ConcreteAgentHybrid:
    """Полная версия улучшенного агента для анализа бетонов"""
    
    def __init__(self, knowledge_base_path: str = "knowledge_base/complete-concrete-knowledge-base.json"):
        """Инициализация агента"""
        self.knowledge_base_path = knowledge_base_path
        
        # Инициализация компонентов
        self.validator = ConcreteGradeValidator(knowledge_base_path)
        self.czech_processor = CzechLanguageProcessor()
        self.regex_engine = ImprovedRegexEngine(self.validator)
        
        # Инициализация парсеров (если доступны)
        self.doc_parser = DocParser() if DocParser else None
        self.smeta_parser = SmetaParser() if SmetaParser else None
        
        # Настройки
        self.min_confidence_threshold = 0.6
        self.max_context_length = 500
        
        logger.info("ConcreteAgentHybrid инициализирован")

    def analyze_text(self, text: str, source_type: str = "document") -> AnalysisResult:
        """Основная функция анализа текста"""
        start_time = time.time()
        
        try:
            # Поиск совпадений
            raw_matches = self.regex_engine.find_matches(text)
            
            # Обработка и валидация
            validated_matches = []
            structural_elements = []
            
            for grade, start, end in raw_matches:
                match_result = self._process_match(text, grade, start, end)
                
                if match_result and match_result.confidence >= self.min_confidence_threshold:
                    validated_matches.append(match_result)
                    
                    # Определяем конструктивный элемент
                    element = self._extract_structural_element(match_result.context)
                    if element:
                        structural_elements.append(element)
            
            # Анализ соответствия нормам
            compliance_issues = self._check_compliance(validated_matches)
            recommendations = self._generate_recommendations(validated_matches, compliance_issues)
            
            # Подсчет общей уверенности
            avg_confidence = sum(m.confidence for m in validated_matches) / len(validated_matches) if validated_matches else 0
            
            processing_time = time.time() - start_time
            
            return AnalysisResult(
                success=True,
                total_matches=len(validated_matches),
                analysis_method="improved_hybrid_regex_czech_validation",
                processing_time=processing_time,
                concrete_summary=[self._match_to_dict(m) for m in validated_matches],
                structural_elements=structural_elements,
                compliance_issues=compliance_issues,
                recommendations=recommendations,
                confidence_score=avg_confidence
            )
            
        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
            return AnalysisResult(
                success=False,
                total_matches=0,
                analysis_method="error",
                processing_time=time.time() - start_time,
                concrete_summary=[],
                structural_elements=[],
                compliance_issues=[f"Ошибка анализа: {str(e)}"],
                recommendations=["Проверьте входные данные и повторите анализ"],
                confidence_score=0.0
            )

    def _process_match(self, text: str, grade: str, start: int, end: int) -> Optional[ConcreteMatch]:
        """Обрабатывает найденное совпадение"""
        # Извлекаем контекст
        context_start = max(0, start - 250)
        context_end = min(len(text), end + 250)
        context = text[context_start:context_end]
        
        # Проверяем чешский контекст
        if not self.czech_processor.is_valid_czech_context(context):
            return None
        
        # Нормализуем марку
        normalized_grade = self.validator.normalize_grade(grade)
        
        # Проверяем валидность
        if not self.validator.is_valid_grade(normalized_grade):
            return None
        
        # Определяем местоположение и конструкцию
        structural_element = self.czech_processor.identify_structural_element(context)
        location = structural_element or "nespecifikováno"
        
        # Извлекаем класс воздействия
        exposure_class = self._extract_exposure_class(context)
        
        # Вычисляем уверенность
        confidence = self._calculate_confidence(normalized_grade, context, structural_element, exposure_class)
        
        return ConcreteMatch(
            grade=normalized_grade,
            context=context.strip()[:self.max_context_length],
            location=location,
            confidence=confidence,
            method="hybrid_regex_czech",
            coordinates=None,
            structural_element=structural_element,
            exposure_class=exposure_class,
            position={"start": start, "end": end}
        )

    def _extract_exposure_class(self, context: str) -> Optional[str]:
        """Извлекает классы воздействующей среды"""
        exposure_pattern = r'X[CDFASM]\d*'
        matches = re.findall(exposure_pattern, context, re.IGNORECASE)
        return ', '.join(set(m.upper() for m in matches)) if matches else None

    def _calculate_confidence(self, grade: str, context: str, structural_element: Optional[str], 
                            exposure_class: Optional[str]) -> float:
        """Вычисляет уверенность в найденной марке"""
        confidence = 0.4  # Базовая уверенность
        
        # Бонус за валидную марку
        if self.validator.is_valid_grade(grade):
            confidence += 0.3
        
        # Бонус за чешский контекст
        czech_terms_count = self.czech_processor.count_concrete_terms(context)
        confidence += min(czech_terms_count * 0.05, 0.25)
        
        # Бонус за структурный элемент
        if structural_element:
            confidence += 0.1
        
        # Бонус за класс воздействия
        if exposure_class:
            confidence += 0.1
        
        # Технические термины
        tech_terms = ['mpa', 'pevnost', 'cement', 'norma', 'výroba', 'kvalita']
        context_lower = context.lower()
        tech_bonus = sum(0.02 for term in tech_terms if term in context_lower)
        confidence += min(tech_bonus, 0.15)
        
        return min(confidence, 1.0)

    def _extract_structural_element(self, context: str) -> Optional[Dict[str, Any]]:
        """Извлекает информацию о конструктивном элементе"""
        element_type = self.czech_processor.identify_structural_element(context)
        
        if not element_type:
            return None
            
        return {
            "type": element_type,
            "context": context[:200],
            "requirements": self._get_element_requirements(element_type)
        }

    def _get_element_requirements(self, element_type: str) -> List[str]:
        """Получает требования для конструктивного элемента"""
        requirements = {
            "ZÁKLAD": ["Minimální třída C16/20", "Ochrana proti XA", "Krytí min 35mm"],
            "PILÍŘ": ["Minimální třída C20/25", "Vhodnost pro XC prostředí"],
            "STĚNA": ["Minimální třída C16/20", "Ochrana proti XC"],
            "DESKA": ["Minimální třída C20/25", "Ochrana proti XC"],
        }
        
        return requirements.get(element_type, ["Kontrola dle ČSN EN 206"])

    def _check_compliance(self, matches: List[ConcreteMatch]) -> List[str]:
        """Проверяет соответствие нормам"""
        issues = []
        
        for match in matches:
            # Проверяем минимальную прочность
            if match.grade.startswith('C'):
                try:
                    strength = int(match.grade.split('/')[0][1:])
                    if strength < 12:
                        issues.append(f"Марка {match.grade} ниже минимальной C12/15")
                except:
                    pass
            
            # Проверяем соответствие структурного элемента
            if match.structural_element == "ZÁKLAD" and match.grade in ["C8/10", "C12/15"]:
                issues.append(f"Для фундаментов рекомендуется минимум C16/20, найдено {match.grade}")
        
        return issues

    def _generate_recommendations(self, matches: List[ConcreteMatch], issues: List[str]) -> List[str]:
        """Генерирует рекомендации"""
        recommendations = []
        
        if not matches:
            recommendations.append("Марки бетона не обнаружены. Проверьте документацию.")
            return recommendations
        
        # Общие рекомендации
        if len(matches) > 5:
            recommendations.append("Обнаружено много разных марок. Рассмотрите стандартизацию.")
        
        # Рекомендации по классам воздействия
        exposure_classes = [m.exposure_class for m in matches if m.exposure_class]
        if not any(exposure_classes):
            recommendations.append("Укажите классы воздействующей среды (XC, XF, XA и т.д.)")
        
        # Рекомендации по конструктивным элементам
        elements = [m.structural_element for m in matches if m.structural_element]
        if not any(elements):
            recommendations.append("Уточните применение бетона в конструктивных элементах")
        
        return recommendations

    def _match_to_dict(self, match: ConcreteMatch) -> Dict[str, Any]:
        """Преобразует ConcreteMatch в словарь"""
        result = asdict(match)
        
        # Добавляем информацию из базы знаний
        grade_info = self.validator.get_grade_info(match.grade)
        if grade_info:
            result["grade_properties"] = grade_info
        
        return result

    def analyze_document(self, file_path: str) -> AnalysisResult:
        """Анализирует документ"""
        try:
            if self.doc_parser:
                text = self.doc_parser.parse(file_path)
            else:
                # Простое чтение текстового файла
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            return self.analyze_text(text, source_type="document")
            
        except Exception as e:
            logger.error(f"Ошибка анализа документа {file_path}: {e}")
            return AnalysisResult(
                success=False,
                total_matches=0,
                analysis_method="document_analysis_error",
                processing_time=0,
                concrete_summary=[],
                structural_elements=[],
                compliance_issues=[f"Ошибка чтения файла: {str(e)}"],
                recommendations=["Проверьте путь к файлу и формат"],
                confidence_score=0.0
            )

    def analyze_smeta(self, file_path: str) -> AnalysisResult:
        """Анализирует смету"""
        try:
            if self.smeta_parser:
                data = self.smeta_parser.parse(file_path)
                # Объединяем весь текст из сметы
                text = " ".join(str(value) for value in data.values() if isinstance(value, (str, int, float)))
            else:
                # Простое чтение
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            return self.analyze_text(text, source_type="smeta")
            
        except Exception as e:
            logger.error(f"Ошибка анализа сметы {file_path}: {e}")
            return AnalysisResult(
                success=False,
                total_matches=0,
                analysis_method="smeta_analysis_error", 
                processing_time=0,
                concrete_summary=[],
                structural_elements=[],
                compliance_issues=[f"Ошибка чтения сметы: {str(e)}"],
                recommendations=["Проверьте формат файла сметы"],
                confidence_score=0.0
            )

    def generate_report(self, result: AnalysisResult, output_path: str = None) -> Dict[str, Any]:
        """Генерирует подробный отчет"""
        report = {
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "agent_version": "2.0_improved",
                "knowledge_base": self.knowledge_base_path,
                "success": result.success,
                "processing_time": result.processing_time,
                "total_matches": result.total_matches,
                "confidence_score": result.confidence_score
            },
            "concrete_analysis": {
                "method": result.analysis_method,
                "matches": result.concrete_summary,
                "unique_grades": list(set(m["grade"] for m in result.concrete_summary)),
                "grade_frequency": self._calculate_grade_frequency(result.concrete_summary)
            },
            "structural_analysis": {
                "elements": result.structural_elements,
                "element_types": list(set(e.get("type", "nespecifikováno") for e in result.structural_elements))
            },
            "compliance_check": {
                "issues": result.compliance_issues,
                "recommendations": result.recommendations,
                "compliance_score": max(0, 1.0 - len(result.compliance_issues) * 0.2)
            },
            "statistics": {
                "avg_confidence": result.confidence_score,
                "high_confidence_matches": len([m for m in result.concrete_summary if m.get("confidence", 0) > 0.8]),
                "with_exposure_class": len([m for m in result.concrete_summary if m.get("exposure_class")]),
                "with_structural_element": len([m for m in result.concrete_summary if m.get("structural_element")])
            }
        }
        
        # Сохраняем отчет, если указан путь
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                logger.info(f"Отчет сохранен: {output_path}")
            except Exception as e:
                logger.error(f"Ошибка сохранения отчета: {e}")
        
        return report

    def _calculate_grade_frequency(self, matches: List[Dict[str, Any]]) -> Dict[str, int]:
        """Подсчитывает частоту марок"""
        frequency = {}
        for match in matches:
            grade = match.get("grade", "unknown")
            frequency[grade] = frequency.get(grade, 0) + 1
        return frequency

    # Методы совместимости с оригинальным API
    def analyze(self, text: str) -> Dict[str, Any]:
        """Метод для совместимости с оригинальным API"""
        result = self.analyze_text(text)
        
        return {
            "success": result.success,
            "total_matches": result.total_matches,
            "analysis_method": result.analysis_method,
            "concrete_summary": result.concrete_summary,
            "confidence_score": result.confidence_score,
            "processing_time": result.processing_time
        }

# Импорты для совместимости
import time
from datetime import datetime

# Функции для совместимости с существующим API
def analyze_concrete_improved(text: str, knowledge_base_path: str = None) -> Dict[str, Any]:
    """Улучшенный анализ бетона - основная функция"""
    if knowledge_base_path is None:
        knowledge_base_path = "knowledge_base/complete-concrete-knowledge-base.json"
    
    agent = ConcreteAgentHybrid(knowledge_base_path)
    return agent.analyze(text)

def create_concrete_agent(knowledge_base_path: str = None) -> ConcreteAgentHybrid:
    """Создает экземпляр улучшенного агента"""
    if knowledge_base_path is None:
        knowledge_base_path = "knowledge_base/complete-concrete-knowledge-base.json"
    
    return ConcreteAgentHybrid(knowledge_base_path)

if __name__ == "__main__":
    # Пример использования
    test_text = """
    Základová konstrukce bude provedena z betonu třídy C25/30 XC1, XA1.
    Stěnové konstrukce budou z betonu C30/37 XF2.
    Pro pilíře se použije beton LC25/28.
    
    Neplatné kódy: C425, CZ75994234, stránka 125.
    Společnost ABC s.r.o. dodá materiál podle normy ČSN EN 206.
    
    Věnec bude betonován betonem třídy C20/25 s cementem CEM I 42.5 R.
    Deska garáže vyžaduje beton C30/37 XF4 kvůli zmrazovacím cyklům.
    """
    
    print("🧱 TESTOVÁNÍ VYLEPŠENÉHO CONCRETE AGENT")
    print("=" * 60)
    
    # Vytvoření agenta
    agent = create_concrete_agent()
    
    # Analýza textu
    result = agent.analyze_text(test_text)
    
    print(f"✅ Úspěch: {result.success}")
    print(f"📊 Nalezeno marky: {result.total_matches}")
    print(f"⚡ Doba zpracování: {result.processing_time:.3f}s")
    print(f"🎯 Celková jistota: {result.confidence_score:.2f}")
    print()
    
    print("🔍 NALEZENÉ MARKY:")
    for i, match in enumerate(result.concrete_summary, 1):
        print(f"{i:2d}. {match['grade']:8s} | {match['location']:15s} | {match['confidence']:.2f} | {match.get('exposure_class', 'N/A')}")
    
    print()
    print("🏗️ KONSTRUKČNÍ PRVKY:")
    for element in result.structural_elements:
        print(f"   - {element.get('type', 'N/A')}: {element.get('requirements', ['N/A'])[0]}")
    
    print()
    print("⚠️ PROBLÉMY A DOPORUČENÍ:")
    for issue in result.compliance_issues:
        print(f"   ❌ {issue}")
    for rec in result.recommendations:
        print(f"   💡 {rec}")
    
    print()
    print("📋 GENEROVÁNÍ PODROBNÉHO REPORTU...")
    
    # Генерируем полный отчет
    report = agent.generate_report(result, "concrete_analysis_report.json")
    print(f"✅ Podrobný report uložen jako 'concrete_analysis_report.json'")
    print(f"📈 Statistiky: {report['statistics']}")
