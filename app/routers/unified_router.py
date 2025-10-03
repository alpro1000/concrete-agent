"""
Unified Analysis Router - handles all three upload panels in one endpoint
This router uses the orchestrator to dynamically route files to appropriate agents

Supports multipart/form-data with both old and new field names for compatibility:
- technical_files or project_documentation (List[UploadFile])
- quantities_files or budget_estimate (List[UploadFile])
- drawings_files or drawings (List[UploadFile])
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from typing import List, Optional
import os
import logging
from datetime import datetime

from app.services.validation import validate_files
from app.services.storage import save_files, create_analysis_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analysis", tags=["unified"])

# Import orchestrator for file processing
try:
    from app.core.orchestrator import OrchestratorService
    orchestrator = OrchestratorService()
    ORCHESTRATOR_AVAILABLE = True
    logger.info("Orchestrator service initialized successfully")
except Exception as e:
    ORCHESTRATOR_AVAILABLE = False
    logger.warning(f"Orchestrator not available: {e}")


def get_user_id_from_token(authorization: Optional[str]) -> int:
    """
    Extract user_id from Bearer token (mock implementation)
    
    Args:
        authorization: Authorization header value
        
    Returns:
        User ID (1 for valid token, 0 otherwise)
    """
    if not authorization:
        return 0
    
    token = authorization.replace("Bearer ", "")
    if token == "mock_jwt_token_12345":
        return 1
    
    return 0


@router.post("/unified")
async def analyze_files(
    # New field names (primary)
    technical_files: Optional[List[UploadFile]] = File(None),
    quantities_files: Optional[List[UploadFile]] = File(None),
    drawings_files: Optional[List[UploadFile]] = File(None),
    # Old field names (compatibility)
    project_documentation: Optional[List[UploadFile]] = File(None),
    budget_estimate: Optional[List[UploadFile]] = File(None),
    drawings: Optional[List[UploadFile]] = File(None),
    # Authorization header
    authorization: Optional[str] = Header(None)
):
    """
    Unified endpoint for file analysis with multipart/form-data
    
    Accepts both sets of field names for compatibility:
    - technical_files or project_documentation (List[UploadFile])
    - quantities_files or budget_estimate (List[UploadFile])
    - drawings_files or drawings (List[UploadFile])
    
    Returns:
        analysis_id: UUID for this analysis
        status: 'processing'
        files: Dictionary with technical_files, quantities_files, drawings_files arrays
    """
    # Get user ID from token (1 for valid token, 0 otherwise)
    user_id = get_user_id_from_token(authorization)
    
    # Generate analysis ID
    analysis_id = create_analysis_id()
    
    # Merge old and new field names (prefer new names if both provided)
    tech_files = technical_files or project_documentation
    quant_files = quantities_files or budget_estimate
    draw_files = drawings_files or drawings
    
    # Check if any files uploaded
    if not any([tech_files, quant_files, draw_files]):
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    logger.info(
        f"Analysis {analysis_id}: user={user_id}, "
        f"technical={len(tech_files or [])}, "
        f"quantities={len(quant_files or [])}, "
        f"drawings={len(draw_files or [])}"
    )
    
    # Validate and save files
    saved_files = {
        "technical_files": [],
        "quantities_files": [],
        "drawings_files": []
    }
    
    try:
        # Validate technical files
        if tech_files:
            await validate_files(tech_files, "technical")
            saved = await save_files(tech_files, user_id, analysis_id, "technical")
            saved_files["technical_files"] = [
                {
                    "filename": f["saved_filename"],
                    "original_filename": f["original_filename"],
                    "size": f["size"]
                }
                for f in saved
            ]
        
        # Validate quantities files
        if quant_files:
            await validate_files(quant_files, "quantities")
            saved = await save_files(quant_files, user_id, analysis_id, "quantities")
            saved_files["quantities_files"] = [
                {
                    "filename": f["saved_filename"],
                    "original_filename": f["original_filename"],
                    "size": f["size"]
                }
                for f in saved
            ]
        
        # Validate drawings files
        if draw_files:
            await validate_files(draw_files, "drawings")
            saved = await save_files(draw_files, user_id, analysis_id, "drawings")
            saved_files["drawings_files"] = [
                {
                    "filename": f["saved_filename"],
                    "original_filename": f["original_filename"],
                    "size": f["size"]
                }
                for f in saved
            ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing files: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Error processing files: {str(e)}"
        )
    
    # Return response
    response = {
        "analysis_id": analysis_id,
        "status": "processing",
        "files": saved_files
    }
    
    logger.info(f"Analysis {analysis_id} created successfully")
    return response
