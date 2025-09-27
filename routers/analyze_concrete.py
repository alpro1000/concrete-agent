from fastapi import APIRouter, UploadFile, File, HTTPException
import sys
import os

# Import from the main concrete_agent.py file (not the package)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import importlib.util
spec = importlib.util.spec_from_file_location("concrete_agent_main", 
        os.path.join(os.path.dirname(__file__), '..', 'agents', 'concrete_agent.py'))
concrete_agent_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(concrete_agent_main)
analyze_concrete = concrete_agent_main.analyze_concrete

from config.settings import settings
import tempfile
import os
import shutil
import asyncio
import logging

router = APIRouter()
concrete_router = router  # Alias for main.py compatibility
logger = logging.getLogger(__name__)

@router.post("/concrete")
async def analyze_concrete_endpoint(
    docs: list[UploadFile] = File(...),
    smeta: UploadFile = File(...)
):
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

        if not any(smeta.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
            raise HTTPException(status_code=400, detail=f"❌ Недопустимый тип файла сметы: {smeta.filename}")
        smeta_path = os.path.join(temp_dir, smeta.filename)
        with open(smeta_path, "wb") as f:
            f.write(await smeta.read())
        logger.info(f"📑 Загружена смета: {smeta.filename}")

        result = await analyze_concrete(doc_paths, smeta_path)
        return result
    finally:
        shutil.rmtree(temp_dir)
        logger.info("🧹 Временные файлы удалены")
