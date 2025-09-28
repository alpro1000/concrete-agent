"""
Специализированный агент для анализа объемов и связывания
agents/volume_agent/agent.py

Отвечает только за:
1. Извлечение объемов из документов и смет
2. Связывание объемов с марками бетона
3. Анализ конструктивных элементов
4. Расчет стоимости и количеств
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from services.doc_parser import parse_document  # New unified parser
from utils.knowledge_base_service import get_knowledge_service
from utils.czech_preprocessor import get_czech_preprocessor
from agents.concrete_agent.agent import get_concrete_grade_extractor

logger = logging.getLogger(__name__)

@dataclass
class VolumeEntry:
    """Структура для найденного объема"""
    concrete_grade: str
    volume_m3: Optional[float]
    area_m2: Optional[float] 
    thickness_mm: Optional[float]
    construction_element: str
    unit_price: Optional[float]
    total_cost: Optional[float]
    unit: str  # 'm3', 'm2', 'ks', 't'
    source_line: str
    source_document: str
    line_number: int
    confidence: float
    context: str

@dataclass
class ElementVolumeGroup:
    """Группировка объемов по конструктивным элементам"""
    element_name: str
    concrete_grade: str
    total_volume_m3: float
    unit_price: Optional[float]
    total_cost: Optional[float]
    entries: List[VolumeEntry]

class VolumeAnalysisAgent:
    """Специализированный агент для анализа объемов"""
    
    def __init__(self):
        self.knowledge_service = get_knowledge_service()
        self.czech_preprocessor = get_czech_preprocessor()
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        self.concrete_extractor = get_concrete_grade_extractor()
        
        logger.info("🏗️ VolumeAnalysisAgent initialized")
        
        # Паттерны для поиска объемов
        self.volume_patterns = [
            # Объемы в м³: 125,5 m3, 125.5 м³
            r'(\d+[,.]?\d*)\s*(?:m3|м3|кубометр)',
            
            # Площади в м²: 50,2 m2, 50.2 м²
            r'(\d+[,.]?\d*)\s*(?:m2|м2|квадратн)',
            
            # Толщины в мм: 200 mm, 150мм
            r'(?:толщ|tloušťk|thick)\w*[:\s]*(\d+)\s*(?:mm|мм)',
            
            # Количества: 15 ks, 20 шт
            r'(\d+)\s*(?:ks|шт|штук)',
            
            # Массы: 2,5 t, 2.5 тонн
            r'(\d+[,.]?\d*)\s*(?:t|тонн|ton)',
        ]
        
        # Паттерны для поиска цен
        self.price_patterns = [
            r'(\d+[,.]?\d*)\s*(?:Kč|кч|крон)',
            r'(?:цена|price|cena)[:\s]*(\d+[,.]?\d*)',
            r'(\d+[,.]?\d*)\s*(?:за|per|na)\s*(?:m3|м3)',
        ]
    
    async def analyze_volumes(self, doc_paths: List[str], 
                            smeta_path: Optional[str] = None) -> List[VolumeEntry]:
        """Анализирует объемы из документов"""
        logger.info(f"📊 Начинаем анализ объемов из {len(doc_paths)} документов")
        
        all_volumes = []
        
        # Сначала извлекаем марки бетона
        concrete_grades = await self.concrete_extractor.extract_concrete_grades(doc_paths, smeta_path)
        grades_by_document = self._group_grades_by_document(concrete_grades)
        
        # Обрабатываем основные документы  
        for doc_path in doc_paths:
            doc_grades = grades_by_document.get(doc_path, [])
            volumes = await self._extract_volumes_from_document(doc_path, doc_grades)
            all_volumes.extend(volumes)
        
        # Обрабатываем смету отдельно
        if smeta_path:
            smeta_grades = grades_by_document.get(smeta_path, [])
            smeta_volumes = await self._extract_volumes_from_smeta(smeta_path, smeta_grades)
            all_volumes.extend(smeta_volumes)
        
        # Связываем объемы с марками бетона
        linked_volumes = self._link_volumes_with_grades(all_volumes, concrete_grades)
        
        logger.info(f"✅ Найдено {len(linked_volumes)} объемов с привязкой к маркам")
        return linked_volumes
    
    def _group_grades_by_document(self, grades) -> Dict[str, List]:
        """Группирует марки по документам"""
        grouped = {}
        for grade in grades:
            doc = grade.source_document
            if doc not in grouped:
                grouped[doc] = []
            grouped[doc].append(grade)
        return grouped
    
    async def _extract_volumes_from_document(self, doc_path: str, grades: List) -> List[VolumeEntry]:
        """Извлекает объемы из документа"""
        try:
            # Use unified parser with MinerU integration
            result = parse_document(doc_path)
            if not result["success"] or not result["results"]:
                return []
            
            # Extract text from parse results
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
            
            if not text.strip():
                return []
            
            text = self.czech_preprocessor.normalize_text(text)
            volumes = self._extract_volumes_from_text(text, doc_path, grades)
            
            # Log which parser was used
            if result["results"]:
                logger.info(f"📊 Объемы из документа {Path(doc_path).name}: {len(volumes)} (parser: {result['results'][0].parser_used})")
                
            return volumes
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки документа {doc_path}: {e}")
            return []
    
    async def _extract_volumes_from_smeta(self, smeta_path: str, grades: List) -> List[VolumeEntry]:
        """Извлекает объемы из сметы"""
        try:
            # Use unified parser for smeta
            result = parse_document(smeta_path)
            if not result["success"] or not result["results"]:
                return []
            
            # Extract structured smeta data
            smeta_data = []
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
            
            if not smeta_data:
                return []
            
            volumes = []
            for row_num, row in enumerate(smeta_data):
                if isinstance(row, dict):
                    volume_entry = self._extract_volume_from_smeta_row(
                        row, smeta_path, row_num, grades
                    )
                    if volume_entry:
                        volumes.append(volume_entry)
            
            # Log which parser was used
            if result["results"]:
                logger.info(f"📊 Объемы из сметы {Path(smeta_path).name}: {len(volumes)} (parser: {result['results'][0].parser_used})")
            
            return volumes
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сметы {smeta_path}: {e}")
            return []
    
    def _extract_volumes_from_text(self, text: str, source_document: str, grades: List) -> List[VolumeEntry]:
        """Извлекает объемы из текста"""
        volumes = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 10:
                continue
            
            # Ищем объемы в строке
            volume_data = self._parse_volume_from_line(line_clean)
            if not volume_data:
                continue
            
            # Получаем контекст
            context = self._get_line_context(lines, line_num)
            
            # Определяем конструктивный элемент
            element = self.knowledge_service.identify_construction_element(context)
            
            # Найти ближайшую марку бетона
            closest_grade = self._find_closest_grade(line_num, grades, context)
            
            volume_entry = VolumeEntry(
                concrete_grade=closest_grade.grade if closest_grade else "",
                volume_m3=volume_data.get('volume_m3'),
                area_m2=volume_data.get('area_m2'),
                thickness_mm=volume_data.get('thickness_mm'),
                construction_element=element,
                unit_price=volume_data.get('unit_price'),
                total_cost=volume_data.get('total_cost'),
                unit=volume_data.get('unit', 'm3'),
                source_line=line_clean,
                source_document=source_document,
                line_number=line_num + 1,
                confidence=self._calculate_volume_confidence(volume_data, context),
                context=context[:200]
            )
            
            volumes.append(volume_entry)
        
        return volumes
    
    def _extract_volume_from_smeta_row(self, row: Dict, source_document: str, 
                                     row_num: int, grades: List) -> Optional[VolumeEntry]:
        """Извлекает объем из строки сметы"""
        description = row.get('description', '')
        quantity = row.get('quantity', 0)
        unit = row.get('unit', '')
        unit_price = row.get('unit_price', 0)
        total_cost = row.get('total_cost', 0)
        
        # Парсим описание для получения дополнительной информации
        volume_data = self._parse_volume_from_line(description)
        
        # Определяем конструктивный элемент
        element = self.knowledge_service.identify_construction_element(description)
        
        # Найти подходящую марку бетона
        closest_grade = self._find_closest_grade_in_smeta(description, grades)
        
        # Определяем основной объем/площадь
        volume_m3 = None
        area_m2 = None
        
        if unit.lower() in ['m3', 'м3']:
            volume_m3 = float(quantity) if quantity else volume_data.get('volume_m3')
        elif unit.lower() in ['m2', 'м2']:
            area_m2 = float(quantity) if quantity else volume_data.get('area_m2')
        
        return VolumeEntry(
            concrete_grade=closest_grade.grade if closest_grade else "",
            volume_m3=volume_m3,
            area_m2=area_m2,
            thickness_mm=volume_data.get('thickness_mm'),
            construction_element=element,
            unit_price=float(unit_price) if unit_price else None,
            total_cost=float(total_cost) if total_cost else None,
            unit=unit,
            source_line=description,
            source_document=source_document,
            line_number=row_num + 1,
            confidence=0.8,  # Высокая уверенность для данных сметы
            context=description
        )
    
    def _parse_volume_from_line(self, line: str) -> Dict[str, Any]:
        """Парсит объемы из строки"""
        volume_data = {}
        
        # Ищем объемы м³
        for pattern in [r'(\d+[,.]?\d*)\s*(?:m3|м3)']:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                volume_str = match.group(1).replace(',', '.')
                try:
                    volume_data['volume_m3'] = float(volume_str)
                    volume_data['unit'] = 'm3'
                except ValueError:
                    pass
        
        # Ищем площади м²
        for pattern in [r'(\d+[,.]?\d*)\s*(?:m2|м2)']:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                area_str = match.group(1).replace(',', '.')
                try:
                    volume_data['area_m2'] = float(area_str)
                    if 'unit' not in volume_data:
                        volume_data['unit'] = 'm2'
                except ValueError:
                    pass
        
        # Ищем толщины
        for pattern in [r'(?:толщ|tloušťk|thick)\w*[:\s]*(\d+)\s*(?:mm|мм)']:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    volume_data['thickness_mm'] = float(match.group(1))
                except ValueError:
                    pass
        
        # Ищем цены
        for pattern in self.price_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(',', '.')
                try:
                    volume_data['unit_price'] = float(price_str)
                except ValueError:
                    pass
        
        return volume_data
    
    def _find_closest_grade(self, line_num: int, grades: List, context: str):
        """Находит ближайшую марку бетона"""
        if not grades:
            return None
        
        # Сначала ищем марку в том же контексте
        for grade in grades:
            if grade.line_number == line_num + 1:  # Та же строка
                return grade
        
        # Ищем в соседних строках (в пределах ±5 строк)
        nearby_grades = [g for g in grades if abs(g.line_number - (line_num + 1)) <= 5]
        if nearby_grades:
            return min(nearby_grades, key=lambda g: abs(g.line_number - (line_num + 1)))
        
        # Возвращаем первую найденную марку из документа
        return grades[0] if grades else None
    
    def _find_closest_grade_in_smeta(self, description: str, grades: List):
        """Находит подходящую марку для строки сметы"""
        if not grades:
            return None
        
        # Ищем марку прямо в описании
        for grade in grades:
            if grade.grade in description:
                return grade
        
        # Возвращаем первую подходящую марку
        return grades[0] if grades else None
    
    def _link_volumes_with_grades(self, volumes: List[VolumeEntry], grades: List) -> List[VolumeEntry]:
        """Связывает объемы с марками бетона"""
        # Для объемов без марки пытаемся найти подходящую
        for volume in volumes:
            if not volume.concrete_grade and grades:
                # Ищем марку по конструктивному элементу
                matching_grades = [g for g in grades if g.location == volume.construction_element]
                if matching_grades:
                    volume.concrete_grade = matching_grades[0].grade
                elif grades:
                    # Берем первую доступную марку
                    volume.concrete_grade = grades[0].grade
        
        return volumes
    
    def _calculate_volume_confidence(self, volume_data: Dict, context: str) -> float:
        """Вычисляет уверенность в найденном объеме"""
        confidence = 0.5
        
        # Повышаем за наличие конкретных значений
        if volume_data.get('volume_m3') or volume_data.get('area_m2'):
            confidence += 0.2
        
        # Повышаем за наличие цены
        if volume_data.get('unit_price'):
            confidence += 0.1
        
        # Повышаем за контекстные ключевые слова
        context_keywords = ['beton', 'železobeton', 'monolitick', 'konstrukce']
        context_lower = context.lower()
        
        if any(keyword in context_lower for keyword in context_keywords):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _get_line_context(self, lines: List[str], line_num: int, window: int = 2) -> str:
        """Получает контекст вокруг строки"""
        start = max(0, line_num - window)
        end = min(len(lines), line_num + window + 1)
        
        context_lines = lines[start:end]
        return ' '.join(context_lines).strip()
    
    def group_volumes_by_element(self, volumes: List[VolumeEntry]) -> List[ElementVolumeGroup]:
        """Группирует объемы по конструктивным элементам"""
        grouped = {}
        
        for volume in volumes:
            key = f"{volume.construction_element}_{volume.concrete_grade}"
            
            if key not in grouped:
                grouped[key] = ElementVolumeGroup(
                    element_name=volume.construction_element,
                    concrete_grade=volume.concrete_grade,
                    total_volume_m3=0.0,
                    unit_price=volume.unit_price,
                    total_cost=0.0,
                    entries=[]
                )
            
            group = grouped[key]
            group.entries.append(volume)
            
            # Суммируем объемы
            if volume.volume_m3:
                group.total_volume_m3 += volume.volume_m3
            
            # Суммируем стоимость
            if volume.total_cost:
                group.total_cost = (group.total_cost or 0) + volume.total_cost
        
        return list(grouped.values())
    
    def create_volume_summary(self, volumes: List[VolumeEntry]) -> Dict[str, Any]:
        """Создает сводку по объемам"""
        if not volumes:
            return {
                'total_entries': 0,
                'total_volume_m3': 0,
                'total_cost': 0,
                'grades_summary': {},
                'elements_summary': {}
            }
        
        total_volume = sum(v.volume_m3 for v in volumes if v.volume_m3)
        total_cost = sum(v.total_cost for v in volumes if v.total_cost)
        
        # Группировка по маркам
        grades_summary = {}
        for volume in volumes:
            grade = volume.concrete_grade or 'Неопределенная марка'
            if grade not in grades_summary:
                grades_summary[grade] = {
                    'count': 0,
                    'total_volume_m3': 0,
                    'total_cost': 0
                }
            
            grades_summary[grade]['count'] += 1
            if volume.volume_m3:
                grades_summary[grade]['total_volume_m3'] += volume.volume_m3
            if volume.total_cost:
                grades_summary[grade]['total_cost'] += volume.total_cost
        
        # Группировка по элементам
        elements_summary = {}
        for volume in volumes:
            element = volume.construction_element or 'Неопределенный элемент'
            if element not in elements_summary:
                elements_summary[element] = {
                    'count': 0,
                    'total_volume_m3': 0,
                    'grades_used': set()
                }
            
            elements_summary[element]['count'] += 1
            if volume.volume_m3:
                elements_summary[element]['total_volume_m3'] += volume.volume_m3
            if volume.concrete_grade:
                elements_summary[element]['grades_used'].add(volume.concrete_grade)
        
        # Конвертируем sets в списки для JSON сериализации
        for element_data in elements_summary.values():
            element_data['grades_used'] = list(element_data['grades_used'])
        
        return {
            'total_entries': len(volumes),
            'total_volume_m3': total_volume,
            'total_cost': total_cost,
            'grades_summary': grades_summary,
            'elements_summary': elements_summary
        }


# Singleton instance
_volume_analysis_agent = None

def get_volume_analysis_agent() -> VolumeAnalysisAgent:
    """Получение глобального экземпляра агента анализа объемов"""
    global _volume_analysis_agent
    if _volume_analysis_agent is None:
        _volume_analysis_agent = VolumeAnalysisAgent()
        logger.info("📊 VolumeAnalysisAgent initialized")
    return _volume_analysis_agent


# ==============================
# 🧪 Функция для тестирования
# ==============================

async def test_volume_analysis_agent():
    """Тестирование агента анализа объемов"""
    agent = get_volume_analysis_agent()
    
    # Тестовый текст с объемами
    test_text = """
    MOSTNÍ OPĚRA ZE ŽELEZOBETONU C30/37
    Objem betonu: 125.5 m3
    Cena: 3500 Kč za m3
    
    ZÁKLADOVÁ DESKA C25/30
    Plocha: 85.2 m2
    Tloušťka: 300 mm
    """
    
    print("🧪 TESTING VOLUME ANALYSIS AGENT")
    print("=" * 50)
    
    # Имитируем извлечение объемов
    volumes = agent._extract_volumes_from_text(test_text, "test_document.pdf", [])
    summary = agent.create_volume_summary(volumes)
    
    print(f"📊 Найдено объемов: {len(volumes)}")
    print(f"🏗️ Общий объем: {summary['total_volume_m3']} м³")
    print(f"💰 Общая стоимость: {summary['total_cost']} Kč")
    
    print("\n📋 Детали объемов:")
    for volume in volumes:
        print(f"  • Марка: {volume.concrete_grade}")
        print(f"    Объем: {volume.volume_m3} м³" if volume.volume_m3 else f"    Площадь: {volume.area_m2} м²")
        print(f"    Элемент: {volume.construction_element}")
        print(f"    Уверенность: {volume.confidence:.2f}")
        print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_volume_analysis_agent())