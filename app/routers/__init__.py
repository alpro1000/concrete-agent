"""
Routers package initialization.

All imports use full package paths (app.*) for proper module resolution.
"""

from app.routers import unified_router, status_router, auth_router

__all__ = [
    "unified_router",
    "status_router",
    "auth_router"
]
