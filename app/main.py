# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
import sys

# Добавляем путь к проекту в PYTHONPATH
sys.path.append('/app')

# Настройка базового логирования
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Construction Analysis API с базой данных запускается...")
    
    # Создаем необходимые директории
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("storage", exist_ok=True)
    
    # Инициализация базы данных
    try:
        import sys
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        from app.database import init_database
        await init_database()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        # Continue without database for now
    
    # Проверяем зависимости
    deps = check_dependencies()
    logger.info(f"📦 Статус зависимостей: {deps}")
    
    # Подключаем роутеры
    setup_routers()
    
    logger.info("✅ Сервер успешно запущен")
    
    yield
    
    # Shutdown
    logger.info("🛑 Construction Analysis API останавливается")
    try:
        import sys
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        from app.database import close_database
        await close_database()
        logger.info("🔌 База данных отключена")
    except Exception as e:
        logger.error(f"❌ Ошибка отключения базы данных: {e}")

# Создание приложения FastAPI
app = FastAPI(
    title="Construction Analysis API",
    description="Агент для анализа бетона, материалов и версий документов с поддержкой базы данных",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Проверка зависимостей ===
def check_dependencies():
    """Проверяем доступность основных модулей"""
    dependencies = {
        "anthropic": False,
        "pdfplumber": False,
        "docx": False,
        "openpyxl": False,
        "sqlalchemy": False,
        "asyncpg": False
    }
    
    try:
        import anthropic
        dependencies["anthropic"] = True
    except ImportError:
        logger.warning("⚠️ anthropic не установлен")
    
    try:
        import pdfplumber
        dependencies["pdfplumber"] = True
    except ImportError:
        logger.warning("⚠️ pdfplumber не установлен")
    
    try:
        from docx import Document
        dependencies["docx"] = True
    except ImportError:
        logger.warning("⚠️ python-docx не установлен")
    
    try:
        import openpyxl
        dependencies["openpyxl"] = True
    except ImportError:
        logger.warning("⚠️ openpyxl не установлен")
        
    try:
        import sqlalchemy
        dependencies["sqlalchemy"] = True
    except ImportError:
        logger.warning("⚠️ sqlalchemy не установлен")
        
    try:
        import asyncpg
        dependencies["asyncpg"] = True
    except ImportError:
        logger.warning("⚠️ asyncpg не установлен")
    
    return dependencies

# === Настройка роутеров ===
def setup_routers():
    """Подключение всех роутеров"""
    try:
        import sys
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        
        # Новые роутеры с поддержкой базы данных
        from app.routers import (
            projects_router,
            documents_router,
            extractions_router,
            corrections_router,
            compare_router,
            upload_router,
            project_router
        )
        
        app.include_router(projects_router, prefix="/api", tags=["Projects"])
        app.include_router(documents_router, prefix="/api", tags=["Documents"])
        app.include_router(extractions_router, prefix="/api", tags=["Extractions"])
        app.include_router(corrections_router, prefix="/api", tags=["Corrections"])
        app.include_router(compare_router, prefix="/api", tags=["Compare"])
        app.include_router(upload_router, prefix="/api", tags=["Upload"])
        app.include_router(project_router, prefix="/analyze", tags=["Project Analysis"])
        
        logger.info("✅ Новые роутеры подключены")
        
        # Подключение старых роутеров для обратной совместимости
        setup_legacy_routers()
        
    except Exception as e:
        logger.error(f"❌ Ошибка подключения роутеров: {e}")
        setup_legacy_routers()

def setup_legacy_routers():
    """Резервное подключение старых роутеров для обратной совместимости"""
    router_configs = [
        ("routers.analyze_concrete", "router", "/analyze", ["Concrete"]),
        ("routers.analyze_materials", "router", "/analyze", ["Materials"]),
        ("routers.analyze_volume", "router", "/analyze", ["Volume"]),
        ("routers.analyze_tov", "router", "/analyze", ["TOV"]),
        ("routers.version_diff", "router", "/compare", ["Diff"]),
        ("routers.upload", "router", "/upload", ["Upload"]),
        ("routers.tzd_router", "router", "/tzd", ["TZD"]),
        # New specialized upload routers
        ("routers.upload_docs", "router", "/upload", ["Upload Docs"]),
        ("routers.upload_smeta", "router", "/upload", ["Upload Estimates"]),
        ("routers.upload_drawings", "router", "/upload", ["Upload Drawings"]),
    ]
    
    successful = 0
    for module_path, router_name, prefix, tags in router_configs:
        try:
            module = __import__(module_path, fromlist=[router_name])
            router = getattr(module, router_name)
            app.include_router(router, prefix=prefix, tags=tags)
            logger.info(f"✅ Legacy: роутер {module_path} подключен")
            successful += 1
        except Exception as e:
            logger.warning(f"⚠️ Legacy: не удалось подключить {module_path}: {e}")
    
    logger.info(f"📊 Legacy роутеров подключено: {successful}")
    return successful

# === Основные эндпоинты ===
@app.get("/")
async def root():
    """Главная страница с информацией о сервисе"""
    claude_status = "enabled" if os.getenv("ANTHROPIC_API_KEY") else "disabled"
    
    return {
        "service": "Construction Analysis API",
        "version": "2.0.0",
        "status": "running",
        "features": {
            "database_storage": True,
            "multi_file_upload": True,
            "zip_support": True,
            "self_learning": True,
            "backward_compatibility": True
        },
        "claude_status": claude_status,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "projects": "/api/projects",
            "upload": "/api/projects/{id}/upload",
            "compare": "/api/projects/{id}/compare",
            # New specialized upload endpoints
            "upload_docs": "/upload/docs",
            "upload_estimates": "/upload/smeta", 
            "upload_drawings": "/upload/drawings",
            # Legacy endpoints
            "analyze_concrete": "/analyze/concrete",
            "analyze_materials": "/analyze/materials",
            "analyze_volume": "/analyze/volume",
            "analyze_tov": "/analyze/tov",
            "compare_docs": "/compare/docs",
            "upload_files": "/upload/files"
        },
        "dependencies": check_dependencies()
    }

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    try:
        # Проверяем подключение к базе данных
        import sys
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        from app.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": "2025-09-28T12:00:00Z",
        "database": db_status,
        "uptime": "running"
    }

