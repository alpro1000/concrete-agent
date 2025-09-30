# app/routers/extractions.py
"""
Extraction management endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models import Document, Extraction, Folder
from app.services import LearningService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ExtractionCreate(BaseModel):
    """Extraction creation schema"""
    agent: str
    data: Dict[str, Any]
    confidence: Optional[float] = None


class ExtractionResponse(BaseModel):
    """Extraction response schema"""
    id: str
    document_id: str
    agent: str
    data: Dict[str, Any]
    confidence: Optional[float]
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/projects/{project_id}/documents/{doc_id}/extract", response_model=ExtractionResponse)
async def run_extraction(
    project_id: str,
    doc_id: str,
    extraction_data: ExtractionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Run extraction on a document manually"""
    try:
        # Verify document exists and belongs to project
        document = await _get_document_in_project(db, project_id, doc_id)
        
        # Apply learning corrections
        corrected_data = await LearningService.apply_corrections(
            db, extraction_data.agent, extraction_data.data
        )
        
        # Create extraction record
        extraction = Extraction(
            document_id=document.id,
            agent=extraction_data.agent,
            data=corrected_data,
            confidence=extraction_data.confidence
        )
        
        db.add(extraction)
        await db.commit()
        await db.refresh(extraction)
        
        logger.info(f"✅ Created extraction: {extraction.agent} for document {doc_id}")
        
        return ExtractionResponse(
            id=str(extraction.id),
            document_id=str(extraction.document_id),
            agent=extraction.agent,
            data=extraction.data,
            confidence=extraction.confidence,
            created_at=extraction.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating extraction: {e}")
        raise HTTPException(status_code=500, detail="Failed to create extraction")


@router.get("/projects/{project_id}/documents/{doc_id}/extractions", response_model=List[ExtractionResponse])
async def list_extractions(
    project_id: str,
    doc_id: str,
    agent: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List extractions for a document"""
    try:
        # Verify document exists and belongs to project
        document = await _get_document_in_project(db, project_id, doc_id)
        
        # Build query
        query = select(Extraction).where(Extraction.document_id == document.id)
        
        if agent:
            query = query.where(Extraction.agent == agent)
        
        query = query.order_by(Extraction.created_at.desc())
        
        result = await db.execute(query)
        extractions = result.scalars().all()
        
        return [
            ExtractionResponse(
                id=str(extraction.id),
                document_id=str(extraction.document_id),
                agent=extraction.agent,
                data=extraction.data,
                confidence=extraction.confidence,
                created_at=extraction.created_at.isoformat()
            )
            for extraction in extractions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing extractions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list extractions")


@router.get("/extractions/{extraction_id}", response_model=ExtractionResponse)
async def get_extraction(
    extraction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get extraction details"""
    try:
        query = select(Extraction).where(Extraction.id == extraction_id)
        result = await db.execute(query)
        extraction = result.scalar_one_or_none()
        
        if not extraction:
            raise HTTPException(status_code=404, detail="Extraction not found")
        
        return ExtractionResponse(
            id=str(extraction.id),
            document_id=str(extraction.document_id),
            agent=extraction.agent,
            data=extraction.data,
            confidence=extraction.confidence,
            created_at=extraction.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting extraction: {e}")
        raise HTTPException(status_code=500, detail="Failed to get extraction")


async def _get_document_in_project(db: AsyncSession, project_id: str, doc_id: str) -> Document:
    """Helper to get document and verify it belongs to project"""
    query = (
        select(Document)
        .join(Folder)
        .where(
            Document.id == doc_id,
            Folder.project_id == project_id
        )
    )
    
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found in project")
    
    return document
