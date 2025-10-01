"""
Unified Analysis Router - handles all three upload panels in one endpoint
This router uses the orchestrator to dynamically route files to appropriate agents
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import tempfile
import os
import logging
from pathlib import Path
from datetime import datetime

from app.core.orchestrator import get_orchestrator_service

logger = logging.getLogger(__name__)

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
    
    **Features:**
    - Dynamic agent discovery and routing
    - Multilingual support (Czech, Russian, English)
    - Automatic file type detection
    - Parallel processing of multiple file types
    
    **Returns:**
    - Combined analysis results from all agents
    - Separate results for each file category
    - Export-ready JSON format
    """
    
    orchestrator = get_orchestrator_service()
    
    # Collect all files
    all_files = []
    file_categories = {
        'technical': technical_files or [],
        'quantities': quantities_files or [],
        'drawings': drawings_files or []
    }
    
    # Count files
    total_files = sum(len(files) for files in file_categories.values())
    
    if total_files == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one file is required from any upload panel"
        )
    
    logger.info(f"Unified analysis started: {total_files} files total")
    logger.info(f"  - Technical: {len(file_categories['technical'])}")
    logger.info(f"  - Quantities: {len(file_categories['quantities'])}")
    logger.info(f"  - Drawings: {len(file_categories['drawings'])}")
    
    results = {
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        'project_name': project_name or 'Unified Analysis',
        'language': language,
        'file_summary': {
            'technical_count': len(file_categories['technical']),
            'quantities_count': len(file_categories['quantities']),
            'drawings_count': len(file_categories['drawings']),
            'total_count': total_files
        },
        'technical_summary': None,
        'quantities_summary': None,
        'drawings_summary': None,
        'combined_results': None,
        'error_message': None
    }
    
    temp_files = []
    
    try:
        # Process each category
        for category, files in file_categories.items():
            if not files:
                continue
            
            category_results = []
            
            for upload_file in files:
                # Save file temporarily
                suffix = Path(upload_file.filename).suffix
                with tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=suffix,
                    dir=tempfile.gettempdir()
                ) as tmp_file:
                    content = await upload_file.read()
                    tmp_file.write(content)
                    tmp_path = tmp_file.name
                    temp_files.append(tmp_path)
                
                # Process with orchestrator (dynamic agent selection)
                analysis = await orchestrator.process_file(tmp_path)
                
                category_results.append({
                    'filename': upload_file.filename,
                    'detected_type': analysis.detected_type,
                    'agent_used': analysis.agent_used,
                    'success': analysis.success,
                    'result': analysis.result if analysis.success else None,
                    'error': analysis.error
                })
            
            # Store category results
            if category == 'technical':
                results['technical_summary'] = category_results
            elif category == 'quantities':
                results['quantities_summary'] = category_results
            elif category == 'drawings':
                results['drawings_summary'] = category_results
        
        # Create combined results
        results['combined_results'] = {
            'technical': results['technical_summary'],
            'quantities': results['quantities_summary'],
            'drawings': results['drawings_summary'],
            'project_summary': f"Analysis completed successfully for {total_files} files",
            'agents_used': list(set([
                item['agent_used'] 
                for category_results in [
                    results['technical_summary'],
                    results['quantities_summary'],
                    results['drawings_summary']
                ]
                if category_results
                for item in category_results
            ]))
        }
        
        logger.info(f"Unified analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Unified analysis failed: {e}")
        results['success'] = False
        results['error_message'] = str(e)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Cleanup temporary files
        for tmp_path in temp_files:
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp_path}: {e}")
    
    return JSONResponse(content=results)


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
