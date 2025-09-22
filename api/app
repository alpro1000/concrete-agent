from fastapi import FastAPI, UploadFile, File
from agents.concrete_agent import analyze_concrete
import shutil
import os
import tempfile

app = FastAPI(
    title="Concrete Intelligence Agent",
    description="LLM-агент для извлечения марок бетона и мест их применения из проектной документации и смет",
    version="1.0"
)

@app.get("/")
async def root():
    return {
        "message": "Concrete Intelligence Agent API",
        "description": "LLM-агент для извлечения марок бетона и мест их применения из проектной документации и смет", 
        "endpoints": {
            "/analyze_concrete": "POST - анализ проектной документации и смет для извлечения марок бетона",
            "/docs": "GET - интерактивная документация API (Swagger UI)",
            "/redoc": "GET - альтернативная документация API (ReDoc)"
        },
        "supported_formats": {
            "docs": ["PDF", "DOCX", "TXT"],
            "smeta": ["XLS", "XLSX", "CSV", "XML"]
        }
    }

@app.post("/analyze_concrete")
async def analyze_concrete_endpoint(docs: list[UploadFile] = File(...), smeta: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_paths = []
        for i, doc in enumerate(docs):
            # Secure file handling: ignore client filename to prevent path traversal
            # Extract only the file extension for proper parsing
            original_ext = ""
            if doc.filename:
                original_ext = os.path.splitext(doc.filename)[1].lower()
            
            # Create secure temporary file with safe name
            secure_filename = f"doc_{i}{original_ext}"
            path = os.path.join(tmpdir, secure_filename)
            
            with open(path, "wb") as f:
                shutil.copyfileobj(doc.file, f)
            doc_paths.append(path)

        # Secure file handling for smeta file
        smeta_ext = ""
        if smeta.filename:
            smeta_ext = os.path.splitext(smeta.filename)[1].lower()
        
        secure_smeta_filename = f"smeta{smeta_ext}"
        smeta_path = os.path.join(tmpdir, secure_smeta_filename)
        
        with open(smeta_path, "wb") as f:
            shutil.copyfileobj(smeta.file, f)

        result = analyze_concrete(doc_paths, smeta_path)
        return result
