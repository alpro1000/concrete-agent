"""
Concrete Analysis Router - Enhanced version using OrchestratorService
"""

import tempfile
import os
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse

from app.core.orchestrator import get_orchestrator_service
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/concrete")
async def analyze_concrete_endpoint(
    docs: List[UploadFile] = File(..., description="Construction documents to analyze"),
    smeta: Optional[UploadFile] = File(None, description="Optional smeta/quantity file"),
    use_parallel: Optional[bool] = Form(True, description="Use parallel analysis"),
    validate_consistency: Optional[bool] = Form(True, description="Validate consistency between documents")
):
    """
    Enhanced concrete analysis endpoint using OrchestratorService
    
    Features:
    - Parallel analysis of multiple documents
    - Consistency validation between documents
    - Supports multiple file types (PDF, DOCX, XLSX, etc.)
    - Comprehensive concrete grade extraction
    """
    if not docs:
        raise HTTPException(status_code=400, detail="No documents provided")
    
    # Validate settings
    if not hasattr(settings, "ALLOWED_EXTENSIONS"):
        raise HTTPException(
            status_code=500, 
            detail="Server configuration error: ALLOWED_EXTENSIONS not defined"
        )
    
    temp_dir = tempfile.mkdtemp()
    orchestrator = get_orchestrator_service()
    
    try:
        # Save uploaded documents
        file_paths = []
        for doc in docs:
            # Validate file extension
            if not any(doc.filename.lower().endswith(ext.lower()) for ext in settings.ALLOWED_EXTENSIONS):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type: {doc.filename}"
                )
            
            file_path = os.path.join(temp_dir, doc.filename)
            with open(file_path, "wb") as f:
                content = await doc.read()
                f.write(content)
            file_paths.append(file_path)
            logger.info(f"Uploaded document: {doc.filename}")
        
        # Save smeta if provided
        if smeta:
            if not any(smeta.filename.lower().endswith(ext.lower()) for ext in settings.ALLOWED_EXTENSIONS):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported smeta file type: {smeta.filename}"
                )
            
            smeta_path = os.path.join(temp_dir, smeta.filename)
            with open(smeta_path, "wb") as f:
                content = await smeta.read()
                f.write(content)
            file_paths.append(smeta_path)
            logger.info(f"Uploaded smeta: {smeta.filename}")
        
        # Run analysis through orchestrator
        result = await orchestrator.run_project(file_paths)
        
        # Add metadata
        result["analysis_metadata"] = {
            "parallel_processing": use_parallel,
            "consistency_validation": validate_consistency,
            "total_documents": len(docs),
            "smeta_included": smeta is not None,
            "orchestrator_version": "enhanced_v2"
        }
        
        logger.info(f"Concrete analysis completed: {len(file_paths)} files")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Concrete analysis completed successfully",
                "data": result
            }
        )
        
    except Exception as e:
        logger.error(f"Concrete analysis failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Analysis failed: {str(e)}"
        )
    
    finally:
        # Cleanup temporary files
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
