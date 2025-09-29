"""
ConcreteGradeExtractor Agent - специализированный агент для извлечения марок бетона
agents/concrete_agent/agent.py
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# Настройка логирования
logger = logging.getLogger(__name__)

@dataclass
class ConcreteGrade:
    """Структура данных для марки бетона"""
    grade: str
    strength_class: Optional[str] = None
    volume_m3: Optional[float] = None
    locations: List[str] = None
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.locations is None:
            self.locations = []

class ConcreteGradeExtractor:
    """Специализированный агент для извлечения и анализа марок бетона"""
    
    def __init__(self):
        self.name = "ConcreteGradeExtractor"
        self.version = "1.0.0"
        self.supported_formats = ['.txt', '.docx', '.pdf', '.xlsx']
        
        # Паттерны для поиска марок бетона
        self.concrete_patterns = [
            r'М\s*-?\s*(\d{2,3})',  # M-300, М 400, М-500
            r'B\s*-?\s*(\d{1,2}[.,]?\d*)',  # B25, B-30, B 22.5
            r'бетон[а-я\s]*М\s*-?\s*(\d{2,3})',  # бетон марки М400
            r'класс[а-я\s]*B\s*-?\s*(\d{1,2}[.,]?\d*)',  # класс прочности B25
            r'C\s*(\d{1,2}[.,]?\d*)/(\d{1,2}[.,]?\d*)',  # C25/30 (европейские стандарты)
        ]
        
        # Паттерны для объемов
        self.volume_patterns = [
            r'(\d+[.,]?\d*)\s*м[³3]',  # 100 м³, 50.5 м3
            r'(\d+[.,]?\d*)\s*куб[\.а-я]*',  # 100 куб.м
            r'объем[а-я\s]*(\d+[.,]?\d*)',  # объем 500
        ]
    
    def extract_concrete_grades(self, text: str) -> List[ConcreteGrade]:
        """Извлечение марок бетона из текста"""
        grades = []
        
        for pattern in self.concrete_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                grade_value = match.group(1)
                
                # Определяем тип марки
                if 'М' in match.group(0).upper() or 'M' in match.group(0).upper():
                    grade = f"М{grade_value}"
                    strength_class = self._convert_m_to_b(grade_value)
                elif 'B' in match.group(0).upper():
                    grade = f"B{grade_value}"
                    strength_class = grade
                elif 'C' in match.group(0).upper():
                    grade = match.group(0)
                    strength_class = grade
                else:
                    grade = grade_value
                    strength_class = None
                
                # Извлекаем контекст для локации
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                locations = self._extract_locations(context)
                
                # Извлекаем объем
                volume = self._extract_volume_from_context(context)
                
                concrete_grade = ConcreteGrade(
                    grade=grade,
                    strength_class=strength_class,
                    volume_m3=volume,
                    locations=locations,
                    confidence=0.8
                )
                
                grades.append(concrete_grade)
        
        return self._deduplicate_grades(grades)
    
    def _convert_m_to_b(self, m_value: str) -> str:
        """Преобразование марки М в класс прочности B"""
        try:
            m_num = int(m_value)
            # Приблизительная формула преобразования
            b_value = round(m_num * 0.787 / 10) * 1.25
            return f"B{b_value}"
        except:
            return None
    
    def _extract_locations(self, context: str) -> List[str]:
        """Извлечение мест применения из контекста"""
        location_patterns = [
            r'(фундамент[а-я]*)',
            r'(стен[а-я]*)',
            r'(плит[а-я]*)',
            r'(колонн[а-я]*)',
            r'(балк[а-я]*)',
            r'(лестниц[а-я]*)',
            r'(перекрыти[а-я]*)',
        ]
        
        locations = []
        for pattern in location_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            locations.extend(matches)
        
        return list(set(locations))
    
    def _extract_volume_from_context(self, context: str) -> Optional[float]:
        """Извлечение объема из контекста"""
        for pattern in self.volume_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                try:
                    volume_str = match.group(1).replace(',', '.')
                    return float(volume_str)
                except:
                    continue
        return None
    
    def _deduplicate_grades(self, grades: List[ConcreteGrade]) -> List[ConcreteGrade]:
        """Удаление дубликатов марок бетона"""
        unique_grades = {}
        
        for grade in grades:
            key = grade.grade
            if key not in unique_grades:
                unique_grades[key] = grade
            else:
                # Объединяем информацию
                existing = unique_grades[key]
                if grade.volume_m3 and not existing.volume_m3:
                    existing.volume_m3 = grade.volume_m3
                existing.locations.extend(grade.locations)
                existing.locations = list(set(existing.locations))
                existing.confidence = max(existing.confidence, grade.confidence)
        
        return list(unique_grades.values())
    
    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """Анализ документа для извлечения марок бетона"""
        try:
            # Чтение файла
            text = self._read_document(file_path)
            if not text:
                return {
                    "success": False,
                    "error": "Не удалось прочитать документ"
                }
            
            # Извлечение марок бетона
            grades = self.extract_concrete_grades(text)
            
            # Формирование результата
            result = {
                "success": True,
                "agent_name": self.name,
                "agent_version": self.version,
                "total_grades_found": len(grades),
                "concrete_grades": [
                    {
                        "grade": grade.grade,
                        "strength_class": grade.strength_class,
                        "volume_m3": grade.volume_m3,
                        "locations": grade.locations,
                        "confidence": grade.confidence
                    }
                    for grade in grades
                ],
                "summary": {
                    "unique_grades": len(grades),
                    "total_volume": sum(g.volume_m3 for g in grades if g.volume_m3),
                    "has_volumes": any(g.volume_m3 for g in grades),
                    "has_locations": any(g.locations for g in grades)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа документа {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent_name": self.name
            }
    
    def _read_document(self, file_path: str) -> str:
        """Чтение содержимого документа"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        if path.suffix.lower() == '.txt':
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        elif path.suffix.lower() == '.docx':
            try:
                from docx import Document
                doc = Document(path)
                return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                logger.warning("python-docx не установлен, используется базовый парсер")
                return ""
        
        elif path.suffix.lower() == '.pdf':
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                return text
            except ImportError:
                logger.warning("pdfplumber не установлен, используется базовый парсер")
                return ""
        
        else:
            logger.warning(f"Неподдерживаемый формат файла: {path.suffix}")
            return ""

# Экспорт основного класса
__all__ = ['ConcreteGradeExtractor']