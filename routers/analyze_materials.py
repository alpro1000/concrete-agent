from fastapi import APIRouter, UploadFile, File
from agents.materials_agent import analyze_materials
import tempfile
import os
import shutil

router = APIRouter()

@router.post("/materials")
async def analyze_materials_endpoint(docs: list[UploadFile] = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        doc_paths = []
        for file in docs:
            path = os.path.join(temp_dir, file.filename)
            with open(path, "wb") as f:
                f.write(await file.read())
            doc_paths.append(path)

        result = analyze_materials(doc_paths)
        return result
    finally:
        shutil.rmtree(temp_dir)
