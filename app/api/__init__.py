"""
API Package initialization
Správné propojení všech routerů
"""
from fastapi import APIRouter

# Import všech routerů
from app.api.routes import router as main_router
from app.api.routes_workflow_a import router as workflow_a_router
from app.api.routes_workflow_b import router as workflow_b_router
from app.api.routes_chat import router as chat_router
from app.api.pdf_extraction_routes import router as pdf_router

# Vytvoření hlavního API routeru
api_router = APIRouter()

# Připojení všech routerů
api_router.include_router(main_router)
api_router.include_router(workflow_a_router)
api_router.include_router(workflow_b_router)
api_router.include_router(chat_router)
api_router.include_router(pdf_router)

__all__ = ["api_router"]
