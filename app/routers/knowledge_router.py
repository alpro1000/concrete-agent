"""
Knowledge Base API Router
Provides access to standards, materials, and labor norms
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("/")
async def knowledge_root():
    """Knowledge base API information"""
    return {
        "service": "Knowledge Base API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/v1/knowledge/search",
            "standards": "/api/v1/knowledge/standards",
            "materials": "/api/v1/knowledge/materials",
            "codes": "/api/v1/knowledge/codes"
        }
    }


@router.get("/search")
async def search_knowledge(
    query: str = Query(..., description="Search query"),
    type: Optional[str] = Query(None, description="Type: standards/materials/codes/all")
):
    """
    Search the knowledge base
    
    - **query**: Search query string
    - **type**: Optional filter by type (standards/materials/codes/all)
    """
    try:
        from app.agents.knowledge_base import KnowledgeBaseAgent
        
        agent = KnowledgeBaseAgent()
        result = await agent.analyze({
            "query": query,
            "type": type or "all"
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/standards")
async def get_standards(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get all standards, optionally filtered by category
    
    - **category**: Optional category filter (concrete/foundations/thermal/etc.)
    """
    try:
        from app.agents.knowledge_base import KnowledgeBaseAgent
        
        agent = KnowledgeBaseAgent()
        query = category if category else ""
        result = await agent.analyze({
            "query": query,
            "type": "standards"
        })
        
        return {
            "standards": result.get("results", {}).get("standards", []),
            "total": len(result.get("results", {}).get("standards", []))
        }
        
    except Exception as e:
        logger.error(f"Get standards failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/materials")
async def get_materials(
    material_type: Optional[str] = Query(None, description="Filter by material type")
):
    """
    Get all materials, optionally filtered by type
    
    - **material_type**: Optional type filter (concrete/steel/masonry/etc.)
    """
    try:
        from app.agents.knowledge_base import KnowledgeBaseAgent
        
        agent = KnowledgeBaseAgent()
        query = material_type if material_type else ""
        result = await agent.analyze({
            "query": query,
            "type": "materials"
        })
        
        return {
            "materials": result.get("results", {}).get("materials", []),
            "total": len(result.get("results", {}).get("materials", []))
        }
        
    except Exception as e:
        logger.error(f"Get materials failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/codes")
async def get_codes(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get KROS/URS budget codes, optionally filtered by category
    
    - **category**: Optional category filter (earthworks/foundations/etc.)
    """
    try:
        from app.agents.knowledge_base import KnowledgeBaseAgent
        
        agent = KnowledgeBaseAgent()
        query = category if category else ""
        result = await agent.analyze({
            "query": query,
            "type": "codes"
        })
        
        return {
            "codes": result.get("results", {}).get("codes", []),
            "total": len(result.get("results", {}).get("codes", []))
        }
        
    except Exception as e:
        logger.error(f"Get codes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
