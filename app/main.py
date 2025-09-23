# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import logging

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
from utils.logging_config import setup_logging
setup_logging()

from routers import upload, analyze

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Concrete Analysis Agent",
    description="LLM-агент для извлечения марок бетона и материалов из проектной документации",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analyze.router, prefix="/analyze", tags=["analysis"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])

@app.on_event("startup")
async def startup_event():
    logger.info("Concrete Analysis Agent запущен")
    logger.info(f"Доступные эндпоинты: /analyze/concrete, /upload/files")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Concrete Analysis Agent остановлен")

@app.get("/")
async def root():
    claude_status = "enabled" if os.getenv("ANTHROPIC_API_KEY") else "disabled"
    return {
        "message": "Concrete Analysis Agent API",
        "version": "1.0.0",
        "status": "running",
        "claude_status": claude_status,
        "endpoints": {
            "analyze_concrete": "/analyze/concrete",
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
