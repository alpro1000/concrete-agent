# app/routers/tzd_router.py - TZD READER SYSTEM
"""
TZD Router для анализа технических заданий
Интегрирован с централизованной системой LLM через Orchestrator
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

# Интеграция с системами
try:
    from agents.tzd_reader.agent import tzd_reader
    from agents.tzd_reader.security import FileSecurityValidator, SecurityError
    TZD_AVAILABLE = True
except ImportError:
    TZD_AVAILABLE = False
    logger.warning("TZD Reader not available")

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ВАЖНО: Роутер должен называться именно 'router' для автоматического обнаружения
router = APIRouter(
    prefix="/api/v1/tzd",
    tags=["TZD Reader"],
    responses={404: {"description": "Not found"}}
)

# Pydantic модели согласно новому формату
class TZDAnalysisResponse(BaseModel):
    """Ответ анализа TZD в новом формате"""
    success: bool
    analysis_id: str
    timestamp: str
    project_object: str
    requirements: List[str]
    norms: List[str]
    constraints: List[str] 
    environment: str
    functions: List[str]
    processing_metadata: Dict[str, Any]
    error_message: Optional[str] = None

# Кеш результатов
analysis_cache = {}
analysis_counter = 0

@router.post("/analyze", response_model=TZDAnalysisResponse)
async def analyze_tzd_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Файлы ТЗ для анализа (PDF, DOCX, TXT)"),
    ai_engine: str = Form(default="auto", description="AI движок: gpt, claude, auto"),
    project_context: Optional[str] = Form(None, description="Контекст проекта")
):
    """
    🎯 **Анализ технических документов с помощью TZD Reader**
    
    **Безопасность:**
    - Максимальный размер файла: 10MB
    - Допустимые форматы: .pdf, .docx, .txt
    - Защита от path traversal
    
    **Возможности:**
    - 📄 Анализ PDF, DOCX, TXT файлов
    - 🏗️ Извлечение требований ТЗ
    - 🤖 Интеграция с LLM через Orchestrator (Claude, GPT, Perplexity)
    - 📊 Структурированный JSON ответ
    
    **Пример использования:**
    ```bash
    curl -X POST "/api/v1/tzd/analyze" \\
         -F "files=@document.pdf" \\
         -F "ai_engine=auto"
    ```
    """
    
    # Проверка доступности TZD модуля
    if not TZD_AVAILABLE:
        return TZDAnalysisResponse(
            success=False,
            analysis_id="error_no_tzd",
            timestamp=datetime.now().isoformat(),
            project_object="Ошибка конфигурации",
            requirements=["Модуль TZD Reader не установлен"],
            norms=[],
            constraints=["Система работает в ограниченном режиме"],
            environment="Демо режим",
            functions=[],
            processing_metadata={"demo_mode": True},
            error_message="TZD Reader не установлен. Проверьте конфигурацию модуля agents/tzd_reader/"
        )
    
    global analysis_counter
    analysis_counter += 1
    analysis_id = f"tzd_{analysis_counter}_{datetime.now().strftime('%H%M%S')}"
    
    # Создаем безопасную временную папку
    temp_dir = tempfile.mkdtemp(prefix="tzd_secure_")
    file_paths = []
    
    try:
        # Валидация безопасности и сохранение файлов
        validator = FileSecurityValidator()
        
        for file in files:
            if not file.filename:
                continue
                
            # Проверка расширения
            try:
                validator.validate_file_extension(file.filename)
            except SecurityError as e:
                raise HTTPException(status_code=400, detail=f"Недопустимое расширение файла: {str(e)}")
            
            # Сохранение файла с безопасной проверкой размера
            safe_filename = Path(file.filename).name  # Защита от path traversal
            file_path = os.path.join(temp_dir, safe_filename)
            
            content = await file.read()
            
            # Проверка размера
            if len(content) > 10 * 1024 * 1024:  # 10MB
                raise HTTPException(status_code=400, detail=f"Файл {safe_filename} превышает лимит 10MB")
            
            with open(file_path, "wb") as f:
                f.write(content)
            file_paths.append(file_path)
        
        if not file_paths:
            raise HTTPException(status_code=400, detail="Нет файлов для анализа")
        
        # Анализ с TZD Reader через централизованную систему
        logger.info(f"Starting TZD analysis with {len(file_paths)} files using engine: {ai_engine}")
        
        result = tzd_reader(
            files=file_paths,
            engine=ai_engine,
            base_dir=temp_dir
        )
        
        # Добавляем метаданные согласно спецификации
        result['analysis_id'] = analysis_id
        result['timestamp'] = datetime.now().isoformat()
        result['llm_orchestrator_used'] = True
        
        # Кеширование результата
        analysis_cache[analysis_id] = result
        
        # Фоновая очистка временных файлов
        background_tasks.add_task(cleanup_temp_files, temp_dir)
        
        return TZDAnalysisResponse(
            success=True,
            analysis_id=analysis_id,
            timestamp=result['timestamp'],
            project_object=result.get('project_object', ''),
            requirements=result.get('requirements', []),
            norms=result.get('norms', []),
            constraints=result.get('constraints', []),
            environment=result.get('environment', ''),
            functions=result.get('functions', []),
            processing_metadata=result.get('processing_metadata', {})
        )
        
    except SecurityError as e:
        cleanup_temp_files(temp_dir)
        logger.error(f"Security error in TZD analysis: {e}")
        raise HTTPException(status_code=400, detail=f"Нарушение безопасности: {str(e)}")
    except Exception as e:
        cleanup_temp_files(temp_dir)
        logger.error(f"TZD analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@router.get("/health")
async def tzd_health():
    """🏥 Проверка состояния TZD системы"""
    return {
        "service": "TZD Reader",
        "status": "healthy" if TZD_AVAILABLE else "limited",
        "tzd_reader_available": TZD_AVAILABLE,
        "cached_analyses": len(analysis_cache),
        "timestamp": datetime.now().isoformat(),
        "security": {
            "max_file_size": "10MB",
            "allowed_extensions": [".pdf", ".docx", ".txt"],
            "path_traversal_protection": True
        },
        "supported_formats": ["PDF", "DOCX", "TXT"],
        "ai_engines": ["gpt", "claude", "auto"],
        "orchestrator_integration": True
    }

@router.get("/analysis/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """📋 Получить результат анализа по ID"""
    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    return JSONResponse(content=analysis_cache[analysis_id])

async def cleanup_temp_files(temp_dir: str):
    """🧹 Безопасная очистка временных файлов"""
    try:
        import shutil
        if os.path.exists(temp_dir) and temp_dir.startswith('/tmp/'):
            shutil.rmtree(temp_dir)
            logger.info(f"🗑️ Очищены временные файлы: {temp_dir}")
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")
