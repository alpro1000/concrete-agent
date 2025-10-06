"""
Main FastAPI application for Concrete Agent system.

This module uses absolute imports with the full package path (app.*)
to ensure proper module resolution in all environments (local, Docker, Render).
No sys.path manipulation is needed when running from the project root.
"""

import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import using full package paths for proper module resolution
from app.core import (
    settings,
    init_db,
    check_db_connection,
    app_logger,
    ConcreteAgentException,
)
from app.services import agent_registry
from app.core.orchestrator import orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    app_logger.info("🚀 Starting Concrete Agent application...")

    try:
        init_db()
        app_logger.info("✅ Database initialized")
    except Exception as e:
        app_logger.error(f"❌ Database initialization failed: {e}")

    # Register all agents dynamically
    agent_registry.discover_agents()
    app_logger.info(f"🧠 Discovered agents: {agent_registry.list_agents()}")

    yield

    app_logger.info("🛑 Shutting down Concrete Agent application...")


# --- FastAPI app initialization ---
app = FastAPI(
    title="Concrete Agent API",
    description="Scientific-method based construction analysis system",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Timing middleware ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response


# --- Error handler ---
@app.exception_handler(ConcreteAgentException)
async def concrete_agent_exception_handler(request: Request, exc: ConcreteAgentException):
    app_logger.error(f"ConcreteAgent exception: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"error": exc.message, "details": exc.details},
    )


# --- Endpoints ---
@app.get("/health")
async def health_check():
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "version": "1.0.0",
        "environment": settings.environment,
    }


@app.get("/status")
async def get_status():
    return {
        "status": "operational",
        "agents": agent_registry.list_agents(),
        "database": "connected" if check_db_connection() else "disconnected",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    return {
        "name": "Concrete Agent API",
        "version": "1.0.0",
        "description": "Scientific-method based construction analysis system",
        "documentation": "/docs",
        "health_check": "/health",
        "status": "/status",
    }


# --- Routers ---
# ✅ ВАЖНО: Импортируем роутеры ПОСЛЕ создания объекта app
from app.routers import unified_router, status_router, auth_router

app.include_router(unified_router.router, prefix="/api/agents", tags=["agents"])
app.include_router(status_router.router, prefix="/api", tags=["status"])
app.include_router(auth_router.router)  # auth_router уже имеет prefix="/api/auth"


if __name__ == "__main__":
    import uvicorn

    # Use full package path that works from project root
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=settings.debug,
    )
