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
    logger.info("TZD Reader API starting...")
    
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    deps = check_dependencies()
    logger.info(f"Dependencies: {deps}")
    
    setup_routers()
    
    logger.info("Server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Server stopping...")

app = FastAPI(
    title="TZD Reader API",
    description="Technical Assignment Reader for construction documents",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

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

def check_dependencies():
    """Check available modules"""
    dependencies = {
        "anthropic": False,
        "pdfplumber": False,
        "docx": False
    }
    
    for module_name in dependencies.keys():
        try:
            __import__(module_name)
            dependencies[module_name] = True
        except ImportError:
            logger.warning(f"{module_name} not installed")
    
    return dependencies

def setup_routers():
    """Auto-discover and setup routers from app/routers/"""
    try:
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        
        from app.core.router_registry import router_registry
        
        # Auto-discover all routers
        discovered_routers = router_registry.discover_routers("app/routers")
        
        # Register discovered routers
        for router_info in discovered_routers:
            try:
                router = router_info['router']
                # Don't pass prefix again - router already has it
                tags = router_info.get('tags', [router_info['name']])
                
                app.include_router(router, tags=tags)
                logger.info(f"✅ Router '{router_info['name']}' registered successfully")
            except Exception as e:
                logger.error(f"❌ Failed to register router '{router_info['name']}': {e}")
        
        # Log registry status
        status = router_registry.get_registry_status()
        logger.info(f"Router registry: {status['successful']}/{status['total_discovered']} routers loaded")
        
        if status['failed']:
            logger.warning(f"Failed routers: {status['failed_routers']}")
        
    except Exception as e:
        logger.error(f"Router setup error: {e}")
        # Don't raise - continue running without routers if necessary

# Setup endpoints - use app_factory if available, otherwise inline
if USE_APP_FACTORY:
    setup_core_endpoints(app)
else:
    # Inline endpoints if app_factory not available
    @app.get("/")
    async def root():
        return {
            "service": "TZD Reader API",
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
        
        return {
            "api_status": "operational",
            "dependencies": deps
        }
    except Exception as e:
        return {"api_status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
