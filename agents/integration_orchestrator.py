"""
Интеграционный оркестратор для автоматического анализа
agents/integration_orchestrator.py

Реализует основной сценарий:
1. ConcreteAgent -> анализ марок бетона
2. VolumeAgent -> анализ объемов на основе результатов ConcreteAgent
3. MaterialAgent -> поиск материалов по запросу пользователя
4. DrawingVolumeAgent -> анализ геометрии из чертежей (опционально)

Поддерживает fallback для безопасной работы без ошибок.
"""

import logging
import sys
import os
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# Import from the main concrete_agent.py file (not the package)
import importlib.util
spec = importlib.util.spec_from_file_location("concrete_agent_main", 
        os.path.join(os.path.dirname(__file__), 'concrete_agent.py'))
concrete_agent_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(concrete_agent_main)
analyze_concrete = concrete_agent_main.analyze_concrete
get_hybrid_agent = concrete_agent_main.get_hybrid_agent

from agents.volume_agent.agent import get_volume_analysis_agent
from agents.material_agent.agent import get_material_analysis_agent
from agents.drawing_volume_agent import get_drawing_volume_agent
from agents.tov_agent import get_tov_agent
from utils.czech_preprocessor import get_czech_preprocessor

logger = logging.getLogger(__name__)

@dataclass
class IntegratedAnalysisRequest:
    """Запрос на интегрированный анализ"""
    doc_paths: List[str]
    smeta_path: Optional[str] = None
    material_query: Optional[str] = None  # "арматура", "окна", "двери", etc.
    use_claude: bool = True
    claude_mode: str = "enhancement"
    language: str = "cz"
    include_drawing_analysis: bool = False

@dataclass
class IntegratedAnalysisResult:
    """Результат интегрированного анализа"""
    concrete_summary: Dict[str, Any]
    volume_summary: Dict[str, Any]
    material_summary: Dict[str, Any]
    drawing_summary: Optional[Dict[str, Any]] = None
    sources: List[str] = None
    analysis_status: Dict[str, str] = None
    success: bool = True
    error_message: Optional[str] = None

