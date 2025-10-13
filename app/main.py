"""
FastAPI Application Entry Point
Czech Building Audit System
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.api.routes import router as main_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Czech Building Audit System",
    description="AI-powered construction audit system for Czech market",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(main_router)

# Mount static files (if web directory exists)
web_dir = settings.BASE_DIR / "web"
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")
    logger.info(f"📁 Static files mounted: {web_dir}")


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("=" * 80)
    logger.info("🚀 Czech Building Audit System Starting...")
    logger.info("=" * 80)
    logger.info(f"📂 Base directory: {settings.BASE_DIR}")
    logger.info(f"📂 Data directory: {settings.DATA_DIR}")
    logger.info(f"📚 KB directory: {settings.KB_DIR}")
    logger.info(f"📝 Prompts directory: {settings.PROMPTS_DIR}")
    logger.info(f"📊 Logs directory: {settings.LOGS_DIR}")
    logger.info("-" * 80)
    logger.info(f"⚙️  Workflow A enabled: {settings.ENABLE_WORKFLOW_A}")
    logger.info(f"⚙️  Workflow B enabled: {settings.ENABLE_WORKFLOW_B}")
    logger.info(f"⚙️  KROS matching: {settings.ENABLE_KROS_MATCHING}")
    logger.info("-" * 80)
    
    # Load Knowledge Base
    try:
        from app.core.kb_loader import kb_loader
        kb_loader.load()
        logger.info(f"✅ Knowledge Base loaded: {len(kb_loader.data)} categories")
        
        # Log each category
        for category, (data, metadata) in kb_loader.data.items():
            if isinstance(data, list):
                logger.info(f"   - {category}: {len(data)} items")
            else:
                logger.info(f"   - {category}: loaded")
                
    except Exception as e:
        logger.error(f"⚠️  KB loading failed: {str(e)}")
    
    logger.info("=" * 80)
    logger.info("✅ System ready!")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("🛑 Czech Building Audit System shutting down...")


# REMOVED: Duplicate root endpoint
# The root endpoint is now handled by routes.py
# This prevents the "Duplicate Operation ID" warning


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
