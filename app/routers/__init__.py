# app/routers/__init__.py
from .tzd_router import router as tzd_router
from .unified_router import router as unified_router
from .user_router import router as user_router
from .results_router import router as results_router

__all__ = [
    "tzd_router",
    "unified_router",
    "user_router",
    "results_router",
]