"""
Project Analysis Router - Uses OrchestratorAgent for comprehensive project analysis
"""

import tempfile
import os
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse

from app.agents.orchestrator_agent import get_orchestrator_agent
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/project")
async def analyze_project(
    files: List[UploadFile] = File(..., description="Project files to analyze"),
    project_name: Optional[str] = Form(None, description="Optional project name"),
    language: Optional[str] = Form("cz", description="Analysis language"),
    use_claude: Optional[bool] = Form(True, description="Use Claude AI for enhanced analysis"),
    export_format: Optional[str] = Form("json", description="Export format")
):
    """
    Comprehensive project analysis using OrchestratorAgent
    
    Automatically detects file types and routes to appropriate agents:
    - Smeta files (xlsx/xml/xc4) → VolumeAgent
    - Technical assignments (pdf/docx/txt) → TZDReader  
    - Drawings (dwg/pdf) → DrawingVolumeAgent
    - General documents → ConcreteAgent + MaterialAgent
    
    Returns aggregated results from all relevant agents.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    temp_dir = tempfile.mkdtemp()
    orchestrator = get_orchestrator_agent()
    
    try:
        # Save uploaded files
        file_paths = []
        for file in files:
            # Validate file extension
            if not any(file.filename.lower().endswith(ext.lower()) for ext in settings.ALLOWED_EXTENSIONS):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type: {file.filename}"
                )
            
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            file_paths.append(file_path)
            logger.info(f"📄 Saved file: {file.filename} ({len(content)} bytes)")

        # Run orchestrator analysis
        logger.info(f"🚀 Starting project analysis for {len(file_paths)} files")
        result = await orchestrator.run_project(file_paths)
        
        # Add metadata
        result["metadata"] = {
            "project_name": project_name or "Unnamed Project",
            "total_files": len(file_paths),
            "file_names": [os.path.basename(fp) for fp in file_paths],
            "language": language,
            "use_claude": use_claude,
            "export_format": export_format
        }
        
        logger.info(f"✅ Project analysis completed successfully")
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"❌ Project analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        
    finally:
        # Cleanup temporary files
        try:
            import shutil
            shutil.rmtree(temp_dir)
            logger.debug(f"🧹 Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")


@router.get("/project/status")
async def get_project_analysis_status():
    """Get status of project analysis capabilities"""
    orchestrator = get_orchestrator_agent()
    
    return {
        "service": "Project Analysis API",
        "orchestrator_available": True,
        "llm_service_status": orchestrator.llm.get_status(),
        "available_prompts": orchestrator.prompt_loader.list_available_prompts(),
        "supported_file_types": {
            "smeta": [".xlsx", ".xls", ".xml", ".xc4"],
            "technical_documents": [".pdf", ".docx", ".doc", ".txt"],
            "drawings": [".dwg", ".dxf"],
            "general": [".pdf", ".docx", ".txt", ".doc"]
        },
        "agent_routing": {
            "smeta_files": "VolumeAgent",
            "technical_assignments": "TZDReader", 
            "drawings": "DrawingVolumeAgent",
            "general_documents": "ConcreteAgent + MaterialAgent"
        }
    }