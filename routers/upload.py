from fastapi import APIRouter, UploadFile, File, HTTPException
from config.settings import settings
import os
import uuid
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/files")
async def upload_files(files: list[UploadFile] = File(...)):
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    saved_files = []
    for file in files:
        if not any(file.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
            raise HTTPException(status_code=400, detail=f"❌ Недопустимый тип файла: {file.filename}")

        unique_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, unique_name)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        saved_files.append({"filename": file.filename, "path": file_path})
        logger.info(f"📂 Файл загружен: {file.filename} → {file_path}")

    return {"uploaded": saved_files}
