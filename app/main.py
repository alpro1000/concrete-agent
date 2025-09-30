"""
Main application entry point for Concrete Intelligence System
Production-ready version with proper error handling and configuration
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.router_registry import router_registry
from app.core.app_factory import setup_core_endpoints

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base exception for application errors"""
    pass


class DependencyCheckError(ApplicationError):
    """Raised when dependency check fails"""
    pass


def check_dependencies() -> None:
    """
    Check all necessary dependencies for the application.
    
    Raises:
        DependencyCheckError: If any dependency check fails
    """
    logger.info("Checking application dependencies...")
    
    try:
        # Check environment variables
        settings = get_settings()
        required_vars = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY']
        missing_vars = [var for var in required_vars if not getattr(settings, var.lower(), None)]
        
        if missing_vars:
            logger.warning(f"Missing optional API keys: {', '.join(missing_vars)}")
        
        # Check file system permissions
        import os
        upload_dir = getattr(settings, 'upload_dir', './uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
            logger.info(f"Created upload directory: {upload_dir}")
        
        # Check write permissions
        if not os.access(upload_dir, os.W_OK):
            raise DependencyCheckError(f"No write permission for upload directory: {upload_dir}")
        
        logger.info("All critical dependencies satisfied")
        
    except Exception as e:
        logger.error(f"Dependency check failed: {e}")
        raise DependencyCheckError(f"Failed to verify dependencies: {str(e)}") from e


def setup_routers(app: FastAPI) -> None:
    """
    Automatically discover and register routers with the application.
    
    Args:
        app: FastAPI application instance
        
    Raises:
        ApplicationError: If router registration fails critically
    """
    logger.info("Discovering and registering routers...")
    
    try:
        routers = router_registry.discover_routers()
        logger.info(f"Found {len(routers)} router(s)")
        
        registered_count = 0
        failed_routers = []
        
        for router_info in routers:
            try:
                app.include_router(
                    router_info['router'],
                    prefix=router_info.get('prefix', ''),
                    tags=router_info.get('tags', [router_info['name']])
                )
                logger.info(
                    f"Registered router '{router_info['name']}' "
                    f"with {router_info['routes_count']} endpoint(s)"
                )
                registered_count += 1
                
            except Exception as e:
                logger.error(f"Failed to register router '{router_info['name']}': {e}")
                failed_routers.append(router_info['name'])
        
        if failed_routers:
            logger.warning(f"Failed to register {len(failed_routers)} router(s): {', '.join(failed_routers)}")
        
        if registered_count == 0:
            raise ApplicationError("No routers were registered successfully")
        
        logger.info(f"Successfully registered {registered_count}/{len(routers)} router(s)")
        
    except Exception as e:
        logger.error(f"Router setup failed: {e}")
        raise ApplicationError(f"Failed to setup routers: {str(e)}") from e


def setup_middleware(app: FastAPI) -> None:
    """
    Configure middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    settings = get_settings()
    
    # CORS configuration
    allowed_origins = getattr(settings, 'allowed_origins', ['*'])
    
    if '*' in allowed_origins:
        logger.warning(
            "CORS configured with wildcard origin (*). "
            "This is not recommended for production. "
            "Set ALLOWED_ORIGINS environment variable."
        )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    logger.info(f"CORS configured with origins: {allowed_origins}")


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Configure global exception handlers.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url)
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "details": exc.errors(),
                "body": exc.body
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc) if get_settings().debug else "An unexpected error occurred"
            }
        )
    
    logger.info("Exception handlers configured")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Application startup: Initializing resources...")
    try:
        check_dependencies()
        logger.info("Application startup complete")
        yield
    finally:
        # Shutdown
        logger.info("Application shutdown: Cleaning up resources...")
        # Add cleanup logic here (close DB connections, etc.)
        logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
        
    Raises:
        ApplicationError: If application creation fails
    """
    logger.info("Creating FastAPI application...")
    
    try:
        settings = get_settings()
        
        app = FastAPI(
            title="Concrete Intelligence System",
            description="""
            Advanced system for analyzing construction documentation.
            
            **Features:**
            - Automatic router registration
            - Dynamic agent integration
            - Multi-LLM support (GPT, Claude, Perplexity)
            - Czech construction standards compliance
            
            **Supported Standards:**
            - Concrete: ČSN EN 206+A2
            - Steel: ČSN EN 10025
            - Thermal Engineering: ČSN 73 0540
            """,
            version="3.0.0",
            lifespan=lifespan,
            docs_url="/docs" if settings.debug else None,
            redoc_url="/redoc" if settings.debug else None,
            openapi_url="/openapi.json" if settings.debug else None,
        )
        
        # Setup middleware
        setup_middleware(app)
        
        # Setup exception handlers
        setup_exception_handlers(app)
        
        # Setup routers
        setup_routers(app)
        
        # Setup core endpoints (health, static files, etc.)
        setup_core_endpoints(app)
        
        logger.info("FastAPI application created successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create application: {e}", exc_info=True)
        raise ApplicationError(f"Application creation failed: {str(e)}") from e


# Application instance
app = create_app()


# Entry point for direct execution
if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    logger.info("Starting Concrete Intelligence System...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Environment: {getattr(settings, 'environment', 'development')}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=getattr(settings, 'port', 8000),
        reload=settings.debug,
        log_level="info"
    )