class IntegrationOrchestrator:
    """Главный оркестратор для интеграции всех агентов"""
    
    def __init__(self):
        # Инициализируем агентов
        try:
            self.concrete_agent = get_hybrid_agent()
            logger.info("✅ ConcreteAgent инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации ConcreteAgent: {e}")
            self.concrete_agent = None
        
        try:
            self.volume_agent = get_volume_analysis_agent()
            logger.info("✅ VolumeAgent инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации VolumeAgent: {e}")
            self.volume_agent = None
        
        try:
            self.material_agent = get_material_analysis_agent()
            logger.info("✅ MaterialAgent инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации MaterialAgent: {e}")
            self.material_agent = None
        
        try:
            self.drawing_agent = get_drawing_volume_agent()
            logger.info("✅ DrawingVolumeAgent инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации DrawingVolumeAgent: {e}")
            self.drawing_agent = None
        
        self.czech_preprocessor = get_czech_preprocessor()
        logger.info("🚀 IntegrationOrchestrator инициализирован")
    
    async def analyze_materials_integrated(self, request: IntegratedAnalysisRequest) -> IntegratedAnalysisResult:
        """
        Главная функция интегрированного анализа
        
        Выполняет последовательно:
        1. Анализ марок бетона (ConcreteAgent)
        2. Анализ объемов на основе марок (VolumeAgent)
        3. Поиск материалов по запросу (MaterialAgent)
        4. Опционально - анализ чертежей (DrawingVolumeAgent)
        """
        logger.info("🏗️ Запуск интегрированного анализа материалов")
        
        # Проверяем входные данные
        if not request.doc_paths:
            return IntegratedAnalysisResult(
                concrete_summary={},
                volume_summary={},
                material_summary={},
                success=False,
                error_message="Не указаны документы для анализа"
            )
        
        sources = request.doc_paths.copy()
        if request.smeta_path:
            sources.append(request.smeta_path)
        
        analysis_status = {}
        
        # ШАГ 1: Анализ марок бетона с помощью ConcreteAgent
        logger.info("📊 Шаг 1: Анализ марок бетона")
        concrete_summary = await self._analyze_concrete_grades(request, analysis_status)
        
        # ШАГ 2: Анализ объемов на основе найденных марок
        logger.info("📐 Шаг 2: Анализ объемов")
        volume_summary = await self._analyze_volumes(request, concrete_summary, analysis_status)
        
        # ШАГ 3: Поиск материалов по запросу пользователя
        logger.info("🔧 Шаг 3: Анализ материалов")
        material_summary = await self._analyze_materials(request, analysis_status)
        
        # ШАГ 4: Опциональный анализ чертежей
        drawing_summary = None
        if request.include_drawing_analysis:
            logger.info("📐 Шаг 4: Анализ чертежей")
            drawing_summary = await self._analyze_drawings(request, analysis_status)
        
        # Формируем итоговый результат
        result = IntegratedAnalysisResult(
            concrete_summary=concrete_summary,
            volume_summary=volume_summary,
            material_summary=material_summary,
            drawing_summary=drawing_summary,
            sources=sources,
            analysis_status=analysis_status,
            success=True
        )
        
        logger.info("✅ Интегрированный анализ завершен успешно")
        return result
    
    async def _analyze_concrete_grades(self, request: IntegratedAnalysisRequest, status: Dict[str, str]) -> Dict[str, Any]:
        """Анализ марок бетона"""
        if not self.concrete_agent:
            status["concrete_analysis"] = "unavailable - agent not initialized"
            return {
                "success": False,
                "error": "ConcreteAgent недоступен",
                "concrete_summary": [],
                "total_grades": 0
            }
        
        try:
            # Используем существующую функцию analyze_concrete
            result = await analyze_concrete(
                doc_paths=request.doc_paths,
                smeta_path=request.smeta_path,
                use_claude=request.use_claude,
                claude_mode=request.claude_mode
            )
            
            if result.get("success", False):
                status["concrete_analysis"] = "completed successfully"
                return result
            else:
                status["concrete_analysis"] = f"failed - {result.get('error', 'unknown error')}"
                return result
                
        except Exception as e:
            logger.error(f"❌ Ошибка анализа марок бетона: {e}")
            status["concrete_analysis"] = f"error - {str(e)}"
            return {
                "success": False,
                "error": str(e),
                "concrete_summary": [],
                "total_grades": 0
            }
    
    async def _analyze_volumes(self, request: IntegratedAnalysisRequest, 
                             concrete_result: Dict[str, Any], status: Dict[str, str]) -> Dict[str, Any]:
        """Анализ объемов на основе найденных марок бетона"""
        if not self.volume_agent:
            status["volume_analysis"] = "unavailable - agent not initialized"
            return {
                "success": False,
                "error": "VolumeAgent недоступен",
                "total_volume_m3": 0,
                "total_cost": 0,
                "volume_entries": []
            }
        
        try:
            # Проверяем наличие сметы
            if not request.smeta_path:
                status["volume_analysis"] = "skipped - no budget/smeta provided"
                return {
                    "success": False,
                    "error": "Расчет объемов невозможен - отсутствует смета",
                    "message": "Для расчета объемов необходим файл сметы или списка работ",
                    "concrete_grades_found": concrete_result.get("total_grades", 0),
                    "grades_locations": [grade.get("location", "") for grade in concrete_result.get("concrete_summary", [])],
                    "total_volume_m3": 0,
                    "total_cost": 0,
                    "volume_entries": []
                }
            
            # Анализируем объемы
            volumes = await self.volume_agent.analyze_volumes(
                doc_paths=request.doc_paths,
                smeta_path=request.smeta_path
            )
            
            # Создаем summary
            volume_summary = self.volume_agent.create_volume_summary(volumes)
            
            status["volume_analysis"] = "completed successfully"
            return {
                "success": True,
                "total_volume_m3": volume_summary.get("total_volume_m3", 0),
                "total_cost": volume_summary.get("total_cost", 0),
                "volume_entries": [asdict(v) for v in volumes],
                "elements_count": volume_summary.get("elements_count", 0),
                "avg_confidence": volume_summary.get("avg_confidence", 0.0)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа объемов: {e}")
            status["volume_analysis"] = f"error - {str(e)}"
            return {
                "success": False,
                "error": str(e),
                "total_volume_m3": 0,
                "total_cost": 0,
                "volume_entries": []
            }
    
    async def _analyze_materials(self, request: IntegratedAnalysisRequest, status: Dict[str, str]) -> Dict[str, Any]:
        """Универсальный поиск материалов по запросу пользователя"""
        if not self.material_agent:
            status["material_analysis"] = "unavailable - agent not initialized"
            return {
                "success": False,
                "error": "MaterialAgent недоступен",
                "materials": [],
                "categories": [],
                "total_materials": 0
            }
        
        try:
            # Анализируем материалы из всех источников
            materials = await self.material_agent.analyze_materials(
                doc_paths=request.doc_paths,
                smeta_path=request.smeta_path
            )
            
            # Фильтруем по запросу пользователя, если он указан
            if request.material_query:
                materials = self._filter_materials_by_query(materials, request.material_query)
                logger.info(f"🔍 Отфильтровано {len(materials)} материалов по запросу '{request.material_query}'")
            
            # Создаем summary и категории
            material_summary = self.material_agent.create_material_summary(materials)
            categories = self.material_agent.categorize_materials(materials)
            
            status["material_analysis"] = "completed successfully"
            return {
                "success": True,
                "query": request.material_query,
                "total_materials": len(materials),
                "materials": [asdict(m) for m in materials],
                "categories": [asdict(c) for c in categories],
                "summary": material_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа материалов: {e}")
            status["material_analysis"] = f"error - {str(e)}"
            return {
                "success": False,
                "error": str(e),
                "materials": [],
                "categories": [],
                "total_materials": 0
            }
    
    def _filter_materials_by_query(self, materials, query: str):
        """Фильтрует материалы по запросу пользователя"""
        if not query:
            return materials
        
        # Нормализуем запрос с помощью чешского препроцессора
        normalized_query = self.czech_preprocessor.normalize_text(query.lower())
        
        # Словарь синонимов (расширенный)
        query_synonyms = {
            "арматура": ["výztuž", "armatura", "железо", "арматурн", "fe500", "fe400", "r10", "r12", "r16", "r20"],
            "výztuž": ["арматура", "armatura", "железо", "арматурн", "fe500", "fe400", "r10", "r12", "r16", "r20"],
            "armatura": ["арматура", "výztuž", "железо", "арматурн", "fe500", "fe400"],
            "окна": ["okna", "окон", "zasklení", "остеклен", "pvc", "dřevo", "hliník"],
            "okna": ["окна", "окон", "zasklení", "остеклен", "pvc", "dřevo", "hliník"],
            "двери": ["dveře", "dvere", "дверн", "vchod", "vchodov"],
            "dveře": ["двери", "dvere", "дверн", "vchod", "vchodov"],
            "плитка": ["dlažba", "obklad", "keramick", "плитк"],
            "dlažba": ["плитка", "obklad", "keramick", "плитк"],
            "изоляция": ["izolace", "утеплен", "теплоизол", "isolation", "xps", "eps"],
            "izolace": ["изоляция", "утеплен", "теплоизол", "isolation", "xps", "eps"],
            "бетон": ["beton", "concrete", "цемент", "c25", "c30", "c35"],
            "beton": ["бетон", "concrete", "цемент", "c25", "c30", "c35"],
            "сталь": ["ocel", "steel", "металл", "железо", "ipe", "hea", "heb"],
            "ocel": ["сталь", "steel", "металл", "железо", "ipe", "hea", "heb"],
            "střešní": ["кровельн", "roof", "крыша", "tašk", "plechov"],
            "roof": ["střešní", "кровельн", "крыша", "tašk", "plechov"],
            "těsnění": ["уплотнен", "sealing", "герметик", "epdm", "pryž"],
            "sealing": ["těsnění", "уплотнен", "герметик", "epdm", "pryž"]
        }
        
        # Расширяем поиск синонимами
        search_terms = [normalized_query]
        
        # Добавляем прямые синонимы
        if normalized_query in query_synonyms:
            search_terms.extend([term.lower() for term in query_synonyms[normalized_query]])
        
        # Проверяем частичные совпадения для ключевых слов
        for key, synonyms in query_synonyms.items():
            if key in normalized_query or normalized_query in key:
                search_terms.extend([term.lower() for term in synonyms])
        
        # Убираем дубликаты
        search_terms = list(set(search_terms))
        
        logger.info(f"🔍 Поисковые термины для '{query}': {search_terms[:5]}...")  # показываем первые 5
        
        filtered_materials = []
        for material in materials:
            # Проверяем в названии, типе и спецификации
            material_text = f"{material.material_name} {material.material_type} {material.specification}".lower()
            material_text = self.czech_preprocessor.normalize_text(material_text)
            
            # Проверяем точные совпадения
            if any(term in material_text for term in search_terms):
                filtered_materials.append(material)
                continue
            
            # Проверяем в контексте
            context_text = material.context.lower()
            context_text = self.czech_preprocessor.normalize_text(context_text)
            if any(term in context_text for term in search_terms):
                filtered_materials.append(material)
        
        return filtered_materials
    
    async def _analyze_drawings(self, request: IntegratedAnalysisRequest, status: Dict[str, str]) -> Dict[str, Any]:
        """Анализ чертежей с использованием DrawingVolumeAgent"""
        if not self.drawing_agent:
            status["drawing_analysis"] = "unavailable - agent not initialized"
            return {
                "success": False,
                "error": "DrawingVolumeAgent недоступен",
                "message": "Анализ чертежей запланирован в следующих версиях",
                "total_drawings": 0,
                "total_volume_m3": 0.0,
                "drawings": []
            }
        
        try:
            # Фильтруем PDF файлы, которые могут быть чертежами
            drawing_paths = [path for path in request.doc_paths if path.lower().endswith('.pdf')]
            
            if not drawing_paths:
                status["drawing_analysis"] = "skipped - no PDF drawings found"
                return {
                    "success": True,
                    "message": "PDF чертежи не найдены",
                    "total_drawings": 0,
                    "total_volume_m3": 0.0,
                    "drawings": []
                }
            
            # Анализируем чертежи
            results = await self.drawing_agent.analyze_drawing_volumes(drawing_paths)
            summary = self.drawing_agent.create_drawing_summary(results)
            
            if summary["successful_analyses"] > 0:
                status["drawing_analysis"] = f"completed - {summary['successful_analyses']}/{summary['total_drawings']} successful"
            else:
                status["drawing_analysis"] = "completed - no successful analyses (external services unavailable)"
            
            return {
                "success": True,
                "total_drawings": summary["total_drawings"],
                "successful_analyses": summary["successful_analyses"],
                "total_volume_m3": summary["total_volume_m3"],
                "total_area_m2": summary["total_area_m2"],
                "analysis_methods": summary["analysis_methods"],
                "external_services": summary["external_services_status"],
                "drawings": summary["drawings"],
                "note": "Полный анализ чертежей требует подключения MinerU и DocStrange"
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа чертежей: {e}")
            status["drawing_analysis"] = f"error - {str(e)}"
            return {
                "success": False,
                "error": str(e),
                "total_drawings": 0,
                "total_volume_m3": 0.0,
                "drawings": []
            }
    
    async def run_integrated_analysis(self, request: IntegratedAnalysisRequest) -> Dict[str, Any]:
        """
        Backward compatibility method that wraps analyze_materials_integrated
        Returns dict instead of IntegratedAnalysisResult dataclass
        """
        try:
            # Call the main analysis method
            result = await self.analyze_materials_integrated(request)
            
            # Convert dataclass result to dict for backward compatibility
            return {
                "success": result.success,
                "summary": {
                    "concrete_grades": result.concrete_summary.get("total_grades", 0),
                    "total_volume_m3": result.volume_summary.get("total_volume_m3", 0),
                    "materials_found": result.material_summary.get("total_materials", 0),
                    "sources_processed": len(result.sources) if result.sources else 0
                },
                "concrete_analysis": result.concrete_summary,
                "volume_analysis": result.volume_summary,
                "materials_analysis": result.material_summary,
                "tzd_analysis": result.drawing_summary,  # For TZD/technical specification analysis
                "status": result.analysis_status,
                "timestamp": time.time(),
                "error_message": result.error_message
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка интегрированного анализа: {e}")
            return {
                "success": False,
                "error_message": str(e),
                "summary": {},
                "concrete_analysis": {},
                "volume_analysis": {},
                "materials_analysis": {},
                "tzd_analysis": {},
                "status": {"error": str(e)},
                "timestamp": time.time()
            }

# Singleton instance
_integration_orchestrator = None

def get_integration_orchestrator() -> IntegrationOrchestrator:
    """Получение глобального экземпляра оркестратора"""
    global _integration_orchestrator
    if _integration_orchestrator is None:
        _integration_orchestrator = IntegrationOrchestrator()
        logger.info("🚀 IntegrationOrchestrator initialized")
    return _integration_orchestrator