# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# Создание приложения FastAPI
app = FastAPI(
    title="Construction Analysis API",
    description="Агент для анализа бетона, материалов и версий документов",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
        "openpyxl": False
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
    
    return dependencies

# === Безопасное подключение роутеров ===
def setup_routers():
    """Безопасное подключение роутеров с обработкой ошибок"""
    try:
        from routers.analyze_concrete import router as concrete_router
        app.include_router(concrete_router, prefix="/analyze", tags=["Concrete"])
        logger.info("✅ Роутер analyze_concrete подключен")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения роутера analyze_concrete: {e}")
    
    try:
        from routers.analyze_materials import router as materials_router
        app.include_router(materials_router, prefix="/analyze", tags=["Materials"])
        logger.info("✅ Роутер analyze_materials подключен")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения роутера analyze_materials: {e}")
    
    try:
        from routers.version_diff import router as diff_router
        app.include_router(diff_router, prefix="/compare", tags=["Diff"])
        logger.info("✅ Роутер version_diff подключен")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения роутера version_diff: {e}")
    
    try:
        from routers.upload import router as upload_router
        app.include_router(upload_router, prefix="/upload", tags=["Upload"])
        logger.info("✅ Роутер upload подключен")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения роутера upload: {e}")

# === События жизненного цикла ===
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Construction Analysis API запускается...")
    
    # Создаем необходимые директории
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    
    # Проверяем зависимости
    deps = check_dependencies()
    logger.info(f"📦 Статус зависимостей: {deps}")
    
    # Подключаем роутеры
    setup_routers()
    
    logger.info("✅ Сервер успешно запущен")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Construction Analysis API останавливается")

# === Основные эндпоинты ===
@app.get("/")
async def root():
    """Главная страница с информацией о сервисе"""
    claude_status = "enabled" if os.getenv("ANTHROPIC_API_KEY") else "disabled"
    
    return {
        "service": "Construction Analysis API",
        "version": "1.0.0",
        "status": "running",
        "claude_status": claude_status,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "analyze_concrete": "/analyze/concrete",
            "analyze_materials": "/analyze/materials",
            "compare_docs": "/compare/docs",
            "compare_smeta": "/compare/smeta",
            "upload_files": "/upload/files"
        },
        "dependencies": check_dependencies()
    }

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {
        "status": "healthy",
        "timestamp": "2025-09-24T12:00:00Z",
        "uptime": "running"
    }

@app.get("/status")
async def detailed_status():
    """Подробный статус сервиса"""
    try:
        deps = check_dependencies()
        return {
            "api_status": "operational",
            "dependencies": deps,
            "claude_available": bool(os.getenv("ANTHROPIC_API_KEY")),
            "directories": {
                "uploads": os.path.exists("uploads"),
                "logs": os.path.exists("logs"),
                "outputs": os.path.exists("outputs")
            },
            "python_path": sys.path[:3],  # Первые 3 пути
            "environment_vars": {
                "USE_CLAUDE": os.getenv("USE_CLAUDE", "not_set"),
                "MAX_FILE_SIZE": os.getenv("MAX_FILE_SIZE", "not_set"),
                "PORT": os.getenv("PORT", "not_set")
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
        "timestamp": "2025-09-24T12:00:00Z"
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
                "/analyze/concrete", "/analyze/materials",
                "/compare/docs", "/compare/smeta", "/upload/files"
            ]
        }
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
