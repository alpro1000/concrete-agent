"""
Специализированный агент для анализа строительных материалов
agents/material_agent/agent.py

Отвечает только за:
1. Идентификацию строительных материалов
2. Анализ арматуры и стали
3. Определение изоляционных материалов
4. Анализ окон, дверей и фурнитуры
5. Категоризацию материалов по типам
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from services.doc_parser import parse_document  # New unified parser
from utils.knowledge_base_service import get_knowledge_service
from utils.czech_preprocessor import get_czech_preprocessor

logger = logging.getLogger(__name__)

@dataclass
class MaterialItem:
    """Структура для найденного материала"""
    material_type: str  # reinforcement, windows, insulation, etc.
    material_name: str
    specification: str  # Fe500, PVC, EPDM, etc.
    quantity: Optional[float]
    unit: str  # kg, m2, ks, m
    context: str
    source_document: str
    line_number: int
    confidence: float

@dataclass
class MaterialCategory:
    """Категория материалов"""
    category_name: str
    total_items: int
    items: List[MaterialItem]
    total_quantity: float
    main_specifications: List[str]

class MaterialAnalysisAgent:
    """Специализированный агент для анализа строительных материалов"""
    
    def __init__(self):
        self.knowledge_service = get_knowledge_service()
        self.czech_preprocessor = get_czech_preprocessor()
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        
        logger.info("🔧 MaterialAnalysisAgent initialized")
        
        # Загружаем паттерны материалов
        self.material_patterns = self._load_material_patterns()
        
        # Паттерны для извлечения количеств
        self.quantity_patterns = [
            r'(\d+[,.]?\d*)\s*(?:kg|кг)',  # килограммы
            r'(\d+[,.]?\d*)\s*(?:m2|м2)',  # квадратные метры
            r'(\d+[,.]?\d*)\s*(?:m|м)(?![2-9])',  # метры (не м2, м3)
            r'(\d+[,.]?\d*)\s*(?:ks|шт)',  # штуки
            r'(\d+[,.]?\d*)\s*(?:t|тонн)',  # тонны
            r'(\d+[,.]?\d*)\s*(?:l|литр)',  # литры
        ]
    
    def _load_material_patterns(self) -> Dict[str, Dict]:
        """Загружает паттерны для поиска материалов"""
        patterns = {
            "reinforcement": {
                "patterns": [
                    r'\b(?:výztuž|арматур)\w*\s+(?:Fe\s?(\d{3})|R(\d{2,3}))',
                    r'\b(?:ocel|сталь)\s+(?:Fe\s?(\d{3})|R(\d{2,3}))',
                    r'\bFe\s?(\d{3})\b',
                    r'\bR(\d{2,3})\b',
                    r'\b(?:betonářsk[áé]|арматурн)\w*\s+výztuž',
                ],
                "specifications": ["Fe500", "Fe400", "R10", "R12", "R16", "R20", "R25", "R32"],
                "units": ["kg", "t", "m"]
            },
            
            "windows": {
                "patterns": [
                    r'\b(?:okn[oa]|окн)\w*\s+(?:PVC|дерев|hliník|plastik)',
                    r'\b(?:PVC|пластик)\w*\s+(?:okn|окн)',
                    r'\b(?:dřevěn[éá]|деревянн)\w*\s+(?:okn|окн)',
                    r'\b(?:hliníkov[éá]|алюминиев)\w*\s+(?:okn|окн)',
                    r'\b(?:zasklení|остеклен)',
                ],
                "specifications": ["PVC", "dřevo", "hliník", "plastik"],
                "units": ["ks", "m2"]
            },
            
            "insulation": {
                "patterns": [
                    r'\b(?:izolac[eí]|изоляц)\w*\s+(?:XPS|EPS|minerální|каменн)',
                    r'\b(?:tepeln[áé]|теплов)\w*\s+izolac',
                    r'\b(?:polystyren|пенопласт|пенополистирол)',
                    r'\b(?:minerální|минеральн)\w*\s+(?:vlna|вата)',
                    r'\bXPS\b|\bEPS\b',
                ],
                "specifications": ["XPS", "EPS", "minerální vlna", "polystyren"],
                "units": ["m2", "m3", "kg"]
            },
            
            "sealing": {
                "patterns": [
                    r'\b(?:těsněn[íé]|уплотнен)\w*\s+(?:EPDM|pryž|резин)',
                    r'\b(?:těsnicí|уплотнительн)\w*\s+(?:pás|лента|profil)',
                    r'\bEPDM\b',
                    r'\b(?:gumov[éá]|резинов)\w*\s+(?:těsněn|уплотнен)',
                ],
                "specifications": ["EPDM", "pryž", "guma", "PVC"],
                "units": ["m", "ks"]
            },
            
            "metal_structures": {
                "patterns": [
                    r'\b(?:konstrukce|конструкц)\w*\s+(?:z\s+)?(?:oceli|стал)',
                    r'\b(?:ocelový|стальн)\w*\s+(?:rám|frame|каркас)',
                    r'\b(?:nosník|балк)\w*\s+(?:ocelový|стальн)',
                    r'\b(?:sloup|колонн)\w*\s+(?:ocelový|стальн)',
                    r'\b(?:profil|профиль)\s+(?:IPE|HEA|HEB|UPE)',
                ],
                "specifications": ["IPE", "HEA", "HEB", "UPE", "ocel S235", "ocel S355"],
                "units": ["kg", "t", "m"]
            },
            
            "doors": {
                "patterns": [
                    r'\b(?:dveř[eí]|двер)\w*\s+(?:PVC|dřev|hliník)',
                    r'\b(?:vchodov[éá]|входн)\w*\s+dveř',
                    r'\b(?:interiérov[éá]|внутренн)\w*\s+dveř',
                    r'\b(?:bezpečnostn[íé]|безопасност)\w*\s+dveř',
                ],
                "specifications": ["PVC", "dřevo", "hliník", "ocel"],
                "units": ["ks", "m2"]
            },
            
            "roofing": {
                "patterns": [
                    r'\b(?:střešn[íé]|кровельн)\w*\s+(?:krytina|материал)',
                    r'\b(?:plechov[áé]|металлическ)\w*\s+(?:krytina|кровл)',
                    r'\b(?:tašk[ay]|черепиц)',
                    r'\b(?:membránu|мембран)\w*\s+(?:střešn|кровельн)',
                ],
                "specifications": ["plech", "tašky", "membrána", "eternit"],
                "units": ["m2", "ks"]
            }
        }
        
        return patterns
    
    async def analyze_materials(self, doc_paths: List[str], 
                              smeta_path: Optional[str] = None) -> List[MaterialItem]:
        """Анализирует материалы из документов"""
        logger.info(f"🔧 Начинаем анализ материалов из {len(doc_paths)} документов")
        
        all_materials = []
        
        # Обрабатываем основные документы
        for doc_path in doc_paths:
            materials = await self._extract_materials_from_document(doc_path)
            all_materials.extend(materials)
        
        # Обрабатываем смету отдельно
        if smeta_path:
            smeta_materials = await self._extract_materials_from_smeta(smeta_path)
            all_materials.extend(smeta_materials)
        
        # Фильтруем и валидируем материалы
        validated_materials = self._validate_materials(all_materials)
        
        logger.info(f"✅ Найдено {len(validated_materials)} материалов")
        return validated_materials
    
    async def _extract_materials_from_document(self, doc_path: str) -> List[MaterialItem]:
        """Извлекает материалы из документа"""
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
            materials = self._extract_materials_from_text(text, doc_path)
            
            # Log which parser was used
            if result["results"]:
                logger.info(f"📊 Материалы извлечены из {Path(doc_path).name}: {len(materials)} (parser: {result['results'][0].parser_used})")
                
            return materials
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки документа {doc_path}: {e}")
            return []
    
    async def _extract_materials_from_smeta(self, smeta_path: str) -> List[MaterialItem]:
        """Извлекает материалы из сметы"""
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
            
            materials = []
            for row_num, row in enumerate(smeta_data):
                if isinstance(row, dict):
                    material_items = self._extract_materials_from_smeta_row(
                        row, smeta_path, row_num
                    )
                    materials.extend(material_items)
            
            # Log which parser was used
            if result["results"]:
                logger.info(f"📊 Материалы из сметы {Path(smeta_path).name}: {len(materials)} (parser: {result['results'][0].parser_used})")
            
            return materials
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сметы {smeta_path}: {e}")
            return []
    
    def _extract_materials_from_text(self, text: str, source_document: str) -> List[MaterialItem]:
        """Извлекает материалы из текста"""
        materials = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 5:
                continue
            
            # Проверяем каждую категорию материалов
            for category, category_data in self.material_patterns.items():
                for pattern in category_data["patterns"]:
                    matches = re.finditer(pattern, line_clean, re.IGNORECASE)
                    for match in matches:
                        # Извлекаем спецификацию из группы или определяем по контексту
                        specification = self._extract_specification(
                            match, line_clean, category_data["specifications"]
                        )
                        
                        # Получаем контекст
                        context = self._get_line_context(lines, line_num)
                        
                        # Извлекаем количество
                        quantity, unit = self._extract_quantity_and_unit(
                            line_clean, category_data["units"]
                        )
                        
                        material = MaterialItem(
                            material_type=category,
                            material_name=match.group(0),
                            specification=specification,
                            quantity=quantity,
                            unit=unit,
                            context=context[:200],
                            source_document=source_document,
                            line_number=line_num + 1,
                            confidence=self._calculate_material_confidence(
                                category, specification, quantity, context
                            )
                        )
                        
                        materials.append(material)
        
        return materials
    
    def _extract_materials_from_smeta_row(self, row: Dict, source_document: str, 
                                        row_num: int) -> List[MaterialItem]:
        """Извлекает материалы из строки сметы"""
        materials = []
        description = row.get('description', '')
        quantity = row.get('quantity', 0)
        unit = row.get('unit', '')
        
        # Проверяем каждую категорию материалов
        for category, category_data in self.material_patterns.items():
            for pattern in category_data["patterns"]:
                matches = re.finditer(pattern, description, re.IGNORECASE)
                for match in matches:
                    specification = self._extract_specification(
                        match, description, category_data["specifications"]
                    )
                    
                    material = MaterialItem(
                        material_type=category,
                        material_name=match.group(0),
                        specification=specification,
                        quantity=float(quantity) if quantity else None,
                        unit=unit,
                        context=description,
                        source_document=source_document,
                        line_number=row_num + 1,
                        confidence=0.8  # Высокая уверенность для данных сметы
                    )
                    
                    materials.append(material)
        
        return materials
    
    def _extract_specification(self, match, line: str, possible_specs: List[str]) -> str:
        """Извлекает спецификацию материала"""
        # Сначала проверяем группы в регулярном выражении
        if match.groups():
            for group in match.groups():
                if group:
                    return group
        
        # Ищем спецификации в строке
        line_upper = line.upper()
        for spec in possible_specs:
            if spec.upper() in line_upper:
                return spec
        
        return ""
    
    def _extract_quantity_and_unit(self, line: str, preferred_units: List[str]) -> tuple:
        """Извлекает количество и единицу измерения"""
        for pattern in self.quantity_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                quantity_str = match.group(1).replace(',', '.')
                try:
                    quantity = float(quantity_str)
                    
                    # Определяем единицу из паттерна
                    unit_match = re.search(r'(\w+)(?:\)|\])?$', match.group(0))
                    unit = unit_match.group(1) if unit_match else ""
                    
                    return quantity, unit
                except ValueError:
                    continue
        
        return None, ""
    
    def _calculate_material_confidence(self, category: str, specification: str, 
                                     quantity: Optional[float], context: str) -> float:
        """Вычисляет уверенность в найденном материале"""
        confidence = 0.6  # Базовая уверенность
        
        # Повышаем за наличие спецификации
        if specification:
            confidence += 0.2
        
        # Повышаем за наличие количества
        if quantity is not None:
            confidence += 0.1
        
        # Повышаем за контекстные ключевые слова
        context_keywords = {
            "reinforcement": ["výztuž", "арматур", "ocel", "сталь"],
            "windows": ["okno", "окн", "zasklení", "остеклен"],
            "insulation": ["izolace", "изоляц", "tepelná", "теплов"],
            "sealing": ["těsnění", "уплотнен"],
            "metal_structures": ["konstrukce", "конструкц", "nosník", "балк"],
            "doors": ["dveře", "двер"],
            "roofing": ["střešní", "кровельн", "krytina"]
        }
        
        category_keywords = context_keywords.get(category, [])
        context_lower = context.lower()
        
        if any(keyword in context_lower for keyword in category_keywords):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _get_line_context(self, lines: List[str], line_num: int, window: int = 1) -> str:
        """Получает контекст вокруг строки"""
        start = max(0, line_num - window)
        end = min(len(lines), line_num + window + 1)
        
        context_lines = lines[start:end]
        return ' '.join(context_lines).strip()
    
    def _validate_materials(self, materials: List[MaterialItem]) -> List[MaterialItem]:
        """Валидирует и фильтрует материалы"""
        validated = []
        seen_materials = set()
        
        for material in materials:
            # Убираем дубликаты
            material_key = f"{material.material_type}_{material.material_name}_{material.source_document}_{material.line_number}"
            if material_key in seen_materials:
                continue
            seen_materials.add(material_key)
            
            # Фильтруем по минимальной уверенности
            if material.confidence >= 0.5:
                validated.append(material)
        
        return validated
    
    def categorize_materials(self, materials: List[MaterialItem]) -> List[MaterialCategory]:
        """Категоризирует материалы по типам"""
        categories = {}
        
        for material in materials:
            category_name = material.material_type
            
            if category_name not in categories:
                categories[category_name] = MaterialCategory(
                    category_name=category_name,
                    total_items=0,
                    items=[],
                    total_quantity=0.0,
                    main_specifications=[]
                )
            
            category = categories[category_name]
            category.items.append(material)
            category.total_items += 1
            
            if material.quantity:
                category.total_quantity += material.quantity
        
        # Определяем основные спецификации для каждой категории
        for category in categories.values():
            specs = [m.specification for m in category.items if m.specification]
            # Берем наиболее частые спецификации
            spec_counts = {}
            for spec in specs:
                spec_counts[spec] = spec_counts.get(spec, 0) + 1
            
            category.main_specifications = sorted(
                spec_counts.keys(), 
                key=lambda x: spec_counts[x], 
                reverse=True
            )[:3]  # Топ-3 спецификации
        
        return list(categories.values())
    
    def create_material_summary(self, materials: List[MaterialItem]) -> Dict[str, Any]:
        """Создает сводку по материалам"""
        if not materials:
            return {
                'total_materials': 0,
                'categories_count': 0,
                'categories': {},
                'specifications_summary': {},
                'documents_summary': {}
            }
        
        categories = self.categorize_materials(materials)
        
        # Сводка по категориям
        categories_summary = {}
        for category in categories:
            categories_summary[category.category_name] = {
                'count': category.total_items,
                'total_quantity': category.total_quantity,
                'main_specifications': category.main_specifications
            }
        
        # Сводка по спецификациям
        specifications_summary = {}
        for material in materials:
            if material.specification:
                spec = material.specification
                if spec not in specifications_summary:
                    specifications_summary[spec] = {
                        'count': 0,
                        'categories': set(),
                        'total_quantity': 0
                    }
                
                specifications_summary[spec]['count'] += 1
                specifications_summary[spec]['categories'].add(material.material_type)
                if material.quantity:
                    specifications_summary[spec]['total_quantity'] += material.quantity
        
        # Конвертируем sets в списки для JSON сериализации
        for spec_data in specifications_summary.values():
            spec_data['categories'] = list(spec_data['categories'])
        
        # Сводка по документам
        documents_summary = {}
        for material in materials:
            doc = material.source_document
            if doc not in documents_summary:
                documents_summary[doc] = {
                    'materials_count': 0,
                    'categories': set()
                }
            
            documents_summary[doc]['materials_count'] += 1
            documents_summary[doc]['categories'].add(material.material_type)
        
        # Конвертируем sets в списки
        for doc_data in documents_summary.values():
            doc_data['categories'] = list(doc_data['categories'])
        
        return {
            'total_materials': len(materials),
            'categories_count': len(categories),
            'categories': categories_summary,
            'specifications_summary': specifications_summary,
            'documents_summary': documents_summary
        }


# Singleton instance
_material_analysis_agent = None

def get_material_analysis_agent() -> MaterialAnalysisAgent:
    """Получение глобального экземпляра агента анализа материалов"""
    global _material_analysis_agent
    if _material_analysis_agent is None:
        _material_analysis_agent = MaterialAnalysisAgent()
        logger.info("🔧 MaterialAnalysisAgent initialized")
    return _material_analysis_agent


# ==============================
# 🧪 Функция для тестирования
# ==============================

async def test_material_analysis_agent():
    """Тестирование агента анализа материалов"""
    agent = get_material_analysis_agent()
    
    # Тестовый текст с материалами
    test_text = """
    Výztuž: Fe500 - 2500 kg
    Okna PVC - 15 ks
    Tepelná izolace XPS 100mm - 85.5 m2
    Ocelový nosník IPE200 - 450 kg
    Střešní krytina - tašky keramické - 125 m2
    Těsnění EPDM - 45 m
    """
    
    print("🧪 TESTING MATERIAL ANALYSIS AGENT")
    print("=" * 50)
    
    # Имитируем извлечение материалов
    materials = agent._extract_materials_from_text(test_text, "test_document.pdf")
    summary = agent.create_material_summary(materials)
    categories = agent.categorize_materials(materials)
    
    print(f"🔧 Найдено материалов: {len(materials)}")
    print(f"📂 Категорий: {len(categories)}")
    
    print("\n📋 Категории материалов:")
    for category in categories:
        print(f"  • {category.category_name}: {category.total_items} шт.")
        print(f"    Основные спецификации: {', '.join(category.main_specifications)}")
        print(f"    Общее количество: {category.total_quantity}")
        print()
    
    print("📊 Детали материалов:")
    for material in materials:
        print(f"  • {material.material_name}")
        print(f"    Тип: {material.material_type}")
        print(f"    Спецификация: {material.specification}")
        print(f"    Количество: {material.quantity} {material.unit}")
        print(f"    Уверенность: {material.confidence:.2f}")
        print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_material_analysis_agent())