"""
App Factory - Responsible for setting up core endpoints and application lifecycle.
"""

import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_core_endpoints(app: FastAPI):
    """
    Set up core endpoints for the application.
    """
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Root endpoint providing basic information."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Concrete Intelligence System</title>
        </head>
        <body>
            <h1>🧠 Welcome to the Concrete Intelligence System</h1>
            <p>Use <a href="/docs">API Documentation</a> to explore available endpoints.</p>
        </body>
        </html>
        """

    @app.get("/health", response_class=JSONResponse)
    async def health_check():
        """Health check endpoint."""
        return {
            "service": "Concrete Intelligence System",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
        }

    @app.get("/minio/health/live", response_class=JSONResponse)
    async def minio_health_live():
        """MinIO-compatible health check endpoint for keepalive."""
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
        }

    logger.info("✅ Core endpoints set up successfully.")
