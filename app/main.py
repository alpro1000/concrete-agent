# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
import sys

sys.path.append('/app')

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Импортируем app_factory только если он существует
try:
    from app.core.app_factory import setup_core_endpoints
    USE_APP_FACTORY = True
except ImportError:
    USE_APP_FACTORY = False
    logger.warning("app_factory not found, using inline endpoints")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Construction Analysis API starting...")
    
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("storage", exist_ok=True)
    
    try:
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        from app.database import init_database
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init error: {e}")
    
    deps = check_dependencies()
    logger.info(f"Dependencies: {deps}")
    
    setup_routers()
    
    logger.info("Server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Server stopping...")
    try:
        from app.database import close_database
        await close_database()
        logger.info("Database closed")
    except Exception as e:
        logger.error(f"Database close error: {e}")

app = FastAPI(
    title="Construction Analysis API",
    description="Construction document analysis with database support",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def check_dependencies():
    """Check available modules"""
    dependencies = {
        "anthropic": False,
        "pdfplumber": False,
        "docx": False,
        "openpyxl": False,
        "sqlalchemy": False,
        "asyncpg": False
    }
    
    for module_name in dependencies.keys():
        try:
            __import__(module_name)
            dependencies[module_name] = True
        except ImportError:
            logger.warning(f"{module_name} not installed")
    
    return dependencies

def setup_routers():
    """Setup all routers"""
    try:
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        
        from app.routers import (
            projects_router,
            documents_router,
            extractions_router,
            corrections_router,
            compare_router,
            upload_router,
            project_router
        )
        
        from app.routers.analyze_concrete import router as concrete_router
        from app.routers.analyze_materials import router as materials_router
        
        app.include_router(projects_router, prefix="/api", tags=["Projects"])
        app.include_router(documents_router, prefix="/api", tags=["Documents"])
        app.include_router(extractions_router, prefix="/api", tags=["Extractions"])
        app.include_router(corrections_router, prefix="/api", tags=["Corrections"])
        app.include_router(compare_router, prefix="/api", tags=["Compare"])
        app.include_router(upload_router, prefix="/api", tags=["Upload"])
        app.include_router(project_router, prefix="/analyze", tags=["Project Analysis"])
        app.include_router(concrete_router, prefix="/analyze", tags=["Concrete Analysis"])
        app.include_router(materials_router, prefix="/analyze", tags=["Material Analysis"])
        
        logger.info("New routers connected")
        setup_legacy_routers()
        
    except Exception as e:
        logger.error(f"Router setup error: {e}")
        setup_legacy_routers()

def setup_legacy_routers():
    """Setup legacy routers for backward compatibility"""
    router_configs = [
        ("routers.analyze_concrete", "router", "/legacy/analyze", ["Legacy Concrete"]),
        ("routers.analyze_materials", "router", "/legacy/analyze", ["Legacy Materials"]),
        ("routers.analyze_volume", "router", "/legacy/analyze", ["Legacy Volume"]),
        ("routers.analyze_tov", "router", "/legacy/analyze", ["Legacy TOV"]),
        ("routers.version_diff", "router", "/legacy/compare", ["Legacy Diff"]),
        ("routers.upload", "router", "/legacy/upload", ["Legacy Upload"]),
        ("routers.tzd_router", "router", "/legacy/tzd", ["Legacy TZD"]),
    ]
    
    successful = 0
    for module_path, router_name, prefix, tags in router_configs:
        try:
            module = __import__(module_path, fromlist=[router_name])
            router = getattr(module, router_name)
            app.include_router(router, prefix=prefix, tags=tags)
            successful += 1
        except Exception as e:
            logger.warning(f"Failed to load {module_path}: {e}")
    
    logger.info(f"Legacy routers: {successful} loaded")
    return successful

# Setup endpoints - use app_factory if available, otherwise inline
if USE_APP_FACTORY:
    setup_core_endpoints(app)
else:
    # Inline endpoints if app_factory not available
    @app.get("/")
    async def root():
        return {
            "service": "Construction Analysis API",
            "version": "2.0.0",
            "status": "running",
            "endpoints": {
                "docs": "/docs",
                "health": "/health",
                "status": "/status"
            }
        }
    
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "timestamp": "2025-09-30"
        }

@app.get("/status")
async def status():
    """Detailed status"""
    try:
        deps = check_dependencies()
        
        try:
            from app.database import AsyncSessionLocal
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            db_status = "connected"
        except:
            db_status = "disconnected"
        
        return {
            "api_status": "operational",
            "database": db_status,
            "dependencies": deps
        }
    except Exception as e:
        return {"api_status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
