from fastapi import APIRouter, UploadFile, File, HTTPException
from agents.materials_agent import analyze_materials
from config.settings import settings
import tempfile
import os
import shutil
import logging

router = APIRouter()
materials_router = router  # Alias for main.py compatibility
logger = logging.getLogger(__name__)


@router.post("/materials")
async def analyze_materials_endpoint(docs: list[UploadFile] = File(...)):
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
