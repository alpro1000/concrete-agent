"""
FastAPI Router для Technical Assignment Reader (TZD Reader)
Интеграция безопасного анализатора технических заданий
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import tempfile
import os
import json
import logging
from pathlib import Path
import asyncio
from datetime import datetime

# Импорт безопасного TZD Reader
try:
    from agents.tzd_reader_secure import tzd_reader, SecurityError
except ImportError:
    try:
        from agents.tzd_reader_script import tzd_reader
        SecurityError = Exception
    except ImportError:
        tzd_reader = None
        SecurityError = Exception

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Создаем роутер
router = APIRouter(prefix="/api/tzd", tags=["TZD Reader"])


# Pydantic модели
class TZDAnalysisRequest(BaseModel):
    """Запрос на анализ технического задания"""
    ai_engine: str = Field(default="gpt", description="AI движок: gpt или claude")
    project_context: Optional[str] = Field(None, description="Контекст проекта")
    analysis_depth: str = Field(default="standard", description="Глубина анализа: basic, standard, detailed")
    focus_areas: List[str] = Field(default_factory=list, description="Области фокуса анализа")


class TZDAnalysisResponse(BaseModel):
    """Ответ анализа технического задания"""
    success: bool
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
    analysis_id: str
    timestamp: str
    error_message: Optional[str] = None


class TZDPromptManager:
    """Менеджер промптов для различных типов анализа"""
    
    @staticmethod
    def get_basic_prompt() -> str:
        return """Выполни базовый анализ технического задания. Верни результат в JSON формате:

{
  "project_name": "название проекта",
  "project_scope": "краткое описание работ",
  "materials": ["основные материалы"],
  "concrete_requirements": ["требования к бетону"],
  "norms": ["упомянутые стандарты"],
  "functional_requirements": ["ключевые требования"],
  "risks_and_constraints": ["основные риски"],
  "estimated_complexity": "низкая|средняя|высокая",
  "key_technologies": ["применяемые технологии"]
}

Текст документа:
"""

    @staticmethod
    def get_standard_prompt() -> str:
        return """Проанализируй техническое задание с учетом чешских строительных стандартов. 
Верни подробный анализ в JSON формате:

{
  "project_name": "полное название проекта",
  "project_scope": "детальное описание объема работ",
  "materials": ["все упомянутые материалы с характеристиками"],
  "concrete_requirements": ["требования к бетону по ČSN EN 206"],
  "norms": ["все нормативные документы ČSN, EN, ISO"],
  "functional_requirements": ["функциональные и технические требования"],
  "risks_and_constraints": ["технические риски и ограничения"],
  "estimated_complexity": "оценка сложности проекта",
  "key_technologies": ["ключевые технологии и методы"],
  "quality_requirements": ["требования к качеству"],
  "safety_requirements": ["требования безопасности"],
  "environmental_considerations": ["экологические требования"],
  "timeline_indicators": ["индикаторы временных рамок"]
}

Особое внимание уделяй:
- Соответствию чешским стандартам (ČSN EN 206+A2 для бетона)
- Классификации материалов по европейским нормам
- Требованиям к прочности и долговечности конструкций
- Климатическим условиям Чехии

Текст технического задания:
"""

    @staticmethod
    def get_detailed_prompt() -> str:
        return """Выполни экспертный анализ технического задания для строительного проекта в Чехии.
Проанализируй документ с точки зрения опытного инженера-строителя и сметчика.

Верни максимально подробный анализ в JSON:

{
  "project_name": "полное официальное название проекта",
  "project_scope": "подробное техническое описание всех видов работ",
  "materials": ["полный перечень материалов с техническими характеристиками"],
  "concrete_requirements": ["детальные требования к бетону по ČSN EN 206+A2"],
  "norms": ["все применимые нормы ČSN, EN, ISO с номерами разделов"],
  "functional_requirements": ["функциональные требования по категориям"],
  "risks_and_constraints": ["технические, финансовые и временные риски"],
  "estimated_complexity": "детальная оценка сложности с обоснованием",
  "key_technologies": ["технологии с описанием применения"],
  "quality_requirements": ["требования к качеству по стандартам"],
  "safety_requirements": ["требования безопасности и охраны труда"],
  "environmental_considerations": ["экологические ограничения и требования"],
  "timeline_indicators": ["временные рамки и критические этапы"],
  "cost_indicators": ["индикаторы стоимости и ценообразования"],
  "resource_requirements": ["потребности в ресурсах и оборудовании"],
  "regulatory_compliance": ["соответствие законодательству ЧР"],
  "technical_specifications": ["подробные технические спецификации"],
  "construction_methods": ["рекомендуемые методы строительства"],
  "testing_requirements": ["требования к испытаниям и контролю"],
  "maintenance_considerations": ["требования к эксплуатации и обслуживанию"]
}

