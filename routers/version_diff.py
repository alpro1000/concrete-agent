from fastapi import APIRouter, UploadFile, File, HTTPException
from agents.version_diff_agent import compare_docs, compare_smeta
from config.settings import settings
import tempfile
import os
import shutil
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/docs")
async def compare_docs_endpoint(
    old_docs: list[UploadFile] = File(...),
    new_docs: list[UploadFile] = File(...)
):
    temp_dir = tempfile.mkdtemp()
    try:
        old_paths, new_paths = [], []

        for file in old_docs:
            if not any(file.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
                raise HTTPException(status_code=400, detail=f"❌ Недопустимый тип файла: {file.filename}")
            path = os.path.join(temp_dir, "old_" + file.filename)
            with open(path, "wb") as f:
                f.write(await file.read())
            old_paths.append(path)
            logger.info(f"📄 Старый документ: {file.filename}")

        for file in new_docs:
            if not any(file.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
                raise HTTPException(status_code=400, detail=f"❌ Недопустимый тип файла: {file.filename}")
            path = os.path.join(temp_dir, "new_" + file.filename)
            with open(path, "wb") as f:
                f.write(await file.read())
            new_paths.append(path)
            logger.info(f"📄 Новый документ: {file.filename}")

        return compare_docs(old_paths, new_paths)
    finally:
        shutil.rmtree(temp_dir)
        logger.info("🧹 Временные файлы удалены")


@router.post("/smeta")
async def compare_smeta_endpoint(
    old_smeta: UploadFile = File(...),
    new_smeta: UploadFile = File(...)
):
    temp_dir = tempfile.mkdtemp()
    try:
        if not any(old_smeta.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
            raise HTTPException(status_code=400, detail=f"❌ Недопустимый тип файла: {old_smeta.filename}")
        if not any(new_smeta.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
            raise HTTPException(status_code=400, detail=f"❌ Недопустимый тип файла: {new_smeta.filename}")

        old_path = os.path.join(temp_dir, "old_" + old_smeta.filename)
        new_path = os.path.join(temp_dir, "new_" + new_smeta.filename)

        with open(old_path, "wb") as f:
            f.write(await old_smeta.read())
        with open(new_path, "wb") as f:
            f.write(await new_smeta.read())

        logger.info(f"📑 Старая смета: {old_smeta.filename}")
        logger.info(f"📑 Новая смета: {new_smeta.filename}")

        return compare_smeta(old_path, new_path)
    finally:
        shutil.rmtree(temp_dir)
        logger.info("🧹 Временные файлы удалены")
