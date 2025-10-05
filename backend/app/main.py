"""
Main FastAPI application for Concrete Agent system.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.core import (
    settings,
    init_db,
    check_db_connection,
    app_logger,
    ConcreteAgentException
)
from app.services import agent_registry
from app.core.orchestrator import orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    app_logger.info("Starting Concrete Agent application...")
    
    # Initialize database
    try:
        init_db()
        app_logger.info("Database initialized")
    except Exception as e:
        app_logger.error(f"Database initialization failed: {e}")
    
    # Discover and register agents
    agent_registry.discover_agents()
    app_logger.info(f"Discovered agents: {agent_registry.list_agents()}")
    
    yield
    
    # Shutdown
    app_logger.info("Shutting down Concrete Agent application...")


# Create FastAPI application
app = FastAPI(
    title="Concrete Agent API",
    description="Scientific-method based construction analysis system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(ConcreteAgentException)
async def concrete_agent_exception_handler(request: Request, exc: ConcreteAgentException):
    """Handle ConcreteAgent exceptions."""
    app_logger.error(f"ConcreteAgent exception: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "details": exc.details
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_status = check_db_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "version": "1.0.0",
        "environment": settings.environment
    }


# Status endpoint
@app.get("/status")
async def get_status():
    """Get system status and available agents."""
    return {
        "status": "operational",
        "agents": agent_registry.list_agents(),
        "database": "connected" if check_db_connection() else "disconnected",
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Concrete Agent API",
        "version": "1.0.0",
        "description": "Scientific-method based construction analysis system",
        "documentation": "/docs",
        "health_check": "/health",
        "status": "/status"
    }


# Import and include routers
from app.routers import unified_router, status_router

app.include_router(unified_router.router, prefix="/api/agents", tags=["agents"])
app.include_router(status_router.router, prefix="/api", tags=["status"])

# NOTE: Additional routers can be added as they are created
# from app.routers import user_router, results_router, admin_router
# app.include_router(user_router.router, prefix="/api/users", tags=["users"])
# app.include_router(results_router.router, prefix="/api/results", tags=["results"])
# app.include_router(admin_router.router, prefix="/api/admin", tags=["admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
