"""
Results Router - handles results retrieval and export functionality
"""

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional
import json
import os
import logging
from io import BytesIO

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/results", tags=["results"])

STORAGE_BASE = "storage"


def validate_token(authorization: Optional[str]) -> dict:
    """Validate mock JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized - No token provided")
    
    token = authorization.replace("Bearer ", "")
    if token != "mock_jwt_token_12345":
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid token")
    
    return {"user_id": 1}


@router.get("/{analysis_id}")
async def get_results(analysis_id: str, authorization: Optional[str] = Header(None)):
    """Get results for a specific analysis"""
    user = validate_token(authorization)
    user_id = user["user_id"]
    
    result_path = os.path.join(STORAGE_BASE, str(user_id), "results", analysis_id, "result.json")
    
    try:
        if os.path.exists(result_path):
            with open(result_path, 'r') as f:
                results = json.load(f)
            logger.info(f"Loaded results for analysis {analysis_id}")
            return results
        else:
            # Return mock data if file doesn't exist
            logger.info(f"No results file found for {analysis_id}, returning mock data")
            return {
                "summary": {
                    "total_files": 3,
                    "processed": 3,
                    "status": "completed"
                },
                "agents": [
                    {
                        "name": "TZD Reader",
                        "files_processed": 1,
                        "status": "completed"
                    }
                ],
                "resources": None
            }
    except Exception as e:
        logger.error(f"Error loading results: {e}")
        raise HTTPException(status_code=500, detail="Failed to load results")


@router.get("/{analysis_id}/export")
async def export_results(
    analysis_id: str,
    format: str = "pdf",
    authorization: Optional[str] = Header(None)
):
    """Export results in specified format (PDF, DOCX, XLSX)"""
    user = validate_token(authorization)
    user_id = user["user_id"]
    
    if format not in ["pdf", "docx", "xlsx"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use: pdf, docx, or xlsx")
    
    result_dir = os.path.join(STORAGE_BASE, str(user_id), "results", analysis_id)
    export_file = os.path.join(result_dir, f"result.{format}")
    
    # For now, generate a mock file if it doesn't exist
    if not os.path.exists(export_file):
        logger.info(f"Export file not found, generating mock {format} file")
        
        # Create directory if it doesn't exist
        os.makedirs(result_dir, exist_ok=True)
        
        # Generate mock content based on format
        if format == "pdf":
            # For PDF, create a simple text file as mock
            content = b"Mock PDF export - Analysis: " + analysis_id.encode()
            content_type = "application/pdf"
        elif format == "docx":
            # For DOCX, create a simple mock
            content = b"Mock DOCX export - Analysis: " + analysis_id.encode()
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:  # xlsx
            content = b"Mock XLSX export - Analysis: " + analysis_id.encode()
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        # Save mock file
        with open(export_file, 'wb') as f:
            f.write(content)
    
    try:
        # Determine content type
        content_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        
        logger.info(f"Exporting {format} for analysis {analysis_id}")
        
        return FileResponse(
            export_file,
            media_type=content_types[format],
            filename=f"analysis_{analysis_id}.{format}",
            headers={
                "Content-Disposition": f"attachment; filename=analysis_{analysis_id}.{format}"
            }
        )
    except Exception as e:
        logger.error(f"Error exporting results: {e}")
        raise HTTPException(status_code=500, detail="Failed to export results")
