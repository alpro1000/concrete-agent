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
    
    yield
    
    # Shutdown
    logger.info("🛑 Construction Analysis API останавливается")

# Создание приложения FastAPI
app = FastAPI(
    title="Construction Analysis API",
    description="Агент для анализа бетона, материалов и версий документов",
    version="1.0.0",
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

# === Автоматическая система роутеров ===
def setup_routers():
    """Автоматическое подключение роутеров с улучшенной обработкой ошибок"""
    try:
        from app.core.router_registry import router_registry
        routers = router_registry.discover_routers("routers")  # Ищем в корневой папке routers
        
        logger.info(f"🔍 Найдено {len(routers)} роутеров для подключения")
        
        successful_routers = 0
        for router_info in routers:
            try:
                app.include_router(
                    router_info['router'],
                    prefix=router_info.get('prefix', ''),
                    tags=router_info.get('tags', [router_info['name']])
                )
                logger.info(f"✅ Роутер {router_info['name']} подключен")
                successful_routers += 1
            except Exception as e:
                logger.error(f"❌ Ошибка подключения роутера {router_info['name']}: {e}")
        
        logger.info(f"📊 Успешно подключено {successful_routers}/{len(routers)} роутеров")
        
        # Fallback к ручному подключению
        if successful_routers == 0:
            logger.warning("⚠️ Автоматическое подключение не сработало, используем fallback")
            setup_routers_fallback()
            
    except Exception as e:
        logger.error(f"❌ Ошибка автоматического подключения роутеров: {e}")
        logger.info("🔄 Переключаемся на ручное подключение")
        setup_routers_fallback()

def setup_routers_fallback():
    """Резервное ручное подключение роутеров"""
    router_configs = [
        ("routers.analyze_concrete", "concrete_router", "/analyze", ["Concrete"]),
        ("routers.analyze_materials", "materials_router", "/analyze", ["Materials"]),
        ("routers.version_diff", "diff_router", "/compare", ["Diff"]),
        ("routers.upload", "upload_router", "/upload", ["Upload"]),
        ("routers.tzd_router", "router", "/tzd", ["TZD"]),
    ]
    
    successful = 0
    for module_path, router_name, prefix, tags in router_configs:
        try:
            module = __import__(module_path, fromlist=[router_name])
            router = getattr(module, router_name)
            app.include_router(router, prefix=prefix, tags=tags)
            logger.info(f"✅ Fallback: роутер {module_path} подключен")
            successful += 1
        except Exception as e:
            logger.warning(f"⚠️ Fallback: не удалось подключить {module_path}: {e}")
    
    return successful

# === Функции для настройки приложения ===

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
