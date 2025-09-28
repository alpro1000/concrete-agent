# app/routers/corrections.py
"""
Correction management endpoints for self-learning
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models import Extraction, Correction
from app.services import LearningService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class CorrectionCreate(BaseModel):
    """Correction creation schema"""
    user_feedback: str
    corrected_data: Dict[str, Any]


class CorrectionResponse(BaseModel):
    """Correction response schema"""
    id: str
    extraction_id: str
    user_feedback: str
    corrected_data: Dict[str, Any]
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/extractions/{extraction_id}/correction", response_model=CorrectionResponse)
async def save_correction(
    extraction_id: str,
    correction_data: CorrectionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Save user correction for self-learning"""
    try:
        # Verify extraction exists
        extraction_query = select(Extraction).where(Extraction.id == extraction_id)
        extraction_result = await db.execute(extraction_query)
        extraction = extraction_result.scalar_one_or_none()
        
        if not extraction:
            raise HTTPException(status_code=404, detail="Extraction not found")
        
        # Save correction using learning service
        correction = await LearningService.save_correction(
            db=db,
            extraction_id=extraction_id,
            user_feedback=correction_data.user_feedback,
            corrected_data=correction_data.corrected_data
        )
        
        logger.info(f"✅ Saved correction for extraction {extraction_id}")
        
        return CorrectionResponse(
            id=str(correction.id),
            extraction_id=str(correction.extraction_id),
            user_feedback=correction.user_feedback,
            corrected_data=correction.corrected_data,
            created_at=correction.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error saving correction: {e}")
        raise HTTPException(status_code=500, detail="Failed to save correction")


@router.get("/extractions/{extraction_id}/corrections", response_model=List[CorrectionResponse])
async def list_corrections(
    extraction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List corrections for an extraction"""
    try:
        # Verify extraction exists
        extraction_query = select(Extraction).where(Extraction.id == extraction_id)
        extraction_result = await db.execute(extraction_query)
        extraction = extraction_result.scalar_one_or_none()
        
        if not extraction:
            raise HTTPException(status_code=404, detail="Extraction not found")
        
        # Get corrections
        corrections_query = (
            select(Correction)
            .where(Correction.extraction_id == extraction_id)
            .order_by(Correction.created_at.desc())
        )
        
        result = await db.execute(corrections_query)
        corrections = result.scalars().all()
        
        return [
            CorrectionResponse(
                id=str(correction.id),
                extraction_id=str(correction.extraction_id),
                user_feedback=correction.user_feedback,
                corrected_data=correction.corrected_data,
                created_at=correction.created_at.isoformat()
            )
            for correction in corrections
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing corrections: {e}")
        raise HTTPException(status_code=500, detail="Failed to list corrections")


@router.get("/corrections/{correction_id}", response_model=CorrectionResponse)
async def get_correction(
    correction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get correction details"""
    try:
        query = select(Correction).where(Correction.id == correction_id)
        result = await db.execute(query)
        correction = result.scalar_one_or_none()
        
        if not correction:
            raise HTTPException(status_code=404, detail="Correction not found")
        
        return CorrectionResponse(
            id=str(correction.id),
            extraction_id=str(correction.extraction_id),
            user_feedback=correction.user_feedback,
            corrected_data=correction.corrected_data,
            created_at=correction.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting correction: {e}")
        raise HTTPException(status_code=500, detail="Failed to get correction")


@router.get("/learning/stats/{agent_name}")
async def get_learning_stats(
    agent_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get learning statistics for an agent"""
    try:
        stats = await LearningService.get_correction_stats(db, agent_name)
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error getting learning stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get learning stats")