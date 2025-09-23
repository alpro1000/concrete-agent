from fastapi import APIRouter, UploadFile, File
from agents.concrete_agent import analyze_concrete
import tempfile
import os
import shutil
import asyncio

router = APIRouter()

@router.post("/concrete")
async def analyze_concrete_endpoint(docs: list[UploadFile] = File(...), smeta: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        doc_paths = []
        for file in docs:
            path = os.path.join(temp_dir, file.filename)
            with open(path, "wb") as f:
                f.write(await file.read())
            doc_paths.append(path)

        smeta_path = os.path.join(temp_dir, smeta.filename)
        with open(smeta_path, "wb") as f:
            f.write(await smeta.read())

        result = await analyze_concrete(doc_paths, smeta_path)
        return result
    finally:
        shutil.rmtree(temp_dir)
