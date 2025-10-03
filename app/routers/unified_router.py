"""
Unified Analysis Router - handles all three upload panels in one endpoint
This router uses the orchestrator to dynamically route files to appropriate agents

Supports multipart/form-data with both old and new field names for compatibility:
- technical_files or project_documentation (List[UploadFile])
- quantities_files or budget_estimate (List[UploadFile])
- drawings_files or drawings (List[UploadFile])
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from typing import List, Optional, Dict, Any
import os
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path

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


async def process_files_background(
    user_id: int,
    analysis_id: str,
    saved_files: Dict[str, List[dict]]
):
    """
    Background task to process files with orchestrator and save results
    
    Args:
        user_id: User ID
        analysis_id: Analysis ID (UUID)
        saved_files: Dictionary of saved files with their paths
    """
    try:
        logger.info(f"Starting background processing for analysis {analysis_id}")
        
        if not ORCHESTRATOR_AVAILABLE:
            logger.warning(f"Orchestrator not available for analysis {analysis_id}")
            return
        
        # Collect all file paths from saved files
        file_paths = []
        for category in ["technical_files", "quantities_files", "drawings_files"]:
            for file_info in saved_files.get(category, []):
                if "path" in file_info:
                    file_paths.append(file_info["path"])
        
        if not file_paths:
            logger.warning(f"No file paths found for analysis {analysis_id}")
            return
        
        logger.info(f"Processing {len(file_paths)} files for analysis {analysis_id}")
        
        # Process files with orchestrator
        results = await orchestrator.run_project(file_paths)
        
        # Save results to storage
        results_dir = Path(os.getenv("STORAGE_BASE", "storage")) / str(user_id) / "results" / analysis_id
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results_file = results_dir / "result.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Successfully saved results for analysis {analysis_id} to {results_file}")
        
    except Exception as e:
        logger.error(f"Error processing files in background for analysis {analysis_id}: {e}")
        
        # Save error to results
        try:
            error_result = {
                "error": str(e),
                "analysis_id": analysis_id,
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
            results_dir = Path(os.getenv("STORAGE_BASE", "storage")) / str(user_id) / "results" / analysis_id
            results_dir.mkdir(parents=True, exist_ok=True)
            
            with open(results_dir / "result.json", 'w') as f:
                json.dump(error_result, f, indent=2)
        except Exception as save_error:
            logger.error(f"Failed to save error result: {save_error}")



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
            saved_files["technical_files"] = saved
        
        # Validate quantities files
        if quant_files:
            await validate_files(quant_files, "quantities")
            saved = await save_files(quant_files, user_id, analysis_id, "quantities")
            saved_files["quantities_files"] = saved
        
        # Validate drawings files
        if draw_files:
            await validate_files(draw_files, "drawings")
            saved = await save_files(draw_files, user_id, analysis_id, "drawings")
            saved_files["drawings_files"] = saved
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing files: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Error processing files: {str(e)}"
        )
    
    # Schedule background processing with orchestrator using asyncio.create_task
    # This allows the processing to happen asynchronously after the response is sent
    asyncio.create_task(
        process_files_background(
            user_id,
            analysis_id,
            saved_files
        )
    )
    
    # Return response with simplified file info (without full paths)
    response = {
        "analysis_id": analysis_id,
        "status": "processing",
        "files": {
            "technical_files": [
                {
                    "filename": f["saved_filename"],
                    "original_filename": f["original_filename"],
                    "size": f["size"]
                }
                for f in saved_files["technical_files"]
            ],
            "quantities_files": [
                {
                    "filename": f["saved_filename"],
                    "original_filename": f["original_filename"],
                    "size": f["size"]
                }
                for f in saved_files["quantities_files"]
            ],
            "drawings_files": [
                {
                    "filename": f["saved_filename"],
                    "original_filename": f["original_filename"],
                    "size": f["size"]
                }
                for f in saved_files["drawings_files"]
            ]
        }
    }
    
    logger.info(f"Analysis {analysis_id} created successfully, background processing scheduled")
    return response
