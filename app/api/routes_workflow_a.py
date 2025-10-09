"""
API Routes for Workflow A (With Estimate/Výkaz výměr)
Specialized endpoints for processing existing estimates
"""
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel

from app.core.config import settings
from app.services.workflow_a import WorkflowA

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflow-a", tags=["Workflow A"])


# Request/Response Models
class AnalyzePositionsRequest(BaseModel):
    """Request to analyze selected positions"""
    selected_indices: List[int]
    project_context: Optional[dict] = None


# ============================================================================
# WORKFLOW A ENDPOINTS
# ============================================================================

@router.post("/upload")
async def upload_workflow_a(
    estimate_file: UploadFile = File(..., description="Výkaz výměr (XML/Excel/PDF)"),
    documentation: List[UploadFile] = File(default=[], description="Additional PDF documentation"),
    project_name: str = Form(..., description="Project name"),
    use_nanonets: bool = Form(default=True, description="Use Nanonets for fallback parsing")
):
    """
    Workflow A: Upload estimate with existing Výkaz výměr
    
    Process:
    1. Parse estimate (KROS XML/Excel/PDF) with specialized parsers
    2. Extract all positions
    3. Return positions for user selection
    
    Args:
        estimate_file: Main estimate file (XML/Excel/PDF)
        documentation: Optional supporting documents
        project_name: Name of the project
        use_nanonets: Whether to use Nanonets for fallback
        
    Returns:
        {
            "project_id": str,
            "project_name": str,
            "total_positions": int,
            "positions": List[dict],
            "file_format": str
        }
    """
    try:
        logger.info(f"Workflow A upload: {project_name}, file: {estimate_file.filename}")
        
        # Generate project ID
        project_id = str(uuid.uuid4())
        
        # Create project directory
        project_dir = settings.DATA_DIR / "raw" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Save estimate file
        estimate_path = project_dir / estimate_file.filename
        content = await estimate_file.read()
        with open(estimate_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Saved estimate to: {estimate_path}")
        
        # Save documentation files
        doc_paths = []
        for doc in documentation:
            doc_path = project_dir / doc.filename
            doc_content = await doc.read()
            with open(doc_path, 'wb') as f:
                f.write(doc_content)
            doc_paths.append(doc_path)
            logger.info(f"Saved documentation: {doc_path}")
        
        # Initialize Workflow A
        workflow = WorkflowA()
        
        # Import and prepare positions
        result = await workflow.import_and_prepare(
            file_path=estimate_path,
            project_name=project_name
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to import positions")
            )
        
        # Store project info
        project_info = {
            "project_id": project_id,
            "project_name": project_name,
            "estimate_file": estimate_file.filename,
            "documentation": [doc.filename for doc in documentation],
            "uploaded_at": datetime.now().isoformat(),
            "positions": result["positions"]
        }
        
        # Save project info
        import json
        info_path = project_dir / "project_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_name,
            "total_positions": result["total_positions"],
            "positions": result["positions"],
            "file_format": result["file_format"]
        }
        
    except Exception as e:
        logger.error(f"Workflow A upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/positions")
async def get_positions(project_id: str):
    """
    Get all positions for a project
    
    Args:
        project_id: Project UUID
        
    Returns:
        {
            "project_id": str,
            "project_name": str,
            "total_positions": int,
            "positions": List[dict]
        }
    """
    try:
        # Load project info
        project_dir = settings.DATA_DIR / "raw" / project_id
        info_path = project_dir / "project_info.json"
        
        if not info_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        import json
        with open(info_path, 'r', encoding='utf-8') as f:
            project_info = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_info["project_name"],
            "total_positions": len(project_info["positions"]),
            "positions": project_info["positions"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/analyze")
async def analyze_positions(
    project_id: str,
    request: AnalyzePositionsRequest
):
    """
    Analyze selected positions
    
    Args:
        project_id: Project UUID
        request: Selected position indices and context
        
    Returns:
        {
            "success": bool,
            "total_analyzed": int,
            "results": List[dict]
        }
    """
    try:
        logger.info(f"Analyzing {len(request.selected_indices)} positions for project {project_id}")
        
        # Load project info
        project_dir = settings.DATA_DIR / "raw" / project_id
        info_path = project_dir / "project_info.json"
        
        if not info_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        import json
        with open(info_path, 'r', encoding='utf-8') as f:
            project_info = json.load(f)
        
        # Initialize Workflow A
        workflow = WorkflowA()
        
        # Analyze selected positions
        result = await workflow.analyze_selected_positions(
            positions=project_info["positions"],
            selected_indices=request.selected_indices,
            project_context=request.project_context
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Analysis failed")
            )
        
        # Save results
        results_dir = settings.DATA_DIR / "results" / project_id
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results_path = results_dir / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Analysis results saved to: {results_path}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/status")
async def get_project_status(project_id: str):
    """
    Get project status and metadata
    
    Args:
        project_id: Project UUID
        
    Returns:
        Project status information
    """
    try:
        project_dir = settings.DATA_DIR / "raw" / project_id
        info_path = project_dir / "project_info.json"
        
        if not info_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        import json
        with open(info_path, 'r', encoding='utf-8') as f:
            project_info = json.load(f)
        
        # Check for analysis results
        results_dir = settings.DATA_DIR / "results" / project_id
        analysis_files = list(results_dir.glob("analysis_*.json")) if results_dir.exists() else []
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_info["project_name"],
            "uploaded_at": project_info["uploaded_at"],
            "total_positions": len(project_info["positions"]),
            "analysis_count": len(analysis_files),
            "has_analysis": len(analysis_files) > 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
