# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

# Логирование
from utils.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# Подключение роутеров
from routers import analyze_concrete, analyze_materials, version_diff, upload

app = FastAPI(
    title="Construction Analysis API",
    description="Агент для анализа бетона, материалов и версий документов",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://stav-agent.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(analyze_concrete.router, prefix="/analyze", tags=["Concrete"])
app.include_router(analyze_materials.router, prefix="/analyze", tags=["Materials"])
app.include_router(version_diff.router, prefix="/compare", tags=["Diff"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Construction Analysis API запущен")
    logger.info("➡️ Доступные эндпоинты: /analyze/concrete, /analyze/materials, /compare/docs, /compare/smeta, /upload/files")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Construction Analysis API остановлен")

@app.get("/")
async def root():
    claude_status = "enabled" if os.getenv("ANTHROPIC_API_KEY") else "disabled"
    return {
        "message": "Construction Analysis API",
        "version": "1.0.0",
        "status": "running",
        "claude_status": claude_status,
        "endpoints": {
            "analyze_concrete": "/analyze/concrete",
            "analyze_materials": "/analyze/materials",
            "compare_docs": "/compare/docs",
            "compare_smeta": "/compare/smeta",
            "upload_files": "/upload/files",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
