# app/services/learning.py
"""
Self-learning correction service
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Extraction, Correction
import logging

logger = logging.getLogger(__name__)


class LearningService:
    """Service for applying user corrections to improve future extractions"""
    
    @staticmethod
    async def apply_corrections(
        db: AsyncSession,
        agent_name: str,
        extraction_data: Dict[str, Any],
        document_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply learned corrections to new extraction data"""
        
        try:
            # Find relevant corrections for this agent
            corrections = await LearningService._get_relevant_corrections(
                db, agent_name, extraction_data, document_context
            )
            
            if not corrections:
                logger.debug(f"No corrections found for agent {agent_name}")
                return extraction_data
            
            # Apply corrections
            corrected_data = extraction_data.copy()
            applied_corrections = []
            
            for correction in corrections:
                correction_applied = LearningService._apply_single_correction(
                    corrected_data, correction.corrected_data, correction.user_feedback
                )
                
                if correction_applied:
                    applied_corrections.append({
                        "correction_id": str(correction.id),
                        "feedback": correction.user_feedback,
                        "confidence_boost": 0.1  # Small confidence boost for corrected values
                    })
            
            # Add metadata about applied corrections
            if applied_corrections:
                corrected_data["_corrections_applied"] = applied_corrections
                corrected_data["_learning_version"] = "1.0"
                logger.info(f"Applied {len(applied_corrections)} corrections to {agent_name} extraction")
            
            return corrected_data
            
        except Exception as e:
            logger.error(f"Error applying corrections: {e}")
            return extraction_data  # Return original data on error
    
    @staticmethod
    async def _get_relevant_corrections(
        db: AsyncSession,
        agent_name: str,
        extraction_data: Dict[str, Any],
        document_context: Optional[str] = None
    ) -> List[Correction]:
        """Find corrections relevant to current extraction"""
        
        # Query corrections for the same agent
        query = (
            select(Correction)
            .join(Extraction)
            .where(Extraction.agent == agent_name)
            .order_by(Correction.created_at.desc())
            .limit(50)  # Limit to recent corrections
        )
        
        result = await db.execute(query)
        corrections = result.scalars().all()
        
        # Filter corrections based on content similarity
        relevant_corrections = []
        
        for correction in corrections:
            if LearningService._is_correction_relevant(
                extraction_data, correction.corrected_data, correction.user_feedback
            ):
                relevant_corrections.append(correction)
        
        return relevant_corrections
    
    @staticmethod
    def _is_correction_relevant(
        current_data: Dict[str, Any],
        correction_data: Dict[str, Any],
        feedback: Optional[str] = None
    ) -> bool:
        """Determine if a correction is relevant to current data"""
        
        # Simple relevance check based on common keys and values
        current_keys = set(current_data.keys())
        correction_keys = set(correction_data.keys())
        
        # Check for common keys
        common_keys = current_keys & correction_keys
        if len(common_keys) < 1:
            return False
        
        # Check for similar values in common keys
        similarity_score = 0
        for key in common_keys:
            if key in current_data and key in correction_data:
                current_val = str(current_data[key]).lower()
                correction_val = str(correction_data[key]).lower()
                
                # Simple string similarity
                if current_val == correction_val:
                    similarity_score += 2
                elif current_val in correction_val or correction_val in current_val:
                    similarity_score += 1
        
        # Consider relevant if similarity score is high enough
        return similarity_score >= 2
    
    @staticmethod
    def _apply_single_correction(
        data: Dict[str, Any],
        correction: Dict[str, Any],
        feedback: Optional[str] = None
    ) -> bool:
        """Apply a single correction to the data"""
        
        applied = False
        
        for key, corrected_value in correction.items():
            if key.startswith("_"):  # Skip metadata keys
                continue
                
            if key in data:
                original_value = data[key]
                
                # Apply correction based on type and context
                if LearningService._should_apply_correction(original_value, corrected_value, feedback):
                    data[key] = corrected_value
                    applied = True
                    logger.debug(f"Applied correction: {key} = {corrected_value} (was {original_value})")
        
        return applied
    
    @staticmethod
    def _should_apply_correction(
        original_value: Any,
        corrected_value: Any,
        feedback: Optional[str] = None
    ) -> bool:
        """Determine if a specific correction should be applied"""
        
        # Don't apply if values are already the same
        if original_value == corrected_value:
            return False
        
        # Apply correction for concrete grades (common use case)
        if isinstance(original_value, str) and isinstance(corrected_value, str):
            # Check for concrete grade patterns
            if any(pattern in original_value.upper() for pattern in ["C20", "C25", "C30", "C35", "C40"]):
                return True
        
        # Apply correction for numerical values with reasonable bounds
        if isinstance(original_value, (int, float)) and isinstance(corrected_value, (int, float)):
            # Apply if correction is within reasonable range (not more than 50% change)
            if original_value != 0:
                change_ratio = abs(corrected_value - original_value) / abs(original_value)
                return change_ratio <= 0.5
        
        # Apply correction for lists/arrays
        if isinstance(original_value, list) and isinstance(corrected_value, list):
            return True
        
        return False
    
    @staticmethod
    async def save_correction(
        db: AsyncSession,
        extraction_id: str,
        user_feedback: str,
        corrected_data: Dict[str, Any]
    ) -> Correction:
        """Save a user correction to the database"""
        
        correction = Correction(
            extraction_id=extraction_id,
            user_feedback=user_feedback,
            corrected_data=corrected_data
        )
        
        db.add(correction)
        await db.commit()
        await db.refresh(correction)
        
        logger.info(f"Saved correction for extraction {extraction_id}")
        return correction
    
    @staticmethod
    async def get_correction_stats(db: AsyncSession, agent_name: str) -> Dict[str, Any]:
        """Get statistics about corrections for an agent"""
        
        query = (
            select(Correction)
            .join(Extraction)
            .where(Extraction.agent == agent_name)
        )
        
        result = await db.execute(query)
        corrections = result.scalars().all()
        
        from datetime import datetime
        
        return {
            "total_corrections": len(corrections),
            "recent_corrections": len([c for c in corrections if (
                c.created_at.timestamp() > (datetime.utcnow().timestamp() - 7*24*3600)
            )]),
            "agent": agent_name
        }