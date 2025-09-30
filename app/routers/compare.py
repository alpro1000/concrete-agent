# app/routers/compare.py
"""
Document comparison endpoints using diff service
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Document, Extraction, Folder
from app.services import DiffService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
diff_service = DiffService()


@router.get("/projects/{project_id}/compare")
async def compare_documents(
    project_id: str,
    doc1: str = Query(..., description="First document ID"),
    doc2: str = Query(..., description="Second document ID"),
    agent: str = Query(None, description="Filter by specific agent"),
    db: AsyncSession = Depends(get_db)
):
    """Compare two document versions or their extractions"""
    try:
        # Get both documents and verify they belong to the project
        doc1_data = await _get_document_extractions(db, project_id, doc1, agent)
        doc2_data = await _get_document_extractions(db, project_id, doc2, agent)
        
        # Perform comparison
        comparison_result = diff_service.compare_documents(doc1_data, doc2_data)
        
        # Add document context
        comparison_result["comparison_context"] = {
            "project_id": project_id,
            "document1_id": doc1,
            "document2_id": doc2,  
            "agent_filter": agent
        }
        
        logger.info(f"✅ Compared documents {doc1} vs {doc2} in project {project_id}")
        
        return comparison_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error comparing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare documents")


@router.get("/projects/{project_id}/compare/concrete")
async def compare_concrete_analysis(
    project_id: str,
    doc1: str = Query(..., description="First document ID"),
    doc2: str = Query(..., description="Second document ID"),
    db: AsyncSession = Depends(get_db)
):
    """Compare concrete analysis results between two documents"""
    try:
        # Get concrete-specific extractions
        doc1_data = await _get_document_extractions(db, project_id, doc1, "ConcreteAgent")
        doc2_data = await _get_document_extractions(db, project_id, doc2, "ConcreteAgent")
        
        # Perform general comparison
        comparison_result = diff_service.compare_documents(doc1_data, doc2_data)
        
        # Extract concrete-specific changes
        concrete_changes = diff_service.extract_concrete_changes(comparison_result["details"])
        
        result = {
            "general_comparison": comparison_result,
            "concrete_specific": concrete_changes,
            "summary": diff_service.generate_diff_summary(comparison_result["details"])
        }
        
        logger.info(f"✅ Compared concrete analysis {doc1} vs {doc2}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error comparing concrete analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare concrete analysis")


@router.get("/extractions/{extraction1_id}/compare/{extraction2_id}")
async def compare_extractions(
    extraction1_id: str,
    extraction2_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Compare two specific extractions directly"""
    try:
        # Get both extractions
        extraction1 = await _get_extraction(db, extraction1_id)
        extraction2 = await _get_extraction(db, extraction2_id)
        
        # Perform comparison
        comparison_result = diff_service.deep_diff(extraction1.data, extraction2.data)
        
        result = {
            "extraction1": {
                "id": str(extraction1.id),
                "agent": extraction1.agent,
                "confidence": extraction1.confidence,
                "created_at": extraction1.created_at.isoformat()
            },
            "extraction2": {
                "id": str(extraction2.id),
                "agent": extraction2.agent,
                "confidence": extraction2.confidence,
                "created_at": extraction2.created_at.isoformat()
            },
            "comparison": comparison_result,
            "summary": diff_service.generate_diff_summary(comparison_result)
        }
        
        logger.info(f"✅ Compared extractions {extraction1_id} vs {extraction2_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error comparing extractions: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare extractions")


async def _get_document_extractions(
    db: AsyncSession, 
    project_id: str, 
    doc_id: str, 
    agent_filter: str = None
) -> Dict[str, Any]:
    """Get document extractions data for comparison"""
    
    # Verify document belongs to project
    doc_query = (
        select(Document)
        .join(Folder)
        .where(
            Document.id == doc_id,
            Folder.project_id == project_id
        )
    )
    
    doc_result = await db.execute(doc_query)
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in project")
    
    # Get extractions
    extractions_query = select(Extraction).where(Extraction.document_id == document.id)
    
    if agent_filter:
        extractions_query = extractions_query.where(Extraction.agent == agent_filter)
    
    extractions_result = await db.execute(extractions_query)
    extractions = extractions_result.scalars().all()
    
    # Combine extraction data
    combined_data = {
        "document_id": str(document.id),
        "filename": document.filename,
        "extractions": {}
    }
    
    for extraction in extractions:
        combined_data["extractions"][extraction.agent] = {
            "data": extraction.data,
            "confidence": extraction.confidence,
            "created_at": extraction.created_at.isoformat()
        }
    
    return combined_data


async def _get_extraction(db: AsyncSession, extraction_id: str) -> Extraction:
    """Helper to get extraction by ID"""
    query = select(Extraction).where(Extraction.id == extraction_id)
    result = await db.execute(query)
    extraction = result.scalar_one_or_none()
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    return extraction
