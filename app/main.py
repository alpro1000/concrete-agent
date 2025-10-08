"""
Czech Building Audit System - Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from datetime import datetime
import os
from pathlib import Path

# Import configuration
from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title="Czech Building Audit System",
    description="AI-powered building audit and cost calculation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
if settings.WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(settings.WEB_DIR)), name="web")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Czech Building Audit System",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and deployment verification
    """
    # Check critical components
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "checks": {
            "api": "ok",
            "configuration": "ok",
        }
    }
    
    # Check if API keys are configured
    if not settings.ANTHROPIC_API_KEY:
        health_status["checks"]["anthropic_api"] = "not_configured"
        health_status["status"] = "degraded"
    else:
        health_status["checks"]["anthropic_api"] = "configured"
    
    if settings.OPENAI_API_KEY:
        health_status["checks"]["openai_api"] = "configured"
    else:
        health_status["checks"]["openai_api"] = "not_configured"
    
    # Check if directories exist
    try:
        health_status["checks"]["data_dir"] = "ok" if settings.DATA_DIR.exists() else "missing"
        health_status["checks"]["kb_dir"] = "ok" if settings.KB_DIR.exists() else "missing"
        health_status["checks"]["logs_dir"] = "ok" if settings.LOGS_DIR.exists() else "missing"
    except Exception as e:
        health_status["checks"]["directories"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check feature flags
    health_status["features"] = {
        "workflow_a": settings.ENABLE_WORKFLOW_A,
        "workflow_b": settings.ENABLE_WORKFLOW_B,
        "kros_matching": settings.ENABLE_KROS_MATCHING,
        "rts_matching": settings.ENABLE_RTS_MATCHING,
        "resource_calculation": settings.ENABLE_RESOURCE_CALCULATION,
    }
    
    return health_status


@app.get("/status")
async def status():
    """
    Detailed status information
    """
    return {
        "service": "Czech Building Audit System",
        "version": "1.0.0",
        "uptime": "running",
        "environment": settings.ENVIRONMENT,
        "configuration": {
            "claude_model": settings.CLAUDE_MODEL,
            "gpt4_model": settings.GPT4_MODEL,
            "audit_green_threshold": settings.AUDIT_GREEN_THRESHOLD,
            "audit_amber_threshold": settings.AUDIT_AMBER_THRESHOLD,
        },
        "features": {
            "workflow_a": settings.ENABLE_WORKFLOW_A,
            "workflow_b": settings.ENABLE_WORKFLOW_B,
            "kros_matching": settings.ENABLE_KROS_MATCHING,
            "rts_matching": settings.ENABLE_RTS_MATCHING,
            "resource_calculation": settings.ENABLE_RESOURCE_CALCULATION,
            "multi_role": settings.multi_role.enabled,
        },
        "paths": {
            "data_dir": str(settings.DATA_DIR),
            "kb_dir": str(settings.KB_DIR),
            "logs_dir": str(settings.LOGS_DIR),
            "web_dir": str(settings.WEB_DIR),
        }
    }


# Import and include routers (when they exist)
# from app.api import routes
# app.include_router(routes.router)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
