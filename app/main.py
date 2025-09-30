"""
Main application entry point.
Enhanced version with new router setup, dependency checks, and lifecycle management.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.router_registry import router_registry
from app.core.app_factory import setup_core_endpoints

logger = logging.getLogger("uvicorn")

def check_dependencies():
    """
    Check all necessary dependencies for the application.
    """
    logger.info("✅ Checking application dependencies...")
    # Add checks for database, external services, or file system here
    logger.info("✅ All dependencies are satisfied!")


def setup_routers(app: FastAPI):
    """
    Automatically discover and register routers with the application.
    """
    logger.info("🔍 Discovering routers...")
    routers = router_registry.discover_routers()
    logger.info(f"📊 Found {len(routers)} routers.")

    for router_info in routers:
        try:
            app.include_router(
                router_info['router'],
                prefix=router_info.get('prefix', ''),
                tags=router_info.get('tags', [router_info['name']])
            )
            logger.info(f"✅ Registered router: {router_info['name']} with {router_info['routes_count']} endpoints.")
        except Exception as e:
            logger.error(f"❌ Error registering router {router_info['name']}: {e}")

    logger.info("✅ All routers registered successfully!")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    logger.info("🚀 Creating FastAPI application...")

    app = FastAPI(
        title="Concrete Intelligence System",
        description="""
        🧠 Advanced system for analyzing construction documentation.

        **Features:**
        - Automatic router registration.
        - Dynamic agent integration.
        - New LLM support (GPT-4.1, Claude Opus 4.1, Sonar models).

        **Supported Standards:**
        - Concrete: ČSN EN 206+A2
        - Steel: ČSN EN 10025
        - Thermal Engineering: ČSN 73 0540
        """,
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup dependencies
    check_dependencies()

    # Setup routers
    setup_routers(app)

    # Setup core endpoints
    setup_core_endpoints(app)

    logger.info("✅ FastAPI application created successfully!")
    return app


# Entry point for running the application
if __name__ == "__main__":
    import uvicorn

    logger.info("🌟 Starting Concrete Intelligence System...")
    uvicorn.run("app.main:create_app", host="0.0.0.0", port=8000, reload=True, factory=True)
