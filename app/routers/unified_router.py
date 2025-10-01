"""
Unified Analysis Router - handles all three upload panels in one endpoint
This router uses the orchestrator to dynamically route files to appropriate agents
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import tempfile
import os
import logging
from pathlib import Path
from datetime import datetime

from app.core.orchestrator import get_orchestrator_service
from app.core.prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)

# File validation configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Unified allowed extensions across all categories
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.xlsx', '.xls', '.xml', '.xc4', '.dwg', '.dxf', '.png', '.jpg', '.jpeg'}

def validate_file(file: UploadFile) -> tuple[bool, Optional[str], str]:
    """
    Validate file extension and return file type.
    
    Returns:
        tuple: (is_valid, error_message, file_type)
    """
    # Get file extension
    file_ext = Path(file.filename).suffix.lower()
    
    # Check if extension is allowed
    if file_ext not in ALLOWED_EXTENSIONS:
        error = f"Invalid extension '{file_ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        logger.warning(f"Upload rejected: {error} for file '{file.filename}'")
        return False, error, file_ext.lstrip('.')
    
    return True, None, file_ext.lstrip('.')

# Router must be named 'router' for auto-discovery
router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["Unified Analysis"],
    responses={404: {"description": "Not found"}}
)


@router.post("/unified")
async def unified_analysis(
    technical_files: Optional[List[UploadFile]] = File(None, description="Technical documents (PDF, DOCX, TXT)"),
    quantities_files: Optional[List[UploadFile]] = File(None, description="Bills of quantities (XLSX, XML, XC4, CSV)"),
    drawings_files: Optional[List[UploadFile]] = File(None, description="Drawings (PDF, DWG, DXF, images)"),
    ai_engine: str = Form(default="auto", description="AI engine: gpt, claude, auto"),
    language: str = Form(default="en", description="Result language: en, cs, ru"),
    project_name: Optional[str] = Form(None, description="Project name")
):
    """
    🎯 **Unified Analysis Endpoint - Handles all three upload panels**
    
    **Three Upload Windows:**
    1. Technical Assignments & Documents (TZD, PDFs, DOCX, TXT)
    2. Work Lists (výkaz výměr, Rozpočet, Excel, XML, XC4)
    3. Drawings (PDF, DWG, DXF, ArchiCAD/Revit images)
    
    **Returns JSON with structure:**
    ```json
    {
      "status": "success" | "error",
      "message": "Optional error description",
      "files": [
        { "name": "file.pdf", "type": "pdf", "success": true, "error": null },
        { "name": "bad.exe", "type": "exe", "success": false, "error": "Invalid extension" }
      ],
      "summary": { "total": 2, "successful": 1, "failed": 1 }
    }
    ```
    
    **HTTP Status Codes:**
    - 200: All files processed successfully
    - 207: Partial success (some files failed)
    - 400: Validation error (bad request)
    - 500: Server error
    """
    
    # Initialize prompt loader (ensures it's available)
    _ = get_prompt_loader()
    
    orchestrator = get_orchestrator_service()
    
    # Collect all files
    all_files: List[tuple[UploadFile, str]] = []  # (file, category)
    
    if technical_files:
        all_files.extend([(f, 'technical') for f in technical_files])
    if quantities_files:
        all_files.extend([(f, 'quantities') for f in quantities_files])
    if drawings_files:
        all_files.extend([(f, 'drawings') for f in drawings_files])
    
    if not all_files:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "At least one file is required from any upload panel",
                "files": [],
                "summary": {"total": 0, "successful": 0, "failed": 0}
            }
        )
    
    logger.info(f"Unified analysis started: {len(all_files)} files total")
    
    # Response structure
    file_results = []
    temp_files = []
    successful_count = 0
    failed_count = 0
    
    try:
        # Process each file
        for upload_file, category in all_files:
            file_result = {
                "name": upload_file.filename,
                "type": None,
                "category": category,
                "success": False,
                "error": None,
                "result": None
            }
            
            try:
                # Validate file
                is_valid, error_msg, file_type = validate_file(upload_file)
                file_result["type"] = file_type
                
                if not is_valid:
                    file_result["error"] = error_msg
                    failed_count += 1
                    file_results.append(file_result)
                    continue
                
                # Read file content and check size
                content = await upload_file.read()
                if len(content) > MAX_FILE_SIZE:
                    size_mb = len(content) / 1024 / 1024
                    max_mb = MAX_FILE_SIZE / 1024 / 1024
                    error = f"File exceeds maximum size of {max_mb:.0f}MB (actual: {size_mb:.2f}MB)"
                    file_result["error"] = error
                    failed_count += 1
                    file_results.append(file_result)
                    logger.warning(f"Upload rejected: {error} for '{upload_file.filename}'")
                    continue
                
                # Save file temporarily to /tmp
                suffix = Path(upload_file.filename).suffix
                with tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=suffix,
                    dir='/tmp'
                ) as tmp_file:
                    tmp_file.write(content)
                    tmp_path = tmp_file.name
                    temp_files.append(tmp_path)
                
                # Process with orchestrator (dynamic agent selection)
                analysis = await orchestrator.process_file(tmp_path)
                
                if analysis.success:
                    file_result["success"] = True
                    file_result["result"] = {
                        "detected_type": analysis.detected_type,
                        "agent_used": analysis.agent_used,
                        "analysis": analysis.result
                    }
                    successful_count += 1
                else:
                    file_result["error"] = analysis.error or "Processing failed"
                    failed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing file {upload_file.filename}: {e}")
                file_result["error"] = str(e)
                failed_count += 1
            
            file_results.append(file_result)
        
        # Determine status and HTTP code
        total = len(all_files)
        
        if failed_count == 0:
            status = "success"
            status_code = 200
            message = f"All {total} file(s) processed successfully"
        elif successful_count == 0:
            status = "error"
            status_code = 400
            message = f"All {total} file(s) failed to process"
        else:
            status = "success"
            status_code = 207  # Multi-Status (partial success)
            message = f"Partial success: {successful_count} succeeded, {failed_count} failed"
        
        response_data = {
            "status": status,
            "message": message,
            "files": file_results,
            "summary": {
                "total": total,
                "successful": successful_count,
                "failed": failed_count
            },
            "project_name": project_name or "Unified Analysis",
            "language": language,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Unified analysis completed: {message}")
        return JSONResponse(status_code=status_code, content=response_data)
        
    except Exception as e:
        logger.error(f"Unified analysis failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Server error: {str(e)}",
                "files": file_results,
                "summary": {
                    "total": len(all_files),
                    "successful": successful_count,
                    "failed": failed_count
                }
            }
        )
    
    finally:
        # Clean up temporary files from /tmp
        for tmp_path in temp_files:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    logger.debug(f"Cleaned up temp file: {tmp_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp_path}: {e}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    orchestrator = get_orchestrator_service()
    orchestrator._ensure_agents_loaded()
    
    return {
        "status": "healthy",
        "service": "unified_analysis",
        "agents_loaded": len(orchestrator._agents),
        "available_agents": list(orchestrator._agents.keys())
    }
