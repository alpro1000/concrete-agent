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
                    detail=f"❌ Unsupported file type: {doc.filename}"
                )
            
            file_path = os.path.join(temp_dir, doc.filename)
            with open(file_path, "wb") as f:
                content = await doc.read()
                f.write(content)
            file_paths.append(file_path)
            logger.info(f"📄 Uploaded document: {doc.filename}")
        
        # Save smeta if provided
        if smeta:
            if not any(smeta.filename.lower().endswith(ext.lower()) for ext in settings.ALLOWED_EXTENSIONS):
                raise HTTPException(
                    status_code=400, 
                    detail=f"❌ Unsupported smeta file type: {smeta.filename}"
                )
            
            smeta_path = os.path.join(temp_dir, smeta.filename)
            with open(smeta_path, "wb") as f:
                content = await smeta.read()
                f.write(content)
            file_paths.append(smeta_path)
            logger.info(f"📑 Uploaded smeta: {smeta.filename}")
        
        # Run analysis through orchestrator
        if use_parallel:
            result = await orchestrator.run_project(file_paths)
        else:
            # Sequential analysis for comparison
            results = []
            for file_path in file_paths:
                analysis = await orchestrator.process_file(file_path)
                results.append(analysis)
            
            # Aggregate results manually
            result = {
                "total_files": len(file_paths),  
                "successful_analyses": len([r for r in results if r.success]),
                "failed_analyses": len([r for r in results if not r.success]),
                "detailed_results": [
                    {
                        "file": r.file_path,
                        "type": r.detected_type,
                        "agent": r.agent_used,
                        "success": r.success,
                        "result": r.result if r.success else None,
                        "error": r.error
                    }
                    for r in results
                ]
            }
        
        # Add metadata
        result["analysis_metadata"] = {
            "parallel_processing": use_parallel,
            "consistency_validation": validate_consistency,
            "total_documents": len(docs),
            "smeta_included": smeta is not None,
            "orchestrator_version": "enhanced_v2"
        }
        
        logger.info(f"✅ Concrete analysis completed: {result['successful_analyses']}/{result['total_files']} files")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Concrete analysis completed successfully",
                "data": result
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Concrete analysis failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Analysis failed: {str(e)}"
        )
    
    finally:
        # Cleanup temporary files
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@router.post("/concrete/quick")
async def quick_concrete_analysis(
    files: List[UploadFile] = File(..., description="Construction documents for quick analysis")
):
    """
    Quick concrete analysis - focuses only on concrete grade extraction
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Process files with concrete agent directly
        from agents.concrete_agent import UnifiedConcreteAgent
        
        concrete_agent = UnifiedConcreteAgent()
        results = []
        
        for file in files:
            # Save file
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Quick analysis
            try:
                result = await concrete_agent.analyze_document(file_path)
                results.append({
                    "file": file.filename,
                    "success": True,
                    "concrete_grades": result.get("concrete_grades", []),
                    "summary": result.get("summary", {})
                })
            except Exception as e:
                logger.error(f"Quick analysis failed for {file.filename}: {e}")
                results.append({
                    "file": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Quick concrete analysis completed",
                "results": results
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Quick concrete analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Quick analysis failed: {str(e)}"
        )
    
    finally:
        # Cleanup
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@router.get("/concrete/grades")
async def get_supported_concrete_grades():
    """
    Get list of supported concrete grades and specifications
    """
    try:
        from utils.knowledge_base_service import get_knowledge_service
        
        knowledge_service = get_knowledge_service()
        grades = knowledge_service.get_all_concrete_grades()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "supported_grades": grades,
                "total_grades": len(grades)
            }
        )
    except Exception as e:
        logger.error(f"❌ Failed to get concrete grades: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve concrete grades"
        )