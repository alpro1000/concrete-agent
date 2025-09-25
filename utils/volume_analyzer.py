"""
Анализатор объемов бетона из смет и výkaz výměr
utils/volume_analyzer.py
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VolumeEntry:
    """Структура для записи объема бетона"""
    concrete_grade: str
    volume_m3: float
    area_m2: Optional[float]
    thickness_mm: Optional[float]
    construction_element: str
    unit: str  # 'm3', 'm2', 'ks', 't'
    source_line: str
    source_document: str
    line_number: int
    confidence: float

@dataclass
class ConcreteVolumeSummary:
    """Сводка по объемам конкретной марки бетона"""
    grade: str
    total_volume_m3: float
    applications: List[Dict[str, Any]]
    total_cost: Optional[float]
    unit_price: Optional[float]

class VolumeAnalyzer:
    """Анализатор объемов бетона из строительных документов"""
    
    def __init__(self):
        # Паттерны для поиска марок бетона в сметах
        self.concrete_patterns = [
            r'(?i)(?:beton(?:u|em|y)?|betónová)\s+(?:třídy?\s+)?((?:LC)?C\d{1,3}/\d{1,3})',
            r'(?i)((?:LC)?C\d{1,3}/\d{1,3})\s*[-–]\s*[XO][CDFASM]?\d*',
            r'(?i)betón\s+((?:LC)?C\d{1,3}/\d{1,3})',
        ]
        
        # Паттерны для поиска объемов
        self.volume_patterns = [
            # Кубические метры: 125,50 m3, 125.50 m³, 125,5 m3
            r'(\d+(?:[,.]\d+)?)\s*(?:m3|m³|m\^3|кб\.?м)',
            # Квадратные метры: 250,00 m2, 250.50 m²
            r'(\d+(?:[,.]\d+)?)\s*(?:m2|m²|m\^2|кв\.?м)',
            # Штуки/количество: 15 ks, 10 шт
            r'(\d+(?:[,.]\d+)?)\s*(?:ks|шт\.?|pc\.?)',
            # Тонны: 25,5 t, 25.5 тонн
            r'(\d+(?:[,.]\d+)?)\s*(?:t|тонн?\.?)',
        ]
        
        # Паттерны для поиска толщин
        self.thickness_patterns = [
            r'(?:tl\.?|толщ\.?|thick\.?)\s*(\d+)\s*(?:mm|мм)',
            r'(\d+)\s*(?:mm|мм)(?:\s+thick)',
            r'(?:h|высота)\s*=?\s*(\d+)\s*(?:mm|мм)',
        ]
        
        # Конструктивные элементы для объемов
        self.volume_elements = {
            'základy': ['základ', 'foundation', 'fundament'],
            'piloty': ['pilot', 'pile', 'сваи'],
            'stěny': ['stěn', 'wall', 'стена'],
            'desky': ['desk', 'slab', 'плита'],
            'sloupy': ['sloup', 'column', 'столб'],
            'trámy': ['trám', 'beam', 'балка'],
            'říms': ['říms', 'cornice', 'карниз'],
            'podkladní': ['podklad', 'substrate', 'подкладка'],
            'mazanin': ['mazanin', 'screed', 'стяжка'],
            'chodník': ['chodník', 'sidewalk', 'тротуар'],
        }
        
        # Стандартные толщины для различных элементов
        self.standard_thicknesses = {
            'mazanin': [80, 100, 120, 150, 200],  # мм
            'desky': [150, 200, 250, 300, 400],
            'stěny': [200, 250, 300, 400, 500],
            'podkladní': [50, 100, 150, 200],
        }

    def analyze_volumes_from_text(self, text: str, document_name: str = "unknown") -> List[VolumeEntry]:
        """
        Извлекает объемы бетона из текста документа
        """
        volumes = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 10:
                continue
                
            # Ищем марки бетона в строке
            concrete_grade = self._extract_concrete_grade(line_clean)
            if not concrete_grade:
                continue
                
            # Ищем объемы в этой же строке или соседних
            volume_data = self._extract_volumes_from_line(line_clean, lines, line_num)
            
            if volume_data:
                # Определяем конструктивный элемент
                element = self._identify_volume_element(line_clean)
                
                for vol_data in volume_data:
                    volumes.append(VolumeEntry(
                        concrete_grade=concrete_grade,
                        volume_m3=vol_data['volume_m3'],
                        area_m2=vol_data.get('area_m2'),
                        thickness_mm=vol_data.get('thickness_mm'),
                        construction_element=element,
                        unit=vol_data['unit'],
                        source_line=line_clean,
                        source_document=document_name,
                        line_number=line_num + 1,
                        confidence=vol_data['confidence']
                    ))
        
        return volumes

    def _extract_concrete_grade(self, line: str) -> Optional[str]:
        """Извлекает марку бетона из строки"""
        for pattern in self.concrete_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                grade = match.group(1).upper().strip()
                # Нормализуем формат
                if re.match(r'^(?:LC)?C\d{1,3}/\d{1,3}$', grade):
                    return grade
        return None

    def _extract_volumes_from_line(self, line: str, all_lines: List[str], line_num: int) -> List[Dict[str, Any]]:
        """Извлекает объемы из строки и соседних строк"""
        volumes = []
        
        # Проверяем текущую строку и 2 соседние
        search_lines = []
        for offset in [-1, 0, 1]:
            idx = line_num + offset
            if 0 <= idx < len(all_lines):
                search_lines.append(all_lines[idx])
        
        search_text = ' '.join(search_lines)
        
        # Ищем м³
        for match in re.finditer(self.volume_patterns[0], search_text, re.IGNORECASE):
            volume_str = match.group(1).replace(',', '.')
            try:
                volume = float(volume_str)
                volumes.append({
                    'volume_m3': volume,
                    'unit': 'm3',
                    'confidence': 0.9
                })
            except ValueError:
                continue
        
        # Ищем м² с возможной толщиной
        for match in re.finditer(self.volume_patterns[1], search_text, re.IGNORECASE):
            area_str = match.group(1).replace(',', '.')
            try:
                area = float(area_str)
                
                # Ищем толщину
                thickness = self._extract_thickness(search_text, line)
                
                volume_data = {
                    'area_m2': area,
                    'unit': 'm2',
                    'confidence': 0.8
                }
                
                if thickness:
                    # Конвертируем в м³
                    volume_m3 = area * (thickness / 1000)
                    volume_data.update({
                        'volume_m3': volume_m3,
                        'thickness_mm': thickness,
                        'confidence': 0.9
                    })
                else:
                    volume_data['volume_m3'] = 0.0
                
                volumes.append(volume_data)
            except ValueError:
                continue
        
        return volumes

    def _extract_thickness(self, search_text: str, primary_line: str) -> Optional[float]:
        """Извлекает толщину из текста"""
        # Сначала ищем в основной строке
        for pattern in self.thickness_patterns:
            match = re.search(pattern, primary_line, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        # Затем в расширенном тексте
        for pattern in self.thickness_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        # Пытаемся угадать по типу элемента
        element = self._identify_volume_element(primary_line)
        for elem_type, thicknesses in self.standard_thicknesses.items():
            if elem_type in element.lower():
                return thicknesses[0]  # Возвращаем стандартную толщину
        
        return None

    def _identify_volume_element(self, line: str) -> str:
        """Определяет тип конструктивного элемента для объемов"""
        line_lower = line.lower()
        
        for element_type, keywords in self.volume_elements.items():
            for keyword in keywords:
                if keyword.lower() in line_lower:
                    return element_type
        
        return "neurčeno"

    def create_volume_summary(self, volumes: List[VolumeEntry]) -> List[ConcreteVolumeSummary]:
        """Создает сводку по объемам для каждой марки бетона"""
        summaries = {}
        
        for volume in volumes:
            grade = volume.concrete_grade
            
            if grade not in summaries:
                summaries[grade] = {
                    'grade': grade,
                    'total_volume_m3': 0.0,
                    'applications': [],
                    'entries': []
                }
            
            summaries[grade]['total_volume_m3'] += volume.volume_m3
            summaries[grade]['entries'].append(volume)
        
        # Группируем применения
        result = []
        for grade, data in summaries.items():
            # Группируем по элементам
            element_groups = {}
            for entry in data['entries']:
                elem = entry.construction_element
                if elem not in element_groups:
                    element_groups[elem] = {
                        'element': elem,
                        'volume_m3': 0.0,
                        'entries_count': 0,
                        'details': []
                    }
                
                element_groups[elem]['volume_m3'] += entry.volume_m3
                element_groups[elem]['entries_count'] += 1
                element_groups[elem]['details'].append({
                    'volume': entry.volume_m3,
                    'unit': entry.unit,
                    'source': entry.source_document,
                    'line': entry.line_number
                })
            
            summary = ConcreteVolumeSummary(
                grade=grade,
                total_volume_m3=data['total_volume_m3'],
                applications=list(element_groups.values()),
                total_cost=None,
                unit_price=None
            )
            
            result.append(summary)
        
        return result

    def merge_with_concrete_analysis(self, concrete_results: Dict[str, Any], 
                                   volumes: List[VolumeEntry]) -> Dict[str, Any]:
        """Объединяет результаты анализа бетона с объемами"""
        
        # Создаем сводку по объемам
        volume_summary = self.create_volume_summary(volumes)
        
        # Создаем словарь для быстрого поиска
        volume_dict = {vs.grade: vs for vs in volume_summary}
        
        # Добавляем объемы к найденным маркам
        enhanced_summary = []
        
        for concrete_item in concrete_results.get('concrete_summary', []):
            grade = concrete_item['grade']
            
            enhanced_item = concrete_item.copy()
            
            if grade in volume_dict:
                volume_data = volume_dict[grade]
                enhanced_item.update({
                    'total_volume_m3': volume_data.total_volume_m3,
                    'volume_applications': [
                        {
                            'element': app['element'],
                            'volume_m3': app['volume_m3'],
                            'entries_count': app['entries_count']
                        }
                        for app in volume_data.applications
                    ],
                    'has_volume_data': True
                })
            else:
                enhanced_item.update({
                    'total_volume_m3': 0.0,
                    'volume_applications': [],
                    'has_volume_data': False
                })
            
            enhanced_summary.append(enhanced_item)
        
        # Обновляем результат
        enhanced_results = concrete_results.copy()
        enhanced_results['concrete_summary'] = enhanced_summary
        enhanced_results['volume_analysis'] = {
            'total_entries': len(volumes),
            'grades_with_volumes': len(volume_summary),
            'volume_summary': [
                {
                    'grade': vs.grade,
                    'total_volume_m3': vs.total_volume_m3,
                    'applications_count': len(vs.applications)
                }
                for vs in volume_summary
            ]
        }
        
        return enhanced_results


# Singleton instance
_volume_analyzer = None

def get_volume_analyzer() -> VolumeAnalyzer:
    """Получение глобального экземпляра анализатора объемов"""
    global _volume_analyzer
    if _volume_analyzer is None:
        _volume_analyzer = VolumeAnalyzer()
        logger.info("📊 Volume analyzer initialized")
    return _volume_analyzer


# Функция для тестирования
def test_volume_analyzer():
    """Тестирование анализатора объемов"""
    analyzer = get_volume_analyzer()
    
    test_text = """
    801.001.001 Beton prostý C12/15-X0 125,50 m3
    801.002.001 Železobeton C25/30-XC2 základy 85,25 m3
    801.003.001 Mazanina C16/20 tl. 120 mm 450,00 m2
    802.001.001 Betonová deska C30/37-XC4 200,00 m2 tl. 250 mm
    """
    
    volumes = analyzer.analyze_volumes_from_text(test_text, "test_smeta.txt")
    
    print("🧪 TESTING VOLUME ANALYZER")
    print("=" * 40)
    
    for vol in volumes:
        print(f"Grade: {vol.concrete_grade}")
        print(f"Volume: {vol.volume_m3} m³")
        print(f"Element: {vol.construction_element}")
        print(f"Source: {vol.source_line[:50]}...")
        print(f"Confidence: {vol.confidence}")
        print("-" * 30)
    
    # Тест сводки
    summary = analyzer.create_volume_summary(volumes)
    print("\nSUMMARY:")
    for s in summary:
        print(f"{s.grade}: {s.total_volume_m3} m³ в {len(s.applications)} применениях")
    
    return volumes


if __name__ == "__main__":
    test_volume_analyzer()
