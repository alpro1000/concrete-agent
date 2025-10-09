"""
API Package initialization
Správné propojení všech routerů
"""
from fastapi import APIRouter

# Import všech routerů
from app.api.routes import router as main_router
from app.api.routes_workflow_a import router as workflow_a_router
from app.api.routes_workflow_b import router as workflow_b_router

# Vytvoření hlavního API routeru
api_router = APIRouter()

# Připojení všech routerů
api_router.include_router(main_router)
api_router.include_router(workflow_a_router)
api_router.include_router(workflow_b_router)

__all__ = ["api_router"]
