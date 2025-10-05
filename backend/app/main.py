"""
main.py — центральная точка входа Stav Agent / Concrete Agent Backend

📦 Назначение:
    - Инициализация FastAPI-приложения
    - Загрузка конфигурации и логгера
    - Подключение маршрутов (API)
    - Настройка базы данных
    - Инициализация агентов и Knowledge Base
    - Проверка готовности LLM-сервисов
"""

import asyncio
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Core modules
from app.core.config import settings
from app.core.database import init_db
from app.core.logger import configure_logging
from app.core.orchestrator import Orchestrator
from app.core.llm_service import LLMService
from app.core.prompt_loader import PromptLoader
from app.services.file_storage import ensure_storage_dirs

# Routers
from app.routers import (
    unified_router,
    results_router,
    user_router,
    chat_router,
    health_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Здесь выполняется инициализация всех системных компонентов.
    """
    logging.info("🚀 Initializing Stav Agent backend environment...")
    await init_db()
    ensure_storage_dirs()
    Orchestrator.initialize()
    PromptLoader.preload_prompts()
    await LLMService.verify_connectivity()
    logging.info("✅ Backend environment ready")
    yield
    logging.info("🧩 Shutting down Stav Agent backend gracefully...")


# --- FastAPI application instance ---
app = FastAPI(
    title="Stav Agent / Concrete Agent API",
    version="1.0.0",
    description=(
        "Modular AI-driven construction analysis system "
        "for reading, analyzing and synthesizing building documentation."
    ),
    lifespan=lifespan
)


# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production: restrict by domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routers registration ---
app.include_router(health_router.router, prefix="/api/v1/health", tags=["health"])
app.include_router(user_router.router, prefix="/api/v1/user", tags=["user"])
app.include_router(unified_router.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(results_router.router, prefix="/api/v1/results", tags=["results"])
app.include_router(chat_router.router, prefix="/api/v1/chat", tags=["chat"])


# --- Startup message ---
@app.on_event("startup")
async def startup_event():
    configure_logging()
    logging.info("🔧 Stav Agent backend starting...")
    logging.info(f"LLM Provider: {settings.LLM_PROVIDER} ({settings.LLM_MODEL})")
    logging.info(f"Backup Provider: {settings.LLM_BACKUP_PROVIDER}")
    logging.info(f"Database URL: {settings.DB_URL}")
    logging.info("📚 Knowledge base and prompts initialized successfully.")


# --- Root endpoint ---
@app.get("/")
async def root():
    """
    Простой приветственный маршрут (проверка API)
    """
    return {
        "service": "Stav Agent / Concrete Agent Backend",
        "status": "running",
        "llm_provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "version": "1.0.0"
    }


# --- Run manually (for local dev only) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
