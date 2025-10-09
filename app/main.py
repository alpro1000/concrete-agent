"""
FastAPI Main Application
С автоматической загрузкой Knowledge Base

⚠️ ЭТОТ ФАЙЛ НАСТРАИВАЕТСЯ ОДИН РАЗ И БОЛЬШЕ НЕ МЕНЯЕТСЯ!
Все новые файлы KB добавляются просто в папки B1-B8
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.kb_loader import get_knowledge_base
from app.api import routes, routes_resources

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# === LIFESPAN: Загрузка KB при старте ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events
    
    startup: Загружаем Knowledge Base ОДИН РАЗ
    shutdown: Очистка ресурсов
    """
    # === STARTUP ===
    logger.info("🚀 Starting Czech Building Audit System...")
    
    try:
        # Загружаем Knowledge Base
        kb = get_knowledge_base()
        logger.info(f"✅ Knowledge Base loaded: {len(kb.data)} categories")
        
        # Проверяем критичные данные
        kros_codes = kb.get_kros_codes()
        if kros_codes:
            logger.info(f"✅ KROS codes available: {len(kros_codes)} positions")
        else:
            logger.warning("⚠️  No KROS codes found in B1!")
        
        current_prices = kb.get_current_prices()
        if current_prices:
            logger.info(f"✅ Current prices available: {len(current_prices)} material types")
        else:
            logger.warning("⚠️  No current prices found in B3!")
        
        productivity = kb.get_productivity_rates()
        if productivity:
            logger.info(f"✅ Productivity rates available: {len(productivity)} work types")
        else:
            logger.warning("⚠️  No productivity rates found in B4!")
        
        logger.info("✅ System ready!")
        
    except Exception as e:
        logger.error(f"❌ Failed to load Knowledge Base: {e}")
        raise
    
    yield  # Приложение работает
    
    # === SHUTDOWN ===
    logger.info("🛑 Shutting down...")


# === СОЗДАНИЕ ПРИЛОЖЕНИЯ ===

app = FastAPI(
    title="Czech Building Audit System",
    description="Automated construction project auditing with Claude AI",
    version="1.0.0",
    lifespan=lifespan  # ← Автоматическая загрузка KB здесь!
)


# === CORS ===

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === ROUTES ===

# API endpoints
app.include_router(routes.router)
app.include_router(routes_resources.router)  # Resource calculation endpoints

# NEW: Workflow-specific endpoints
try:
    from app.api import routes_workflow_a, routes_workflow_b, routes_parsing
    app.include_router(routes_workflow_a.router)
    app.include_router(routes_workflow_b.router)
    app.include_router(routes_parsing.router)
    logger.info("✅ Workflow A/B and parsing routes loaded")
except Exception as e:
    logger.warning(f"⚠️  Failed to load new workflow routes: {e}")


# === STATIC FILES (Frontend) ===

if settings.WEB_DIR.exists():
    app.mount(
        "/web",
        StaticFiles(directory=str(settings.WEB_DIR), html=True),
        name="web"
    )


# === ROOT ENDPOINT ===

@app.get("/")
async def root():
    """
    Root endpoint - информация о сервисе
    
    Также показывает статус Knowledge Base
    """
    kb = get_knowledge_base()
    
    return {
        "service": "Czech Building Audit System",
        "version": "1.0.0",
        "status": "running",
        "knowledge_base": {
            "loaded_at": kb.loaded_at.isoformat() if kb.loaded_at else None,
            "categories": len(kb.data),
            "status": "ready" if kb.data else "empty"
        },
        "endpoints": {
            "api_docs": "/docs",
            "upload": "/api/upload",
            "audit": "/api/audit/{project_id}",
            "resources": "/api/resources/*",
            "frontend": "/web/index.html"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Проверяет что KB загружена и доступна
    """
    kb = get_knowledge_base()
    
    # Проверяем критичные категории
    has_kros = bool(kb.get_kros_codes())
    has_prices = bool(kb.get_current_prices())
    has_benchmarks = bool(kb.get_productivity_rates())
    
    all_healthy = has_kros and has_prices and has_benchmarks
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "kb_loaded": kb.loaded_at is not None,
        "checks": {
            "kros_codes": "ok" if has_kros else "missing",
            "current_prices": "ok" if has_prices else "missing",
            "benchmarks": "ok" if has_benchmarks else "missing"
        }
    }


@app.get("/kb/status")
async def kb_status():
    """
    Детальная информация о Knowledge Base
    
    Показывает что загружено в каждой категории
    """
    kb = get_knowledge_base()
    
    status = {}
    
    for category in kb.CATEGORIES:
        if category in kb.data:
            files = list(kb.data[category].keys())
            metadata = kb.metadata.get(category, {})
            
            status[category] = {
                "files_count": len(files),
                "files": files[:5],  # Первые 5 файлов
                "last_updated": metadata.get("last_updated"),
                "version": metadata.get("version")
            }
        else:
            status[category] = {
                "status": "not_loaded",
                "files_count": 0
            }
    
    return {
        "loaded_at": kb.loaded_at.isoformat() if kb.loaded_at else None,
        "categories": status
    }


@app.post("/kb/reload")
async def kb_reload():
    """
    🔄 Перезагрузка Knowledge Base
    
    Используется когда добавили новые файлы без перезапуска сервиса.
    В production можно защитить паролем или API ключом.
    """
    try:
        # Сбрасываем singleton
        from app.core import kb_loader
        kb_loader._kb_instance = None
        
        # Загружаем заново
        kb = get_knowledge_base()
        
        return {
            "status": "success",
            "message": "Knowledge Base reloaded",
            "loaded_at": kb.loaded_at.isoformat(),
            "categories": len(kb.data)
        }
    
    except Exception as e:
        logger.error(f"Failed to reload KB: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload Knowledge Base: {str(e)}"
        )


# === ERROR HANDLERS ===

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Not Found",
        "message": "The requested resource was not found",
        "path": request.url.path
    }


@app.exception_handler(500)
async def server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    }


# === STARTUP MESSAGE ===

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  🏗️  Czech Building Audit System                        ║
    ║                                                          ║
    ║  🚀 Starting server...                                   ║
    ║  📚 Knowledge Base будет загружена автоматически         ║
    ║                                                          ║
    ║  📖 API Docs: http://localhost:8000/docs                ║
    ║  🌐 Frontend: http://localhost:8000/web/index.html      ║
    ║  ❤️  Health:   http://localhost:8000/health             ║
    ║  📊 KB Status: http://localhost:8000/kb/status          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload при изменении кода
    )
