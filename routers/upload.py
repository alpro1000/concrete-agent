from fastapi import APIRouter, UploadFile, File
import os
import shutil
import uuid

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/files")
async def upload_files(files: list[UploadFile] = File(...)):
    saved_paths = []

    for file in files:
        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        path = os.path.join(UPLOAD_DIR, filename)

        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_paths.append({"filename": filename, "path": path})

    return {"uploaded_files": saved_paths}