Критерии экспертного анализа:
1. Соответствие Building Act (Zákon o stavebním řádu)
2. Требования к энергоэффективности по ČSN 73 0540
3. Классификация конструкций по Eurocodes
4. Требования к противопожарной безопасности
5. Экологические стандарты EU
6. Требования к доступности для инвалидов
7. Сейсмическая безопасность (если применимо)
8. Гидроизоляция и теплоизоляция
9. Вентиляция и кондиционирование
10. Инженерные системы и коммуникации

Текст технического задания:
"""

    @classmethod
    def get_focused_prompt(cls, focus_areas: List[str]) -> str:
        """Генерирует промпт с фокусом на определенных областях"""
        base_prompt = cls.get_standard_prompt()
        
        if focus_areas:
            focus_text = "\n\nОСОБЫЙ ФОКУС на следующих областях:\n"
            for area in focus_areas:
                if area == "concrete":
                    focus_text += "- БЕТОН: подробно проанализируй все требования к бетону, марки, классы воздействия по ČSN EN 206\n"
                elif area == "norms":
                    focus_text += "- НОРМЫ: найди все упомянутые стандарты ČSN, EN, ISO с точными номерами\n"
                elif area == "costs":
                    focus_text += "- СТОИМОСТЬ: выяви все индикаторы стоимости, объемы работ, ресурсы\n"
                elif area == "timeline":
                    focus_text += "- СРОКИ: определи временные рамки, этапы, критический путь\n"
                elif area == "safety":
                    focus_text += "- БЕЗОПАСНОСТЬ: проанализируй требования охраны труда и безопасности\n"
                elif area == "materials":
                    focus_text += "- МАТЕРИАЛЫ: детально опиши все материалы с техническими характеристиками\n"
            
            base_prompt = base_prompt.replace("Текст технического задания:", focus_text + "\nТекст технического задания:")
        
        return base_prompt


# Глобальные переменные для кеширования результатов
analysis_cache = {}
analysis_counter = 0


@router.post("/analyze", response_model=TZDAnalysisResponse)
async def analyze_technical_assignment(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Файлы технического задания (PDF, DOCX, TXT)"),
    ai_engine: str = Form(default="gpt", description="AI движок: gpt или claude"),
    analysis_depth: str = Form(default="standard", description="Глубина анализа: basic, standard, detailed"),
    focus_areas: str = Form(default="", description="Области фокуса через запятую"),
    project_context: Optional[str] = Form(None, description="Дополнительный контекст проекта")
):
    """
    Анализирует техническое задание с помощью AI
    
    - **files**: Файлы документов (поддерживаются PDF, DOCX, TXT)
    - **ai_engine**: Выбор AI движка (gpt или claude)
    - **analysis_depth**: Глубина анализа (basic/standard/detailed)
    - **focus_areas**: Специальные области фокуса (concrete,norms,costs,timeline,safety,materials)
    - **project_context**: Дополнительная информация о проекте
    """
    global analysis_counter
    analysis_counter += 1
    analysis_id = f"tzd_analysis_{analysis_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if not tzd_reader:
        raise HTTPException(
            status_code=500,
            detail="TZD Reader не доступен. Проверьте установку модуля agents.tzd_reader_secure"
        )
    
    # Валидация параметров
    if ai_engine not in ["gpt", "claude"]:
        raise HTTPException(status_code=400, detail="AI движок должен быть 'gpt' или 'claude'")
    
    if analysis_depth not in ["basic", "standard", "detailed"]:
        raise HTTPException(status_code=400, detail="Глубина анализа должна быть 'basic', 'standard' или 'detailed'")
    
    # Проверка файлов
    if not files:
        raise HTTPException(status_code=400, detail="Необходимо загрузить хотя бы один файл")
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Максимальное количество файлов: 10")
    
    # Создаем временную директорию
    temp_dir = tempfile.mkdtemp(prefix="tzd_analysis_")
    file_paths = []
    
    try:
        # Сохраняем загруженные файлы
        for file in files:
            if not file.filename:
                continue
                
            # Проверяем расширение
            allowed_extensions = {'.pdf', '.docx', '.txt'}
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Неподдерживаемый тип файла: {file_ext}. Разрешены: {', '.join(allowed_extensions)}"
                )
            
            # Сохраняем файл
            temp_file_path = os.path.join(temp_dir, file.filename)
            with open(temp_file_path, "wb") as temp_file:
                content = await file.read()
                temp_file.write(content)
            
            file_paths.append(temp_file_path)
            logger.info(f"Сохранен файл: {file.filename} ({len(content)} bytes)")
        
        if not file_paths:
            raise HTTPException(status_code=400, detail="Не удалось обработать ни один файл")
        
        # Подготавливаем параметры анализа
        focus_list = [area.strip() for area in focus_areas.split(",") if area.strip()] if focus_areas else []
        
        # Кастомизируем промпт в зависимости от настроек
        logger.info(f"Запуск анализа: движок={ai_engine}, глубина={analysis_depth}, фокус={focus_list}")
        
        # Выполняем анализ
        try:
            result = tzd_reader(
                files=file_paths,
                engine=ai_engine,
                base_dir=temp_dir
            )
        except SecurityError as e:
            logger.error(f"Ошибка безопасности при анализе: {e}")
            raise HTTPException(status_code=400, detail=f"Ошибка безопасности: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка анализа TZD: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")
        
        # Добавляем метаданные запроса
        result['analysis_id'] = analysis_id
        result['timestamp'] = datetime.now().isoformat()
        result['request_parameters'] = {
            'ai_engine': ai_engine,
            'analysis_depth': analysis_depth,
            'focus_areas': focus_list,
            'files_count': len(file_paths),
            'project_context': project_context
        }
        
        # Кешируем результат
        analysis_cache[analysis_id] = result
        
        # Добавляем фоновую задачу для очистки
        background_tasks.add_task(cleanup_temp_files, temp_dir, analysis_id)
        
        # Формируем ответ
        response = TZDAnalysisResponse(
            success=True,
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
            analysis_id=analysis_id,
            timestamp=result['timestamp']
        )
        
        logger.info(f"Анализ {analysis_id} завершен успешно")
        return response
        
    except HTTPException:
        # Очищаем временные файлы при ошибках HTTP
        cleanup_temp_files(temp_dir, analysis_id)
        raise
    except Exception as e:
        # Очищаем временные файлы при других ошибках
        cleanup_temp_files(temp_dir, analysis_id)
        logger.error(f"Неожиданная ошибка в анализе {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@router.get("/analysis/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """Получить результат анализа по ID"""
    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Результат анализа не найден")
    
    return JSONResponse(content=analysis_cache[analysis_id])


@router.get("/health")
async def health_check():
    """Проверка состояния TZD Reader сервиса"""
    status = {
        "service": "TZD Reader API",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tzd_reader_available": tzd_reader is not None,
        "cached_analyses": len(analysis_cache),
        "supported_formats": [".pdf", ".docx", ".txt"],
        "ai_engines": ["gpt", "claude"],
        "analysis_depths": ["basic", "standard", "detailed"]
    }
    
    # Проверяем доступность AI клиентов
    try:
        from agents.tzd_reader_secure import SecureAIAnalyzer
        analyzer = SecureAIAnalyzer()
        status["openai_available"] = analyzer.openai_client is not None
        status["claude_available"] = analyzer.anthropic_client is not None
    except:
        status["openai_available"] = False
        status["claude_available"] = False
    
    return JSONResponse(content=status)


@router.get("/prompts")
async def get_available_prompts():
    """Получить доступные шаблоны промптов"""
    prompts = {
        "basic": {
            "description": "Базовый анализ для быстрого обзора",
            "fields": ["project_name", "project_scope", "materials", "concrete_requirements", "norms"],
            "use_case": "Первичная оценка документа"
        },
        "standard": {
            "description": "Стандартный анализ с учетом чешских норм",
            "fields": ["все поля basic", "quality_requirements", "safety_requirements", "environmental_considerations"],
            "use_case": "Подготовка к проектированию"
        },
        "detailed": {
            "description": "Экспертный анализ для сложных проектов",
            "fields": ["все поля standard", "cost_indicators", "regulatory_compliance", "construction_methods"],
            "use_case": "Детальное планирование и сметное дело"
        }
    }
    
    focus_areas = {
        "concrete": "Фокус на требованиях к бетону и ČSN EN 206",
        "norms": "Детальный поиск всех стандартов и норм",
        "costs": "Анализ стоимостных показателей",
        "timeline": "Временные рамки и этапы",
        "safety": "Требования безопасности",
        "materials": "Подробная спецификация материалов"
    }
    
    return JSONResponse(content={
        "analysis_depths": prompts,
        "focus_areas": focus_areas,
        "supported_languages": ["czech", "english", "mixed"],
        "output_format": "structured_json"
    })


async def cleanup_temp_files(temp_dir: str, analysis_id: str):
    """Фоновая задача для очистки временных файлов"""
    try:
        # Удаляем временные файлы через 1 час
        await asyncio.sleep(3600)
        
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"Очищены временные файлы для анализа {analysis_id}")
        
        # Удаляем из кеша через 24 часа
        await asyncio.sleep(82800)  # 23 часа дополнительно
        if analysis_id in analysis_cache:
            del analysis_cache[analysis_id]
            logger.info(f"Результат анализа {analysis_id} удален из кеша")
            
    except Exception as e:
        logger.error(f"Ошибка очистки для анализа {analysis_id}: {e}")


# Middleware для логирования запросов TZD
@router.middleware("http")
async def log_tzd_requests(request, call_next):
    """Логирование запросов к TZD API"""
    start_time = datetime.now()
    
    response = await call_next(request)
    
    processing_time = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"TZD API: {request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Time: {processing_time:.2f}s"
    )
    
    return response
