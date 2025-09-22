from fastapi import APIRouter, UploadFile, File
from agents.concrete_agent import analyze_concrete
import shutil
import os
import tempfile

router = APIRouter()

@router.post("/concrete")
async def analyze_concrete_route(docs: list[UploadFile] = File(...), smeta: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_paths = []

        for i, doc in enumerate(docs):
            ext = os.path.splitext(doc.filename)[1]
            filename = f"doc_{i}{ext}"
            path = os.path.join(tmpdir, filename)
            with open(path, "wb") as f:
                shutil.copyfileobj(doc.file, f)
            doc_paths.append(path)

        smeta_ext = os.path.splitext(smeta.filename)[1]
        smeta_path = os.path.join(tmpdir, f"smeta{smeta_ext}")
        with open(smeta_path, "wb") as f:
            shutil.copyfileobj(smeta.file, f)

        result = analyze_concrete(doc_paths, smeta_path)
        return result