@app.get("/status")
async def detailed_status():
    """Подробный статус сервиса"""
    try:
        deps = check_dependencies()
        
        # Проверяем базу данных
        try:
            import sys
            sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
            from app.database import AsyncSessionLocal
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            db_status = "operational"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        return {
            "api_status": "operational",
            "database_status": db_status,
            "dependencies": deps,
            "claude_available": bool(os.getenv("ANTHROPIC_API_KEY")),
            "directories": {
                "uploads": os.path.exists("uploads"),
                "logs": os.path.exists("logs"),
                "outputs": os.path.exists("outputs"),
                "storage": os.path.exists("storage")
            },
            "python_path": sys.path[:3],  # Первые 3 пути
            "environment_vars": {
                "USE_CLAUDE": os.getenv("USE_CLAUDE", "not_set"),
                "MAX_FILE_SIZE": os.getenv("MAX_FILE_SIZE", "not_set"),
                "PORT": os.getenv("PORT", "not_set"),
                "DATABASE_URL": "configured" if os.getenv("DATABASE_URL") else "default"
            }
        }
    except Exception as e:
        return {
            "api_status": "error",
            "error": str(e)
        }

# === Простой тестовый эндпоинт ===
@app.post("/test/echo")
async def test_echo(data: dict = None):
    """Простой эхо-тест для проверки POST запросов"""
    return {
        "received": data or {},
        "message": "Echo test successful",
        "timestamp": "2025-09-28T12:00:00Z"
    }

# === Обработчики ошибок ===
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"500 Internal Server Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "Произошла внутренняя ошибка сервера",
            "detail": str(exc) if os.getenv("DEBUG") == "true" else "Contact support"
        }
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"Эндпоинт {request.url.path} не найден",
            "available_endpoints": [
                "/", "/docs", "/health", "/status",
                "/api/projects", "/api/projects/{id}/upload",
                "/upload/docs", "/upload/smeta", "/upload/drawings",
                "/analyze/concrete", "/analyze/materials",
                "/compare/docs", "/compare/smeta", "/upload/files"
            ]
        }
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
