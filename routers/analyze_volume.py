from fastapi import APIRouter, UploadFile, File, HTTPException
from agents.volume_agent.agent import get_volume_analysis_agent
from config.settings import settings
import tempfile
import os
import shutil
import logging

router = APIRouter()
volume_router = router  # Alias for main.py compatibility
logger = logging.getLogger(__name__)


@router.post("/volume")
async def analyze_volume_endpoint(docs: list[UploadFile] = File(...)):
    """
    Анализ объемов в строительных документах
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

        # Используем агент анализа объемов
        volume_agent = get_volume_analysis_agent()
        result = await volume_agent.analyze_documents(doc_paths)
        
        return {
            "status": "success",
            "analysis_type": "volume_analysis",
            "files_processed": len(doc_paths),
            "result": result
        }
    except Exception as e:
        logger.error(f"❌ Ошибка анализа объемов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа объемов: {str(e)}")
    finally:
        shutil.rmtree(temp_dir)
        logger.info("🧹 Временные файлы удалены")