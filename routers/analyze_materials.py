from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from agents.integration_orchestrator import get_integration_orchestrator, IntegratedAnalysisRequest
from agents.materials_agent import analyze_materials  # Keep for backward compatibility
from config.settings import settings
import tempfile
import os
import shutil
import logging
from typing import Optional, List

router = APIRouter()
materials_router = router  # Alias for main.py compatibility
logger = logging.getLogger(__name__)

@router.post("/materials")
async def analyze_materials_integrated_endpoint(
    docs: List[UploadFile] = File(..., description="Основные документы (PDF, DOCX, TXT)"),
    smeta: UploadFile = File(..., description="Смета или выказ вымер (XLSX, CSV, PDF). Если нет файла сметы, загрузите пустой файл."),
    material_query: Optional[str] = Form(None, description="Запрос материала (арматура, окна, двери, плитка)"),
    use_claude: bool = Form(True, description="Использовать Claude AI для анализа"),
    claude_mode: str = Form("enhancement", description="Режим Claude: enhancement или primary"),
    language: str = Form("cz", description="Язык отчетов: cz, en, ru"),
    include_drawing_analysis: bool = Form(False, description="Включить анализ чертежей (пока не реализовано)")
):
    """
    🚀 НОВЫЙ ИНТЕГРИРОВАННЫЙ ЭНДПОИНТ для автоматического анализа строительных материалов
    
    Выполняет последовательно:
    1. ConcreteAgent - анализ марок бетона и их местоположения
    2. VolumeAgent - анализ объемов на основе найденных марок и сметы
    3. MaterialAgent - поиск указанного материала во всех источниках
    4. DrawingVolumeAgent - анализ геометрии из чертежей (опционально, в разработке)
    
    Возвращает единый JSON с результатами всех агентов и статусами анализа.
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Сохраняем загруженные файлы
        doc_paths = []
        for file in docs:
            if not any(file.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
                raise HTTPException(
                    status_code=400, 
                    detail=f"❌ Недопустимый тип файла: {file.filename}. Разрешены: {', '.join(settings.ALLOWED_EXTENSIONS)}"
                )
            path = os.path.join(temp_dir, file.filename)
            with open(path, "wb") as f:
                f.write(await file.read())
            doc_paths.append(path)
            logger.info(f"📄 Загружен документ: {file.filename}")

        # Обрабатываем смету, если она есть и не пустая
        smeta_path = None
        if smeta and smeta.filename and smeta.size > 0:
            if not any(smeta.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
                raise HTTPException(
                    status_code=400, 
                    detail=f"❌ Недопустимый тип файла сметы: {smeta.filename}"
                )
            smeta_path = os.path.join(temp_dir, smeta.filename)
            with open(smeta_path, "wb") as f:
                f.write(await smeta.read())
            logger.info(f"📑 Загружена смета: {smeta.filename}")
        else:
            logger.info("📑 Смета не предоставлена или файл пустой")

        # Создаем запрос для интегрированного анализа
        request = IntegratedAnalysisRequest(
            doc_paths=doc_paths,
            smeta_path=smeta_path,
            material_query=material_query,
            use_claude=use_claude,
            claude_mode=claude_mode,
            language=language,
            include_drawing_analysis=include_drawing_analysis
        )

        # Получаем оркестратор и выполняем анализ
        orchestrator = get_integration_orchestrator()
        result = await orchestrator.analyze_materials_integrated(request)

        # Логируем результат
        if result.success:
            logger.info("✅ Интегрированный анализ завершен успешно")
            logger.info(f"📊 Найдено марок бетона: {result.concrete_summary.get('total_grades', 0)}")
            logger.info(f"📐 Объем анализа: {result.volume_summary.get('total_volume_m3', 0)} м³")
            logger.info(f"🔧 Найдено материалов: {result.material_summary.get('total_materials', 0)}")
        else:
            logger.error(f"❌ Ошибка интегрированного анализа: {result.error_message}")

        # Конвертируем в словарь для JSON response
        result_dict = {
            "success": result.success,
            "error_message": result.error_message,
            "concrete_analysis": result.concrete_summary,
            "volume_analysis": result.volume_summary,
            "material_analysis": result.material_summary,
            "drawing_analysis": result.drawing_summary,
            "sources": result.sources,
            "analysis_status": result.analysis_status,
            "request_parameters": {
                "material_query": material_query,
                "use_claude": use_claude,
                "claude_mode": claude_mode,
                "language": language,
                "documents_count": len(doc_paths),
                "smeta_provided": smeta_path is not None,
                "include_drawing_analysis": include_drawing_analysis
            }
        }

        return result_dict

    except HTTPException:
        # Переподымаем HTTP исключения
        raise
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в интегрированном анализе: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_message": str(e),
                "concrete_analysis": {},
                "volume_analysis": {},
                "material_analysis": {},
                "analysis_status": {
                    "concrete_analysis": "error",
                    "volume_analysis": "error", 
                    "material_analysis": "error"
                }
            }
        )
    finally:
        # Очищаем временные файлы
        shutil.rmtree(temp_dir)
        logger.info("🧹 Временные файлы удалены")

# Сохраняем старую версию для обратной совместимости
@router.post("/materials-legacy")
async def analyze_materials_legacy_endpoint(docs: list[UploadFile] = File(...)):
    """
    Старая версия эндпоинта для анализа материалов (для обратной совместимости)
    Рекомендуется использовать /materials для новых интеграций
    """
    temp_dir = tempfile.mkdtemp()
    try:
        doc_paths = []
        for file in docs:
            if not any(file.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
                raise HTTPException(status_code=400, detail=f"❌ Недопустимый тип файла: {file.filename}")
            path = os.path.join(temp_dir, file.filename)
            with open(path, "wb") as f:
                f.write(await file.read())
            doc_paths.append(path)
            logger.info(f"📄 Загружен документ: {file.filename}")

        result = analyze_materials(doc_paths)
        return result
    finally:
        shutil.rmtree(temp_dir)
        logger.info("🧹 Временные файлы удалены")
