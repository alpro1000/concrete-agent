# app/routers/__init__.py
from .projects import router as projects_router
from .documents import router as documents_router
from .extractions import router as extractions_router
from .corrections import router as corrections_router
from .compare import router as compare_router
from .upload import router as upload_router
from .project import router as project_router

__all__ = [
    "projects_router",
    "documents_router", 
    "extractions_router",
    "corrections_router",
    "compare_router",
    "upload_router",
    "project_router"
]