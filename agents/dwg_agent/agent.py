"""
Специализированный агент для работы с DWG/DXF файлами
agents/dwg_agent/agent.py

Отвечает только за:
1. Парсинг DWG и DXF файлов с помощью ezdxf
2. Извлечение текстовых аннотаций и размеров
3. Анализ слоев чертежа
4. Поиск марок бетона в технических блоках
5. Извлечение размеров и спецификаций
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    import ezdxf
    from ezdxf import recover
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False
    logging.warning("⚠️ ezdxf не установлен. DWG/DXF функциональность недоступна")

from utils.knowledge_base_service import get_knowledge_service
from utils.czech_preprocessor import get_czech_preprocessor

logger = logging.getLogger(__name__)

@dataclass
class DwgTextEntity:
    """Текстовая сущность из DWG"""
    text: str
    layer: str
    position: Tuple[float, float, float]  # x, y, z координаты
    height: float
    style: str
    entity_type: str  # TEXT, MTEXT, DIMENSION

@dataclass  
class DwgLayer:
    """Слой DWG файла"""
    name: str
    color: int
    linetype: str
    entities_count: int
    has_text: bool
    has_dimensions: bool

@dataclass
class ConcreteSpecification:
    """Спецификация бетона найденная в DWG"""
    grade: str
    layer: str
    position: Tuple[float, float, float]
    context: str
    confidence: float
    source_entity: str

@dataclass
class DimensionInfo:
    """Информация о размере"""
    value: float
    text: str
    layer: str
    position: Tuple[float, float, float]
    dimension_type: str  # LINEAR, ANGULAR, RADIAL

class DwgAnalysisAgent:
    """Специализированный агент для анализа DWG/DXF файлов"""
    
    def __init__(self):
        if not EZDXF_AVAILABLE:
            raise ImportError("ezdxf не установлен. Установите: pip install ezdxf")
        
        self.knowledge_service = get_knowledge_service()
        self.czech_preprocessor = get_czech_preprocessor()
        
        # Получаем допустимые марки бетона
        self.allowed_grades = set(self.knowledge_service.get_all_concrete_grades())
        
        logger.info("📐 DwgAnalysisAgent initialized")
        
        # Паттерны для поиска марок бетона в DWG текстах
        self.concrete_patterns = [
            r'(?i)\b(C\d{1,3}/\d{1,3})\b',
            r'(?i)\b(LC\d{1,3}/\d{1,3})\b', 
            r'(?i)\b(B\d{1,2})\b',
            r'(?i)(?:beton|бетон)\s+(C\d{1,3}/\d{1,3})',
            r'(?i)(?:beton|бетон)\s+(B\d{1,2})',
        ]
        
        # Слои, которые часто содержат спецификации
        self.specification_layers = [
            'TEXT', 'NOTES', 'SPECS', 'ANNOTATION',
            'POZNÁMKY', 'SPECIFIKACE', 'POPIS',
            '0'  # Слой по умолчанию
        ]
    
    async def analyze_dwg_file(self, file_path: str) -> Dict[str, Any]:
        """Анализирует DWG/DXF файл"""
        logger.info(f"📐 Начинаем анализ DWG файла: {file_path}")
        
        try:
            # Пытаемся открыть файл с восстановлением если нужно
            try:
                doc = ezdxf.readfile(file_path)
                recovered = False
            except ezdxf.DXFStructureError:
                logger.warning(f"⚠️ Поврежденный DXF, пытаемся восстановить: {file_path}")
                doc, auditor = recover.readfile(file_path)
                recovered = True
                logger.info(f"🔧 Файл восстановлен, ошибок: {len(auditor.errors)}")
            
            # Анализируем содержимое
            analysis_result = await self._analyze_document_content(doc, file_path, recovered)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа DWG файла {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    async def _analyze_document_content(self, doc, file_path: str, recovered: bool) -> Dict[str, Any]:
        """Анализирует содержимое документа"""
        
        # Извлекаем информацию о слоях
        layers = self._extract_layers_info(doc)
        
        # Извлекаем текстовые сущности
        text_entities = self._extract_text_entities(doc)
        
        # Извлекаем размеры
        dimensions = self._extract_dimensions(doc)
        
        # Ищем марки бетона
        concrete_specs = self._find_concrete_specifications(text_entities)
        
        # Создаем сводку
        summary = self._create_analysis_summary(
            layers, text_entities, dimensions, concrete_specs
        )
        
        return {
            'success': True,
            'file_path': file_path,
            'recovered': recovered,
            'dxf_version': doc.dxfversion,
            'layers': layers,
            'text_entities_count': len(text_entities),
            'dimensions_count': len(dimensions), 
            'concrete_specifications': concrete_specs,
            'summary': summary,
            'raw_text_entities': [entity.__dict__ for entity in text_entities[:10]]  # Первые 10 для примера
        }
    
    def _extract_layers_info(self, doc) -> List[DwgLayer]:
        """Извлекает информацию о слоях"""
        layers = []
        
        for layer in doc.layers:
            # Считаем сущности в слое
            entities_count = 0
            has_text = False
            has_dimensions = False
            
            for entity in doc.modelspace().query(f'*[layer=="{layer.dxf.name}"]'):
                entities_count += 1
                if entity.dxftype() in ['TEXT', 'MTEXT']:
                    has_text = True
                elif entity.dxftype().startswith('DIMENSION'):
                    has_dimensions = True
            
            dwg_layer = DwgLayer(
                name=layer.dxf.name,
                color=layer.dxf.color,
                linetype=layer.dxf.linetype,
                entities_count=entities_count,
                has_text=has_text,
                has_dimensions=has_dimensions
            )
            layers.append(dwg_layer)
        
        return layers
    
    def _extract_text_entities(self, doc) -> List[DwgTextEntity]:
        """Извлекает текстовые сущности"""
        text_entities = []
        
        # Извлекаем TEXT сущности
        for entity in doc.modelspace().query('TEXT'):
            if hasattr(entity.dxf, 'text') and entity.dxf.text:
                text_entity = DwgTextEntity(
                    text=entity.dxf.text,
                    layer=entity.dxf.layer,
                    position=(entity.dxf.insert.x, entity.dxf.insert.y, entity.dxf.insert.z),
                    height=entity.dxf.height,
                    style=getattr(entity.dxf, 'style', ''),
                    entity_type='TEXT'
                )
                text_entities.append(text_entity)
        
        # Извлекаем MTEXT сущности
        for entity in doc.modelspace().query('MTEXT'):
            if hasattr(entity, 'text') and entity.text:
                text_entity = DwgTextEntity(
                    text=entity.text,
                    layer=entity.dxf.layer,
                    position=(entity.dxf.insert.x, entity.dxf.insert.y, entity.dxf.insert.z),
                    height=entity.dxf.char_height,
                    style=getattr(entity.dxf, 'style', ''),
                    entity_type='MTEXT'
                )
                text_entities.append(text_entity)
        
        return text_entities
    
    def _extract_dimensions(self, doc) -> List[DimensionInfo]:
        """Извлекает размеры"""
        dimensions = []
        
        for entity in doc.modelspace().query('DIMENSION'):
            try:
                # Получаем текст размера
                dim_text = entity.get_text() if hasattr(entity, 'get_text') else ""
                
                # Пытаемся извлечь числовое значение
                import re
                numbers = re.findall(r'\d+(?:[.,]\d+)?', dim_text)
                value = float(numbers[0].replace(',', '.')) if numbers else 0.0
                
                dimension_info = DimensionInfo(
                    value=value,
                    text=dim_text,
                    layer=entity.dxf.layer,
                    position=(0, 0, 0),  # Размеры имеют сложную геометрию
                    dimension_type=entity.dxftype()
                )
                dimensions.append(dimension_info)
                
            except Exception as e:
                logger.debug(f"Ошибка обработки размера: {e}")
                continue
        
        return dimensions
    
    def _find_concrete_specifications(self, text_entities: List[DwgTextEntity]) -> List[ConcreteSpecification]:
        """Находит спецификации бетона в текстовых сущностях"""
        concrete_specs = []
        
        for entity in text_entities:
            text = entity.text.strip()
            if not text or len(text) < 3:
                continue
            
            # Ищем марки бетона в тексте
            for pattern in self.concrete_patterns:
                import re
                matches = re.finditer(pattern, text)
                for match in matches:
                    grade = match.group(1) if match.groups() else match.group(0)
                    grade = grade.upper().strip()
                    
                    # Проверяем валидность марки
                    if self._is_valid_concrete_grade(grade):
                        concrete_spec = ConcreteSpecification(
                            grade=grade,
                            layer=entity.layer,
                            position=entity.position,
                            context=text,
                            confidence=self._calculate_dwg_confidence(grade, text, entity.layer),
                            source_entity=entity.entity_type
                        )
                        concrete_specs.append(concrete_spec)
        
        return concrete_specs
    
    def _is_valid_concrete_grade(self, grade: str) -> bool:
        """Проверяет валидность марки бетона"""
        return grade in self.allowed_grades or self.knowledge_service.is_valid_concrete_grade(grade)
    
    def _calculate_dwg_confidence(self, grade: str, text: str, layer: str) -> float:
        """Вычисляет уверенность для марки найденной в DWG"""
        confidence = 0.7  # Базовая уверенность для DWG
        
        # Повышаем за валидную марку в базе знаний
        if grade in self.allowed_grades:
            confidence += 0.2
        
        # Повышаем за специализированный слой
        if layer.upper() in [l.upper() for l in self.specification_layers]:
            confidence += 0.1
        
        # Повышаем за контекстные слова
        context_words = ['beton', 'железобетон', 'monolitick', 'konstrukce']
        text_lower = text.lower()
        if any(word in text_lower for word in context_words):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _create_analysis_summary(self, layers: List[DwgLayer], 
                               text_entities: List[DwgTextEntity],
                               dimensions: List[DimensionInfo],
                               concrete_specs: List[ConcreteSpecification]) -> Dict[str, Any]:
        """Создает сводку анализа"""
        
        # Статистика по слоям
        layers_with_text = [l for l in layers if l.has_text]
        layers_with_dimensions = [l for l in layers if l.has_dimensions]
        
        # Статистика по маркам бетона
        unique_grades = list(set(spec.grade for spec in concrete_specs))
        grades_by_layer = {}
        for spec in concrete_specs:
            layer = spec.layer
            if layer not in grades_by_layer:
                grades_by_layer[layer] = []
            grades_by_layer[layer].append(spec.grade)
        
        # Очистка дубликатов в слоях
        for layer in grades_by_layer:
            grades_by_layer[layer] = list(set(grades_by_layer[layer]))
        
        return {
            'layers_summary': {
                'total_layers': len(layers),
                'layers_with_text': len(layers_with_text),
                'layers_with_dimensions': len(layers_with_dimensions),
                'text_layers_names': [l.name for l in layers_with_text]
            },
            'content_summary': {
                'total_text_entities': len(text_entities),
                'total_dimensions': len(dimensions),
                'concrete_specifications_found': len(concrete_specs),
                'unique_concrete_grades': len(unique_grades)
            },
            'concrete_analysis': {
                'grades_found': unique_grades,
                'grades_by_layer': grades_by_layer,
                'highest_confidence': max([s.confidence for s in concrete_specs]) if concrete_specs else 0
            }
        }
    
    async def analyze_multiple_dwg_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Анализирует несколько DWG файлов"""
        logger.info(f"📐 Начинаем анализ {len(file_paths)} DWG файлов")
        
        results = {}
        all_concrete_specs = []
        
        for file_path in file_paths:
            try:
                result = await self.analyze_dwg_file(file_path)
                results[file_path] = result
                
                if result.get('success') and result.get('concrete_specifications'):
                    all_concrete_specs.extend(result['concrete_specifications'])
                    
            except Exception as e:
                logger.error(f"❌ Ошибка анализа {file_path}: {e}")
                results[file_path] = {
                    'success': False,
                    'error': str(e),
                    'file_path': file_path
                }
        
        # Создаем общую сводку
        overall_summary = self._create_overall_summary(results, all_concrete_specs)
        
        return {
            'files_analyzed': len(file_paths),
            'successful_analyses': sum(1 for r in results.values() if r.get('success')),
            'failed_analyses': sum(1 for r in results.values() if not r.get('success')),
            'results_by_file': results,
            'overall_summary': overall_summary
        }
    
    def _create_overall_summary(self, results: Dict[str, Any], 
                              all_concrete_specs: List[ConcreteSpecification]) -> Dict[str, Any]:
        """Создает общую сводку по всем файлам"""
        
        successful_results = [r for r in results.values() if r.get('success')]
        
        # Статистика по контенту
        total_text_entities = sum(r.get('text_entities_count', 0) for r in successful_results)
        total_dimensions = sum(r.get('dimensions_count', 0) for r in successful_results)
        
        # Уникальные марки бетона по всем файлам
        all_grades = list(set(spec.grade for spec in all_concrete_specs))
        
        # Марки по файлам
        grades_by_file = {}
        for file_path, result in results.items():
            if result.get('success') and result.get('concrete_specifications'):
                grades = [spec.grade for spec in result['concrete_specifications']]
                grades_by_file[file_path] = list(set(grades))
        
        return {
            'content_statistics': {
                'total_text_entities': total_text_entities,
                'total_dimensions': total_dimensions,
                'total_concrete_specs': len(all_concrete_specs)
            },
            'concrete_analysis': {
                'unique_grades_found': all_grades,
                'total_unique_grades': len(all_grades),
                'grades_by_file': grades_by_file,
                'files_with_concrete_specs': len([f for f in grades_by_file if grades_by_file[f]])
            }
        }


