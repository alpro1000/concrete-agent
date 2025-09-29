"""
Специализированный агент для извлечения марок бетона
agents/concrete_agent/agent.py

Отвечает только за:
1. Извлечение марок бетона из документов
2. Валидацию марок через базу знаний
3. Определение классов воздействия
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from utils.knowledge_base_service import get_knowledge_service
from utils.czech_preprocessor import get_czech_preprocessor

logger = logging.getLogger(__name__)

@dataclass
class ConcreteGrade:
    """Структура для найденной марки бетона"""
    grade: str
    exposure_classes: List[str]
    context: str
    location: str
    confidence: float
    source_document: str
    line_number: int

class ConcreteGradeExtractor:
    """Специализированный агент для извлечения марок бетона"""
    
    def __init__(self):
        self.knowledge_service = get_knowledge_service()
        self.czech_preprocessor = get_czech_preprocessor()
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        
        # Получаем допустимые марки из базы знаний
        self.allowed_grades = set(self.knowledge_service.get_all_concrete_grades())
        logger.info(f"🎯 Загружено {len(self.allowed_grades)} допустимых марок бетона")
        
        # Паттерны для поиска марок бетона
        self.concrete_patterns = [
            # Стандартные форматы C25/30, LC25/28
            r'(?i)(?:beton(?:u|em|y|ové|ová)?|betónová?)\s+(?:třídy?\s+)?((?:LC)?C\d{1,3}/\d{1,3})',
            r'(?i)\b((?:LC)?C\d{1,3}/\d{1,3})\b',
            
            # Старые обозначения B20, B25
            r'(?i)(?:beton(?:u|em|y)?)\s+(?:třídy?\s+)?(B\d{1,2})',
            r'(?i)\b(B\d{1,2})\b(?=\s|$|[,.])',
            
            # Контекстные паттерны
            r'(?i)(?:ze\s+železobetonu|železobetonov[ýá])\s+(?:třídy?\s+)?((?:LC)?C\d{1,3}/\d{1,3})',
            r'(?i)(?:monolitick[ýá]|litý)\s+beton\s+(?:třídy?\s+)?((?:LC)?C\d{1,3}/\d{1,3})',
        ]
        
        # Паттерны для классов воздействия
        self.exposure_patterns = [
            r'\b(X[CDFASM]\d*)\b',
            r'\b(XO)\b'
        ]
    
    async def extract_concrete_grades(self, doc_paths: List[str], 
                                    smeta_path: Optional[str] = None) -> List[ConcreteGrade]:
        """Извлекает марки бетона из документов"""
        logger.info(f"🔍 Начинаем извлечение марок бетона из {len(doc_paths)} документов")
        
        all_grades = []
        
        # Обрабатываем основные документы
        for doc_path in doc_paths:
            grades = await self._extract_from_document(doc_path)
            all_grades.extend(grades)
        
        # Обрабатываем смету отдельно
        if smeta_path:
            smeta_grades = await self._extract_from_smeta(smeta_path)
            all_grades.extend(smeta_grades)
        
        # Фильтруем и валидируем найденные марки
        validated_grades = self._validate_grades(all_grades)
        
        logger.info(f"✅ Найдено {len(validated_grades)} валидных марок бетона")
        return validated_grades
    
    async def _extract_from_document(self, doc_path: str) -> List[ConcreteGrade]:
        """Извлекает марки из одного документа"""
        try:
            text = self.doc_parser.parse(doc_path)
            if not text:
                return []
            
            # Предобработка текста
            text = self.czech_preprocessor.normalize_text(text)
            
            return self._extract_grades_from_text(text, doc_path)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки документа {doc_path}: {e}")
            return []
    
    async def _extract_from_smeta(self, smeta_path: str) -> List[ConcreteGrade]:
        """Извлекает марки из сметы"""
        try:
            smeta_data = self.smeta_parser.parse(smeta_path)
            if not smeta_data:
                return []
            
            # Извлекаем текст из всех строк сметы
            text_parts = []
            for row in smeta_data:
                if isinstance(row, dict):
                    desc = row.get('description', '')
                    if desc:
                        text_parts.append(desc)
            
            text = '\n'.join(text_parts)
            text = self.czech_preprocessor.normalize_text(text)
            
            return self._extract_grades_from_text(text, smeta_path)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сметы {smeta_path}: {e}")
            return []
    
    def _extract_grades_from_text(self, text: str, source_document: str) -> List[ConcreteGrade]:
        """Извлекает марки бетона из текста"""
        grades = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 5:
                continue
            
            # Ищем марки бетона в строке
            for pattern in self.concrete_patterns:
                matches = re.finditer(pattern, line_clean)
                for match in matches:
                    grade = match.group(1) if match.groups() else match.group(0)
                    grade = grade.strip().upper()
                    
                    # Проверяем, что это валидная марка
                    if self._is_valid_grade_format(grade):
                        # Получаем контекст
                        context = self._get_line_context(lines, line_num)
                        
                        # Извлекаем классы воздействия
                        exposure_classes = self._extract_exposure_classes(context)
                        
                        # Определяем расположение/элемент
                        location = self._identify_construction_element(context)
                        
                        concrete_grade = ConcreteGrade(
                            grade=grade,
                            exposure_classes=exposure_classes,
                            context=context[:200],  # Ограничиваем длину контекста
                            location=location,
                            confidence=self._calculate_confidence(grade, context),
                            source_document=source_document,
                            line_number=line_num + 1
                        )
                        
                        grades.append(concrete_grade)
        
        return grades
    
    def _is_valid_grade_format(self, grade: str) -> bool:
        """Проверяет формат марки бетона"""
        # Стандартные форматы: C25/30, LC25/28, B25
        standard_patterns = [
            r'^(?:LC)?C\d{1,3}/\d{1,3}$',  # C25/30, LC25/28
            r'^B\d{1,2}$'  # B25
        ]
        
        return any(re.match(pattern, grade) for pattern in standard_patterns)
    
    def _extract_exposure_classes(self, context: str) -> List[str]:
        """Извлекает классы воздействия из контекста"""
        classes = []
        for pattern in self.exposure_patterns:
            matches = re.findall(pattern, context)
            classes.extend(matches)
        
        return list(set(classes))  # Убираем дубликаты
    
    def _identify_construction_element(self, context: str) -> str:
        """Определяет конструктивный элемент по контексту"""
        element = self.knowledge_service.identify_construction_element(context)
        return element if element != "unknown" else ""
    
    def _calculate_confidence(self, grade: str, context: str) -> float:
        """Вычисляет уверенность в найденной марке"""
        confidence = 0.5  # Базовая уверенность
        
        # Повышаем уверенность если марка в базе знаний
        if grade in self.allowed_grades:
            confidence += 0.3
        
        # Повышаем уверенность если есть контекстные слова
        context_keywords = self.knowledge_service.get_context_keywords()
        context_lower = context.lower()
        
        for keyword in context_keywords:
            if keyword in context_lower:
                confidence += 0.1
                break
        
        # Повышаем уверенность если есть классы воздействия
        if self._extract_exposure_classes(context):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _get_line_context(self, lines: List[str], line_num: int, window: int = 2) -> str:
        """Получает контекст вокруг строки"""
        start = max(0, line_num - window)
        end = min(len(lines), line_num + window + 1)
        
        context_lines = lines[start:end]
        return ' '.join(context_lines).strip()
    
    def _validate_grades(self, grades: List[ConcreteGrade]) -> List[ConcreteGrade]:
        """Валидирует и фильтрует найденные марки"""
        validated = []
        seen_grades = set()
        
        for grade in grades:
            # Убираем дубликаты
            grade_key = f"{grade.grade}_{grade.source_document}_{grade.line_number}"
            if grade_key in seen_grades:
                continue
            seen_grades.add(grade_key)
            
            # Валидируем через базу знаний
            if self.knowledge_service.is_valid_concrete_grade(grade.grade):
                validated.append(grade)
            else:
                logger.warning(f"⚠️ Неизвестная марка бетона: {grade.grade}")
        
        return validated
    
    def create_grades_summary(self, grades: List[ConcreteGrade]) -> Dict[str, Any]:
        """Создает сводку по найденным маркам"""
        if not grades:
            return {
                'total_grades_found': 0,
                'unique_grades': [],
                'grades_by_document': {},
                'grades_by_element': {},
                'validation_summary': {
                    'valid_grades': 0,
                    'invalid_grades': 0
                }
            }
        
        unique_grades = list(set(g.grade for g in grades))
        
        # Группировка по документам
        by_document = {}
        for grade in grades:
            doc = grade.source_document
            if doc not in by_document:
                by_document[doc] = []
            by_document[doc].append(grade.grade)
        
        # Группировка по элементам
        by_element = {}
        for grade in grades:
            element = grade.location or 'Неопределенный элемент'
            if element not in by_element:
                by_element[element] = []
            by_element[element].append(grade.grade)
        
        return {
            'total_grades_found': len(grades),
            'unique_grades': unique_grades,
            'grades_by_document': by_document,
            'grades_by_element': by_element,
            'validation_summary': {
                'valid_grades': len(grades),  # Все прошли валидацию
                'invalid_grades': 0
            }
        }


# Singleton instance
_concrete_grade_extractor = None

def get_concrete_grade_extractor() -> ConcreteGradeExtractor:
    """Получение глобального экземпляра экстрактора марок бетона"""
    global _concrete_grade_extractor
    if _concrete_grade_extractor is None:
        _concrete_grade_extractor = ConcreteGradeExtractor()
        logger.info("🎯 ConcreteGradeExtractor initialized")
    return _concrete_grade_extractor


# ==============================
# 🧪 Функция для тестирования
# ==============================

async def test_concrete_grade_extractor():
    """Тестирование экстрактора марок бетона"""
    extractor = get_concrete_grade_extractor()
    
    # Тестовый текст
    test_text = """
    MOSTNÍ OPĚRA ZE ŽELEZOBETONU C30/37 XD2
    Použitý beton: C25/30 XC2 XF1
    Základová deska - monolitický beton B25
    """
    
    # Имитируем извлечение из текста
    grades = extractor._extract_grades_from_text(test_text, "test_document.pdf")
    summary = extractor.create_grades_summary(grades)
    
    print("🧪 TESTING CONCRETE GRADE EXTRACTOR")
    print("=" * 50)
    print(f"📊 Найдено марок: {len(grades)}")
    print(f"🎯 Уникальных марок: {len(summary['unique_grades'])}")
    
    print("\n📋 Детали найденных марок:")
    for grade in grades:
        print(f"  • {grade.grade} (уверенность: {grade.confidence:.2f})")
        print(f"    Элемент: {grade.location}")
        print(f"    Классы воздействия: {', '.join(grade.exposure_classes)}")
        print(f"    Строка: {grade.line_number}")
        print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_concrete_grade_extractor())