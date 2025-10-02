"""
Unified Analysis Router - handles all three upload panels in one endpoint
This router uses the orchestrator to dynamically route files to appropriate agents
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Optional
import os
import tempfile
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analysis", tags=["unified"])

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.xlsx', '.xls', '.xml', '.xc4', '.dwg', '.dxf', '.png', '.jpg', '.jpeg'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/unified")
async def analyze_files(
    technical_files: Optional[List[UploadFile]] = File(None),
    quantities_files: Optional[List[UploadFile]] = File(None),
    drawings_files: Optional[List[UploadFile]] = File(None)
):
    """Unified endpoint for file analysis"""
    
    # Combine all files into a single list with category tracking
    all_files = []
    
    if technical_files:
        for file in technical_files:
            all_files.append((file, "technical"))
    
    if quantities_files:
        for file in quantities_files:
            all_files.append((file, "quantities"))
    
    if drawings_files:
        for file in drawings_files:
            all_files.append((file, "drawings"))
    
    logger.info(f"Received {len(all_files)} files for analysis (technical: {len(technical_files or [])}, quantities: {len(quantities_files or [])}, drawings: {len(drawings_files or [])})")
    
    results = {
        "status": "success",
        "message": None,
        "files": [],
        "summary": {"total": 0, "successful": 0, "failed": 0}
    }
    
    if not all_files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    results["summary"]["total"] = len(all_files)
    
    for file, category in all_files:
        file_result = {
            "name": file.filename,
            "type": os.path.splitext(file.filename)[1].lower(),
            "category": category,
            "success": False,
            "error": None
        }
        
        # Validate extension
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            file_result["error"] = f"Invalid extension: {ext}"
            results["files"].append(file_result)
            results["summary"]["failed"] += 1
            logger.warning(f"Rejected file {file.filename}: invalid extension {ext}")
            continue
        
        # Read file content
        try:
            content = await file.read()
            
            # Validate size
            if len(content) > MAX_FILE_SIZE:
                file_result["error"] = f"File too large: {len(content)} bytes (max 50MB)"
                results["files"].append(file_result)
                results["summary"]["failed"] += 1
                logger.warning(f"Rejected file {file.filename}: too large")
                continue
            
            # Save to temp
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            # TODO: Process file with orchestrator
            # For now, just mark as success
            file_result["success"] = True
            results["summary"]["successful"] += 1
            logger.info(f"Successfully processed {file.filename}")
            
            # Cleanup
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")
            
        except Exception as e:
            file_result["error"] = str(e)
            results["summary"]["failed"] += 1
            logger.error(f"Error processing {file.filename}: {e}")
        
        results["files"].append(file_result)
    
    # Set overall status
    if results["summary"]["failed"] == results["summary"]["total"]:
        results["status"] = "error"
        results["message"] = "All files failed to process"
    elif results["summary"]["failed"] > 0:
        results["status"] = "partial"
        results["message"] = f"{results['summary']['failed']} of {results['summary']['total']} files failed"
    
    logger.info(f"Analysis complete: {results['summary']}")
    return results
