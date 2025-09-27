# app/routers/tzd_router.py - ВАШ TZD ROUTER ПО НОВОЙ СИСТЕМЕ
"""
TZD Router для автоматической регистрации
Система найдет этот роутер автоматически!
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import tempfile
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Интеграция с существующими системами
try:
    from agents.concrete_agent import ConcreteAgent
    CONCRETE_AGENT_AVAILABLE = True
except ImportError:
    CONCRETE_AGENT_AVAILABLE = False

try:
    from agents.tzd_reader.agent import tzd_reader
    TZD_AVAILABLE = True
except ImportError:
    TZD_AVAILABLE = False

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ВАЖНО: Роутер должен называться именно 'router' для автоматического обнаружения
router = APIRouter(
    prefix="/api/v1/tzd",
    tags=["TZD Reader"],
    responses={404: {"description": "Not found"}}
)

# Pydantic модели
class TZDAnalysisResponse(BaseModel):
    """Ответ анализа TZD"""
    success: bool
    analysis_id: str
    timestamp: str
    project_name: str
    project_scope: str
    materials: List[str]
    concrete_requirements: List[str]
    norms: List[str]
    functional_requirements: List[str]
    risks_and_constraints: List[str]
    estimated_complexity: str
    key_technologies: List[str]
    processing_metadata: Dict[str, Any]
    project_summary: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

# Кеш результатов
analysis_cache = {}
analysis_counter = 0

@router.post("/analyze", response_model=TZDAnalysisResponse)
async def analyze_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Файлы для анализа (PDF, DOCX, TXT)"),
    ai_engine: str = Form(default="gpt", description="AI движок: gpt или claude"),
    analysis_depth: str = Form(default="standard", description="Глубина: basic, standard, detailed"),
    focus_areas: str = Form(default="", description="Области фокуса через запятую"),
    project_context: Optional[str] = Form(None, description="Контекст проекта")
):
    """
    🎯 **Анализ технических документов с помощью TZD Reader**
    
    **Автоматически найден системой регистрации роутеров!**
    
    **Возможности:**
    - 📄 Анализ PDF, DOCX, TXT файлов
    - 🏗️ Поддержка чешских стандартов ČSN EN 206+A2
    - 🤖 Интеграция с AI агентами системы
    - 📊 Различные уровни детализации анализа
    
    **Области фокуса:**
    - `concrete`: анализ бетонных конструкций
    - `materials`: спецификация материалов
    - `norms`: соответствие стандартам
    - `costs`: анализ стоимости
    - `safety`: требования безопасности
    
    **Примеры использования:**
    ```bash
    curl -X POST "/api/v1/tzd/analyze" \\
         -F "files=@document.pdf" \\
         -F "ai_engine=gpt" \\
         -F "analysis_depth=detailed" \\
         -F "focus_areas=concrete,norms"
    ```
    """
    
    # Демо режим если TZD недоступен
    if not TZD_AVAILABLE:
        return TZDAnalysisResponse(
            success=False,
            analysis_id="demo_mode",
            timestamp=datetime.now().isoformat(),
            project_name="Demo Mode - TZD Reader",
            project_scope="TZD Reader не установлен",
            materials=[],
            concrete_requirements=[],
            norms=["ČSN EN 206+A2", "ČSN EN 10025", "ČSN 73 0540"],
            functional_requirements=["Установите модуль tzd_reader"],
            risks_and_constraints=["Система работает в демо режиме"],
            estimated_complexity="demo",
            key_technologies=["FastAPI", "Auto Router Discovery"],
            processing_metadata={"demo_mode": True},
            project_summary={},
            error_message="TZD Reader не установлен. Установите модуль agents/tzd_reader/agent.py"
        )
    
    global analysis_counter
    analysis_counter += 1
    analysis_id = f"tzd_{analysis_counter}_{datetime.now().strftime('%H%M%S')}"
    
    # Создаем временную папку
    temp_dir = tempfile.mkdtemp(prefix="tzd_")
    file_paths = []
    
    try:
        # Сохраняем загруженные файлы
        for file in files:
            if file.filename:
                path = os.path.join(temp_dir, file.filename)
                content = await file.read()
                with open(path, "wb") as f:
                    f.write(content)
                file_paths.append(path)
        
        if not file_paths:
            raise HTTPException(status_code=400, detail="Нет файлов для анализа")
        
        # Парсим области фокуса
        focus_list = [area.strip() for area in focus_areas.split(",") if area.strip()] if focus_areas else []
        
        # Анализ с TZD Reader
        result = tzd_reader(
            files=file_paths,
            engine=ai_engine,
            base_dir=temp_dir
        )
        
        # Интеграция с Concrete Agent если доступен
        if CONCRETE_AGENT_AVAILABLE and "concrete" in focus_list:
            try:
                concrete_agent = ConcreteAgent()
                concrete_analysis = concrete_agent.analyze_concrete_requirements(
                    result.get('concrete_requirements', [])
                )
                result['concrete_analysis'] = concrete_analysis
                logger.info("✅ Concrete Agent интегрирован")
            except Exception as e:
                logger.warning(f"⚠️ Concrete Agent error: {e}")
        
        # Добавляем метаданные
        result['analysis_id'] = analysis_id
        result['timestamp'] = datetime.now().isoformat()
        result['auto_discovered'] = True  # Маркер автоматической регистрации
        
        # Кеширование
        analysis_cache[analysis_id] = result
        
        # Фоновая очистка
        background_tasks.add_task(cleanup_temp_files, temp_dir)
        
        return TZDAnalysisResponse(
            success=True,
            analysis_id=analysis_id,
            timestamp=result['timestamp'],
            project_name=result.get('project_name', ''),
            project_scope=result.get('project_scope', ''),
            materials=result.get('materials', []),
            concrete_requirements=result.get('concrete_requirements', []),
            norms=result.get('norms', []),
            functional_requirements=result.get('functional_requirements', []),
            risks_and_constraints=result.get('risks_and_constraints', []),
            estimated_complexity=result.get('estimated_complexity', 'неопределена'),
            key_technologies=result.get('key_technologies', []),
            processing_metadata=result.get('processing_metadata', {}),
            project_summary=result.get('project_summary', {})
        )
        
    except Exception as e:
        cleanup_temp_files(temp_dir)
        logger.error(f"TZD analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def tzd_health():
    """🏥 Проверка состояния TZD системы"""
    return {
        "service": "TZD Reader",
        "status": "healthy" if TZD_AVAILABLE else "limited",
        "auto_discovered": True,
        "tzd_reader": TZD_AVAILABLE,
        "concrete_integration": CONCRETE_AGENT_AVAILABLE,
        "cached_analyses": len(analysis_cache),
        "timestamp": datetime.now().isoformat(),
        "supported_formats": ["PDF", "DOCX", "TXT"],
        "ai_engines": ["gpt", "claude"],
        "czech_standards": ["ČSN EN 206+A2", "ČSN EN 10025", "ČSN 73 0540"]
    }

@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """📋 Получить результат анализа по ID"""
    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    return JSONResponse(content=analysis_cache[analysis_id])

@router.get("/capabilities")
async def get_capabilities():
    """🔍 Возможности TZD системы"""
    
    # Check MinerU availability
    mineru_enabled = os.getenv("MINERU_ENABLED", "false").lower() == "true"
    try:
        import mineru
        mineru_available = True
    except ImportError:
        mineru_available = False
    
    return {
        "document_analysis": {
            "formats": ["PDF", "DOCX", "TXT"],
            "max_file_size": "10MB",
            "max_files": 10,
            "languages": ["Czech", "English"],
            "mineru_integration": {
                "available": mineru_available,
                "enabled": mineru_enabled,
                "description": "Enhanced PDF text/structure extraction"
            }
        },
        "ai_analysis": {
            "engines": ["gpt-4", "claude-3.5"],
            "depths": ["basic", "standard", "detailed", "expert"],
            "focus_areas": ["concrete", "materials", "norms", "costs", "safety"]
        },
        "response_fields": {
            "standard_fields": [
                "project_name", "project_scope", "materials",
                "concrete_requirements", "norms", "functional_requirements",
                "risks_and_constraints", "estimated_complexity", "key_technologies"
            ],
            "enhanced_fields": {
                "project_summary": {
                    "description": "Structured project summary by sections",
                    "sections": ["overview", "scope", "concrete", "materials", "norms", "risks", "schedule", "costs", "deliverables"]
                },
                "processing_metadata": {
                    "description": "Processing statistics and configuration",
                    "includes": ["processed_files", "processing_time", "ai_engine", "mineru_used"]
                }
            }
        },
        "czech_standards": {
            "concrete": "ČSN EN 206+A2",
            "steel": "ČSN EN 10025", 
            "thermal": "ČSN 73 0540",
            "fire_safety": "ČSN 73 0802"
        },
        "integrations": {
            "concrete_agent": CONCRETE_AGENT_AVAILABLE,
            "auto_discovery": True,
            "export_formats": ["JSON", "Excel"]
        },
        "auto_registration": {
            "discovered_by": "RouterRegistry",
            "registration_time": "startup",
            "module_path": "app.routers.tzd_router"
        }
    }

async def cleanup_temp_files(temp_dir: str):
    """🧹 Очистка временных файлов"""
    try:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"🗑️ Очищены временные файлы: {temp_dir}")
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")
