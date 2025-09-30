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
    """Setup TZD router only"""
    try:
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        
        from app.routers import tzd_router
        
        # Include only TZD router
        app.include_router(tzd_router, tags=["TZD Reader"])
        
        logger.info("TZD Router connected successfully")
        
    except Exception as e:
        logger.error(f"Router setup error: {e}")
        raise

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
