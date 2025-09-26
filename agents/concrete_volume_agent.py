"""
Специализированный агент для анализа объемов бетона
agents/concrete_volume_agent.py

Отвечает за:
1. Извлечение объемов из смет и výkaz výměr
2. Точное связывание марок бетона с объемами
3. Анализ конструктивных элементов
4. Обработку различных форматов документов
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from utils.czech_preprocessor import get_czech_preprocessor

logger = logging.getLogger(__name__)

@dataclass
class VolumeMatch:
    """Структура для найденного объема бетона"""
    concrete_grade: str
    volume_m3: float
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
    context: str  # Дополнительный контекст из окружающих строк

@dataclass
class ElementVolumeGroup:
    """Группировка объемов по конструктивным элементам"""
    element_name: str
    concrete_grade: str
    total_volume_m3: float
    unit_price: Optional[float]
    total_cost: Optional[float]
    entries: List[VolumeMatch]
    
class ConcreteVolumeAgent:
    """
    Специализированный агент для анализа объемов бетона
    Фокусируется только на извлечении и связывании объемов
    """
    
    def __init__(self, knowledge_base_path="knowledge_base/complete-concrete-knowledge-base.json"):
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        self.czech_preprocessor = get_czech_preprocessor()
        
        # Загружаем базу знаний для контекстной проверки
        self.knowledge_base = self._load_knowledge_base(knowledge_base_path)
        
        # Улучшенные паттерны для поиска марок бетона в сметах
        self.concrete_patterns = [
            # Стандартные форматы с контекстом
            r'(?i)(?:beton(?:u|em|y|ové|ová)?|betónová?)\s+(?:třídy?\s+)?((?:LC)?C\d{1,3}/\d{1,3})',
            r'(?i)((?:LC)?C\d{1,3}/\d{1,3})\s*[-–]\s*[XO][CDFASM]?\d*',
            r'(?i)betón\s+((?:LC)?C\d{1,3}/\d{1,3})',
            r'(?i)ze\s+železobetonu\s+(?:do\s+)?((?:LC)?C\d{1,3}/\d{1,3})',
            r'(?i)prostý\s+beton\s+((?:LC)?C\d{1,3}/\d{1,3})',
            
            # Паттерны для строк типа "MOSTNÍ OPĚRY A KŘÍDLA ZE ŽELEZOBETONU DO C30/37"
            r'(?i)(?:mostní|železobeton|ze|do)\s+.*?((?:LC)?C\d{1,3}/\d{1,3})',
        ]
        
        # Улучшенные паттерны для поиска объемов с контекстом
        self.volume_patterns = [
            # Кубические метры с различными форматами
            r'(\d+(?:[,.]\d+)?)\s*(?:m3|m³|m\^3|кб\.?м|кубич)',
            # Квадратные метры 
            r'(\d+(?:[,.]\d+)?)\s*(?:m2|m²|m\^2|кв\.?м|квадр)',
            # Штуки/количество
            r'(\d+(?:[,.]\d+)?)\s*(?:ks|шт\.?|pc\.?|kusů)',
            # Тонны
            r'(\d+(?:[,.]\d+)?)\s*(?:t|тонн?\.?|tuny?)',
        ]
        
        # Паттерны для поиска цен
        self.price_patterns = [
            r'(\d+(?:[,.]?\d+)?)\s*(?:Kč|CZK|кч|крон)',  # Цены в кронах
            r'(\d+(?:[,.]?\d+)?)\s*(?:EUR|евро)',         # Цены в евро
        ]
        
        # Расширенный словарь конструктивных элементов
        self.construction_elements = {
            # Основные конструкции
            'opěr': ['opěra', 'opěry', 'abutment', 'опора'],
            'pilíř': ['pilíř', 'pilíře', 'pier', 'столб', 'пилон'],
            'říms': ['římsa', 'říms', 'cornice', 'карниз'],
            'mostovk': ['mostovka', 'deck', 'настил'],
            'základ': ['základ', 'základy', 'foundation', 'фундамент'],
            'krídl': ['křídlo', 'křídla', 'wing', 'крыло'],
            
            # Детальные элементы
            'desk': ['deska', 'desky', 'slab', 'плита'],
            'stěn': ['stěna', 'stěny', 'wall', 'стена'],
            'sloup': ['sloup', 'sloupy', 'column', 'колонна'],
            'trám': ['trám', 'trámy', 'beam', 'балка'],
            'schodišt': ['schodiště', 'stairs', 'лестница'],
            'podkladn': ['podkladní', 'subgrade', 'подкладочный'],
            'mazanin': ['mazanina', 'screed', 'стяжка'],
            'chodník': ['chodník', 'sidewalk', 'тротуар'],
            'vozovk': ['vozovka', 'roadway', 'проезжая часть'],
            
            # Специальные конструкции
            'prefabrikát': ['prefabrikát', 'precast', 'сборный'],
            'monolitick': ['monolitický', 'monolithic', 'монолитный'],
            'železobeton': ['železobeton', 'reinforced concrete', 'железобетон'],
            'prostý': ['prostý beton', 'plain concrete', 'простой бетон'],
        }

    def _load_knowledge_base(self, path: str) -> Dict[str, Any]:
        """Загружает базу знаний для контекстной проверки"""
        try:
            if Path(path).exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить базу знаний: {e}")
        
        return {
            "concrete_grades": ["C12/15", "C16/20", "C20/25", "C25/30", "C30/37", "C35/45", "LC25/28"],
            "exposure_classes": ["X0", "XC1", "XC2", "XC3", "XC4", "XD1", "XD2", "XD3", "XF1", "XF2", "XF3", "XF4"]
        }

    async def analyze_volumes_from_documents(self, doc_paths: List[str], 
                                           smeta_path: Optional[str] = None) -> List[VolumeMatch]:
        """
        Главная функция для анализа объемов из документов
        
        Args:
            doc_paths: Список путей к основным документам
            smeta_path: Путь к смете или výkaz výměr
            
        Returns:
            Список найденных объемов бетона
        """
        logger.info(f"🔍 Начинаем анализ объемов из {len(doc_paths)} документов")
        
        all_volumes = []
        
        # Анализируем основные документы
        for doc_path in doc_paths:
            try:
                volumes = await self._analyze_single_document(doc_path)
                all_volumes.extend(volumes)
                logger.info(f"📄 {doc_path}: найдено {len(volumes)} объемов")
            except Exception as e:
                logger.error(f"❌ Ошибка анализа {doc_path}: {e}")
        
        # Анализируем смету отдельно (приоритет)
        if smeta_path:
            try:
                smeta_volumes = await self._analyze_smeta_document(smeta_path)
                all_volumes.extend(smeta_volumes)
                logger.info(f"📊 Смета {smeta_path}: найдено {len(smeta_volumes)} объемов")
            except Exception as e:
                logger.error(f"❌ Ошибка анализа сметы {smeta_path}: {e}")
        
        # Деупликация и группировка
        deduplicated = self._deduplicate_volumes(all_volumes)
        
        logger.info(f"✅ Итого найдено {len(deduplicated)} уникальных объемов")
        return deduplicated

    async def _analyze_single_document(self, doc_path: str) -> List[VolumeMatch]:
        """Анализирует один документ на предмет объемов"""
        volumes = []
        
        try:
            # Извлекаем текст документа
            text = await self.doc_parser.parse_document(doc_path)
            if not text or len(text.strip()) < 50:
                return volumes
                
            # Предобработка чешского текста
            processed_text = self.czech_preprocessor.process_text(text)
            
            # Извлекаем объемы
            volumes = self._extract_volumes_from_text(processed_text, doc_path)
            
        except Exception as e:
            logger.error(f"Ошибка анализа документа {doc_path}: {e}")
            
        return volumes

    async def _analyze_smeta_document(self, smeta_path: str) -> List[VolumeMatch]:
        """Специализированный анализ сметы"""
        volumes = []
        
        try:
            # Используем специализированный парсер смет
            smeta_data = await self.smeta_parser.parse_smeta(smeta_path)
            
            if smeta_data.get('items'):
                # Структурированные данные сметы
                volumes = self._extract_volumes_from_smeta_items(smeta_data['items'], smeta_path)
            elif smeta_data.get('raw_text'):
                # Текстовые данные сметы
                volumes = self._extract_volumes_from_text(smeta_data['raw_text'], smeta_path)
                
        except Exception as e:
            logger.error(f"Ошибка анализа сметы {smeta_path}: {e}")
            
        return volumes

    def _extract_volumes_from_text(self, text: str, document_name: str) -> List[VolumeMatch]:
        """Извлекает объемы из текста документа"""
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
                
            # Получаем контекст (соседние строки)
            context = self._get_line_context(lines, line_num, window=2)
            
            # Ищем объемы в этой же строке или соседних
            volume_matches = self._extract_volumes_from_line(
                line_clean, context, line_num, document_name
            )
            
            if volume_matches:
                # Определяем конструктивный элемент
                element = self._identify_construction_element(line_clean, context)
                
                for vol_match in volume_matches:
                    vol_match.concrete_grade = concrete_grade
                    vol_match.construction_element = element
                    vol_match.context = context[:200]  # Ограничиваем длину контекста
                    volumes.append(vol_match)
        
        return volumes

    def _extract_concrete_grade(self, line: str) -> Optional[str]:
        """Извлекает марку бетона из строки с улучшенным распознаванием"""
        for pattern in self.concrete_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                grade = match.group(1).upper().strip()
                # Нормализуеми формат
                if re.match(r'^(?:LC)?C\d{1,3}/\d{1,3}$', grade):
                    return grade
        return None

    def _get_line_context(self, lines: List[str], line_num: int, window: int = 2) -> str:
        """Получает контекст вокруг строки"""
        start = max(0, line_num - window)
        end = min(len(lines), line_num + window + 1)
        context_lines = lines[start:end]
        return ' '.join(l.strip() for l in context_lines if l.strip())

    def _extract_volumes_from_line(self, line: str, context: str, line_num: int, 
                                 document_name: str) -> List[VolumeMatch]:
        """Извлекает объемы из строки с контекстом"""
        volumes = []
        search_text = f"{line} {context}"
        
        # Поиск м³
        for match in re.finditer(self.volume_patterns[0], search_text, re.IGNORECASE):
            volume_str = match.group(1).replace(',', '.')
            try:
                volume = float(volume_str)
                if volume > 0:  # Только положительные объемы
                    vol_match = VolumeMatch(
                        concrete_grade="",  # Будет заполнено выше
                        volume_m3=volume,
                        area_m2=None,
                        thickness_mm=None,
                        construction_element="",  # Будет заполнено выше
                        unit_price=self._extract_unit_price(search_text),
                        total_cost=self._extract_total_cost(search_text),
                        unit='m3',
                        source_line=line,
                        source_document=document_name,
                        line_number=line_num + 1,
                        confidence=0.9,
                        context=""  # Будет заполнено выше
                    )
                    volumes.append(vol_match)
            except ValueError:
                continue
        
        # Поиск м² с возможной толщиной
        for match in re.finditer(self.volume_patterns[1], search_text, re.IGNORECASE):
            area_str = match.group(1).replace(',', '.')
            try:
                area = float(area_str)
                if area > 0:
                    thickness = self._extract_thickness(search_text)
                    volume = area * (thickness / 1000) if thickness else 0.0
                    
                    vol_match = VolumeMatch(
                        concrete_grade="",
                        volume_m3=volume,
                        area_m2=area,
                        thickness_mm=thickness,
                        construction_element="",
                        unit_price=self._extract_unit_price(search_text),
                        total_cost=self._extract_total_cost(search_text),
                        unit='m2',
                        source_line=line,
                        source_document=document_name,
                        line_number=line_num + 1,
                        confidence=0.8 if thickness else 0.6,
                        context=""
                    )
                    volumes.append(vol_match)
            except ValueError:
                continue
        
        return volumes

    def _extract_thickness(self, text: str) -> Optional[float]:
        """Извлекает толщину из текста"""
        thickness_patterns = [
            r'(?i)(?:tl\.?|толщ\.?|thick\.?)\s*(\d+)\s*(?:mm|мм)',
            r'(\d+)\s*(?:mm|мм)(?:\s+thick)?',
            r'(?i)(?:h|высота)\s*=?\s*(\d+)\s*(?:mm|мм)',
        ]
        
        for pattern in thickness_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    def _extract_unit_price(self, text: str) -> Optional[float]:
        """Извлекает единичную цену"""
        for pattern in self.price_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    price_str = match.group(1).replace(',', '.')
                    return float(price_str)
                except ValueError:
                    continue
        return None

    def _extract_total_cost(self, text: str) -> Optional[float]:
        """Извлекает общую стоимость (проще - ищем большие числа с валютой)"""
        # Ищем большие суммы (обычно общая стоимость > единичной)
        large_price_pattern = r'(\d{3,}(?:[,.]?\d+)?)\s*(?:Kč|CZK|кч|крон)'
        match = re.search(large_price_pattern, text)
        if match:
            try:
                cost_str = match.group(1).replace(',', '.')
                return float(cost_str)
            except ValueError:
                pass
        return None

    def _identify_construction_element(self, line: str, context: str) -> str:
        """Определяет тип конструктивного элемента"""
        full_text = f"{line} {context}".lower()
        
        # Ищем по ключевым словам
        for element_key, synonyms in self.construction_elements.items():
            for synonym in synonyms:
                if synonym.lower() in full_text:
                    return element_key
        
        # Если не нашли конкретный элемент, пытаемся определить общий тип
        if any(word in full_text for word in ['základ', 'foundation', 'фундамент']):
            return 'základ'
        elif any(word in full_text for word in ['stěn', 'wall', 'стена']):
            return 'stěn'
        elif any(word in full_text for word in ['desk', 'slab', 'плита']):
            return 'desk'
        else:
            return 'unknown'

    def _extract_volumes_from_smeta_items(self, items: List[Dict], smeta_path: str) -> List[VolumeMatch]:
        """Извлекает объемы из структурированных данных сметы"""
        volumes = []
        
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
                
            # Ищем марку бетона в описании
            description = item.get('description', '') or item.get('popis', '')
            concrete_grade = self._extract_concrete_grade(description)
            
            if not concrete_grade:
                continue
                
            # Извлекаем объем
            volume_m3 = 0.0
            area_m2 = None
            thickness_mm = None
            unit = item.get('unit', '') or item.get('mj', '')
            quantity = item.get('quantity', 0) or item.get('mnozstvi', 0)
            
            try:
                quantity = float(str(quantity).replace(',', '.'))
            except (ValueError, TypeError):
                quantity = 0.0
                
            if quantity <= 0:
                continue
                
            # Определяем тип единицы и рассчитываем объем
            unit_lower = unit.lower()
            if 'm3' in unit_lower or 'm³' in unit_lower:
                volume_m3 = quantity
            elif 'm2' in unit_lower or 'm²' in unit_lower:
                area_m2 = quantity
                thickness_mm = self._extract_thickness(description)
                if thickness_mm:
                    volume_m3 = area_m2 * (thickness_mm / 1000)
            else:
                # Пропускаем неопределенные единицы
                continue
                
            # Извлекаем цены
            unit_price = None
            total_cost = None
            
            if 'unit_price' in item or 'jednotkova_cena' in item:
                try:
                    price_val = item.get('unit_price') or item.get('jednotkova_cena')
                    unit_price = float(str(price_val).replace(',', '.'))
                except (ValueError, TypeError):
                    pass
                    
            if 'total_cost' in item or 'celkem' in item:
                try:
                    cost_val = item.get('total_cost') or item.get('celkem')
                    total_cost = float(str(cost_val).replace(',', '.'))
                except (ValueError, TypeError):
                    pass
                    
            # Определяем конструктивный элемент
            element = self._identify_construction_element(description, "")
            
            vol_match = VolumeMatch(
                concrete_grade=concrete_grade,
                volume_m3=volume_m3,
                area_m2=area_m2,
                thickness_mm=thickness_mm,
                construction_element=element,
                unit_price=unit_price,
                total_cost=total_cost,
                unit=unit,
                source_line=description,
                source_document=smeta_path,
                line_number=i + 1,
                confidence=0.95,  # Высокая уверенность для структурированных данных
                context=description
            )
            
            volumes.append(vol_match)
            
        return volumes

    def _deduplicate_volumes(self, volumes: List[VolumeMatch]) -> List[VolumeMatch]:
        """Удаляет дубликаты объемов"""
        if not volumes:
            return volumes
            
        # Группируем по ключевым признакам
        groups = {}
        for vol in volumes:
            # Создаем ключ для группировки
            key = (
                vol.concrete_grade,
                vol.construction_element,
                round(vol.volume_m3, 2),  # Округляем для сравнения
                vol.source_document
            )
            
            if key not in groups:
                groups[key] = []
            groups[key].append(vol)
        
        # Оставляем лучший из группы (с наивысшей уверенностью)
        deduplicated = []
        for group in groups.values():
            best_match = max(group, key=lambda x: x.confidence)
            deduplicated.append(best_match)
        
        return deduplicated

    def group_volumes_by_grade(self, volumes: List[VolumeMatch]) -> Dict[str, ElementVolumeGroup]:
        """Группирует объемы по маркам бетона и элементам"""
        groups = {}
        
        for volume in volumes:
            key = f"{volume.concrete_grade}_{volume.construction_element}"
            
            if key not in groups:
                groups[key] = ElementVolumeGroup(
                    element_name=volume.construction_element,
                    concrete_grade=volume.concrete_grade,
                    total_volume_m3=0.0,
                    unit_price=volume.unit_price,
                    total_cost=0.0,
                    entries=[]
                )
            
            group = groups[key]
            group.total_volume_m3 += volume.volume_m3
            group.entries.append(volume)
            
            if volume.total_cost:
                group.total_cost = (group.total_cost or 0) + volume.total_cost
        
        return groups

    def create_volume_summary(self, volumes: List[VolumeMatch]) -> Dict[str, Any]:
        """Создает сводку по объемам"""
        if not volumes:
            return {
                'total_grades_found': 0,
                'total_volume_m3': 0.0,
                'total_cost': 0.0,
                'grades_summary': {},
                'elements_summary': {}
            }
        
        # Группируем данные
        grouped = self.group_volumes_by_grade(volumes)
        
        # Создаем сводки
        grades_summary = {}
        elements_summary = {}
        total_volume = 0.0
        total_cost = 0.0
        
        for group in grouped.values():
            grade = group.concrete_grade
            element = group.element_name
            
            # Сводка по маркам
            if grade not in grades_summary:
                grades_summary[grade] = {
                    'total_volume_m3': 0.0,
                    'total_cost': 0.0,
                    'elements': []
                }
            
            grades_summary[grade]['total_volume_m3'] += group.total_volume_m3
            grades_summary[grade]['total_cost'] += (group.total_cost or 0)
            grades_summary[grade]['elements'].append({
                'element': element,
                'volume_m3': group.total_volume_m3,
                'cost': group.total_cost
            })
            
            # Сводка по элементам
            if element not in elements_summary:
                elements_summary[element] = {
                    'total_volume_m3': 0.0,
                    'grades': []
                }
            
            elements_summary[element]['total_volume_m3'] += group.total_volume_m3
            elements_summary[element]['grades'].append({
                'grade': grade,
                'volume_m3': group.total_volume_m3
            })
            
            total_volume += group.total_volume_m3
            total_cost += (group.total_cost or 0)
        
        return {
            'total_grades_found': len(grades_summary),
            'total_volume_m3': round(total_volume, 2),
            'total_cost': round(total_cost, 2),
            'grades_summary': grades_summary,
            'elements_summary': elements_summary,
            'detailed_entries': [asdict(vol) for vol in volumes]
        }

# Singleton instance
_volume_agent = None

def get_concrete_volume_agent() -> ConcreteVolumeAgent:
    """Получение глобального экземпляра агента объемов"""
    global _volume_agent
    if _volume_agent is None:
        _volume_agent = ConcreteVolumeAgent()
        logger.info("🏗️ ConcreteVolumeAgent initialized")
    return _volume_agent


# ==============================
# 🧪 Функция для тестирования
# ==============================

async def test_volume_agent():
    """Тестирование агента объемов"""
    agent = get_concrete_volume_agent()
    
    test_text = """
    801.001.001 Beton prostý C12/15-X0 125,50 m3 2500 Kč 313750 Kč
    801.002.001 Železobeton C25/30-XC2 základy 85,25 m3 3200 Kč 272800 Kč
    801.003.001 Mazanina C16/20 tl. 120 mm 450,00 m2 850 Kč 382500 Kč
    802.001.001 Betonová deska C30/37-XC4 200,00 m2 tl. 250 mm 1200 Kč 240000 Kč
    MOSTNÍ OPĚRY A KŘÍDLA ZE ŽELEZOBETONU DO C30/37 255,7 m3
    ŘÍMS ZE ŽELEZOBETONU DO C30/37 176,768 m3
    """
    
    volumes = agent._extract_volumes_from_text(test_text, "test_smeta.txt")
    summary = agent.create_volume_summary(volumes)
    
    print("🧪 TESTING CONCRETE VOLUME AGENT")
    print("=" * 50)
    print(f"📊 Найдено объемов: {len(volumes)}")
    print(f"🏗️ Марок бетона: {summary['total_grades_found']}")
    print(f"📐 Общий объем: {summary['total_volume_m3']} м³")
    print(f"💰 Общая стоимость: {summary['total_cost']} Kč")
    
    print("\n📋 Детали по маркам:")
    for grade, data in summary['grades_summary'].items():
        print(f"  {grade}: {data['total_volume_m3']} м³")
        for elem in data['elements']:
            print(f"    - {elem['element']}: {elem['volume_m3']} м³")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_volume_agent())