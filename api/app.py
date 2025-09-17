from fastapi import FastAPI, UploadFile, File
from agents.concrete_agent import analyze_concrete
import shutil
import os
import tempfile

app = FastAPI()

@app.post("/analyze_concrete")
async def analyze_concrete_endpoint(docs: list[UploadFile] = File(...), smeta: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_paths = []
        for doc in docs:
            path = os.path.join(tmpdir, doc.filename)
            with open(path, "wb") as f:
                shutil.copyfileobj(doc.file, f)
            doc_paths.append(path)

        smeta_path = os.path.join(tmpdir, smeta.filename)
        with open(smeta_path, "wb") as f:
            shutil.copyfileobj(smeta.file, f)

        result = analyze_concrete(doc_paths, smeta_path)
        return result
