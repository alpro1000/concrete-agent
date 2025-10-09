"""
API Routes for Workflow B (Without Estimate - Generate from Drawings)
Specialized endpoints for generating estimates from technical drawings
"""
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from app.core.config import settings
from app.services.workflow_b import WorkflowB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflow-b", tags=["Workflow B"])


# ============================================================================
# WORKFLOW B ENDPOINTS
# ============================================================================

@router.post("/upload")
async def upload_workflow_b(
    drawings: List[UploadFile] = File(..., description="Technical drawings (PDF/images)"),
    documentation: List[UploadFile] = File(default=[], description="Technical documentation"),
    project_name: str = Form(..., description="Project name"),
    use_gpt4v: bool = Form(default=True, description="Use GPT-4 Vision for drawing analysis")
):
    """
    Workflow B: Generate estimate from technical drawings (no existing Výkaz)
    
    Process:
    1. Analyze drawings with GPT-4 Vision → extract dimensions, materials
    2. Calculate material quantities → concrete, reinforcement, formwork
    3. Generate positions with Claude → create complete estimate
    4. Optional: Run AUDIT on generated positions
    
    Args:
        drawings: Technical drawing files (PDF/images)
        documentation: Optional technical specs
        project_name: Name of the project
        use_gpt4v: Whether to use GPT-4V (if False, uses OCR only)
        
    Returns:
        {
            "project_id": str,
            "project_name": str,
            "generated_positions": List[dict],
            "drawing_analysis": List[dict],
            "calculations": dict,
            "tech_card": dict
        }
    """
    try:
        if not settings.ENABLE_WORKFLOW_B:
            raise HTTPException(
                status_code=503,
                detail="Workflow B is disabled. Enable it in settings."
            )
        
        logger.info(f"Workflow B upload: {project_name}, {len(drawings)} drawings")
        
        # Generate project ID
        project_id = str(uuid.uuid4())
        
        # Create project directory
        project_dir = settings.DATA_DIR / "raw" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Save drawing files
        drawing_paths = []
        for drawing in drawings:
            drawing_path = project_dir / drawing.filename
            content = await drawing.read()
            with open(drawing_path, 'wb') as f:
                f.write(content)
            drawing_paths.append(drawing_path)
            logger.info(f"Saved drawing: {drawing_path}")
        
        # Save documentation files
        doc_paths = []
        for doc in documentation:
            doc_path = project_dir / doc.filename
            doc_content = await doc.read()
            with open(doc_path, 'wb') as f:
                f.write(doc_content)
            doc_paths.append(doc_path)
            logger.info(f"Saved documentation: {doc_path}")
        
        # Initialize Workflow B
        workflow = WorkflowB()
        
        # Process drawings and generate estimate
        result = await workflow.process_drawings(
            drawings=drawing_paths,
            documentation=doc_paths if doc_paths else None,
            project_name=project_name
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to process drawings")
            )
        
        # Store project info
        project_info = {
            "project_id": project_id,
            "project_name": project_name,
            "workflow": "B",
            "drawings": [d.name for d in drawing_paths],
            "documentation": [d.name for d in doc_paths],
            "uploaded_at": datetime.now().isoformat(),
            "result": result
        }
        
        # Save project info
        import json
        info_path = project_dir / "project_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        # Save results
        results_dir = settings.DATA_DIR / "results" / project_id
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results_path = results_dir / f"generated_estimate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Workflow B complete. Results saved to: {results_path}")
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_name,
            "generated_positions": result.get("generated_positions", []),
            "drawing_analysis": result.get("drawing_analysis", []),
            "calculations": result.get("calculations", {}),
            "tech_card": result.get("tech_card", {}),
            "total_positions": result.get("total_positions", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow B upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/results")
async def get_workflow_b_results(project_id: str):
    """
    Get Workflow B results for a project
    
    Args:
        project_id: Project UUID
        
    Returns:
        Generated estimate and analysis results
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
        
        # Verify this is a Workflow B project
        if project_info.get("workflow") != "B":
            raise HTTPException(
                status_code=400,
                detail="This is not a Workflow B project"
            )
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_info["project_name"],
            "result": project_info["result"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/tech-card")
async def get_tech_card(project_id: str):
    """
    Get technical card for Workflow B project
    
    Args:
        project_id: Project UUID
        
    Returns:
        Technical card with material calculations
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
        
        tech_card = project_info.get("result", {}).get("tech_card", {})
        
        return {
            "success": True,
            "project_id": project_id,
            "tech_card": tech_card
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tech card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/status")
async def get_workflow_b_status(project_id: str):
    """
    Get Workflow B project status
    
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
        
        result = project_info.get("result", {})
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_info["project_name"],
            "workflow": "B",
            "uploaded_at": project_info["uploaded_at"],
            "drawings_count": len(project_info.get("drawings", [])),
            "generated_positions": result.get("total_positions", 0),
            "has_tech_card": bool(result.get("tech_card"))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