# Singleton instance
_dwg_analysis_agent = None

def get_dwg_analysis_agent() -> DwgAnalysisAgent:
    """Получение глобального экземпляра агента анализа DWG"""
    global _dwg_analysis_agent
    if _dwg_analysis_agent is None:
        if not EZDXF_AVAILABLE:
            raise ImportError("ezdxf не установлен. Установите: pip install ezdxf")
        _dwg_analysis_agent = DwgAnalysisAgent()
        logger.info("📐 DwgAnalysisAgent initialized")
    return _dwg_analysis_agent


# ==============================
# 🧪 Функция для тестирования
# ==============================

async def test_dwg_analysis_agent():
    """Тестирование агента анализа DWG"""
    if not EZDXF_AVAILABLE:
        print("❌ EZDXF не установлен, тестирование невозможно")
        return
    
    print("🧪 TESTING DWG ANALYSIS AGENT")
    print("=" * 50)
    
    # Создаем простой тестовый DXF файл
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Добавляем текст с маркой бетона
    msp.add_text("Beton C25/30 XC2", dxfattribs={'layer': 'SPECS'})
    msp.add_text("Železobetonová konstrukce C30/37", dxfattribs={'layer': 'NOTES'})
    
    # Сохраняем временный файл
    test_file = "/tmp/test_dwg.dxf"
    doc.saveas(test_file)
    
    try:
        agent = get_dwg_analysis_agent()
        result = await agent.analyze_dwg_file(test_file)
        
        print(f"📐 Успех анализа: {result.get('success')}")
        print(f"📄 DXF версия: {result.get('dxf_version')}")
        print(f"📊 Слоев: {len(result.get('layers', []))}")
        print(f"📝 Текстовых сущностей: {result.get('text_entities_count')}")
        print(f"🎯 Найдено марок бетона: {len(result.get('concrete_specifications', []))}")
        
        if result.get('concrete_specifications'):
            print("\n🔍 Найденные марки:")
            for spec in result['concrete_specifications']:
                print(f"  • {spec.grade} (слой: {spec.layer}, уверенность: {spec.confidence:.2f})")
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
    finally:
        # Удаляем тестовый файл
        import os
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_dwg_analysis_agent())