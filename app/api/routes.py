"""
API Routes for Czech Building Audit System
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
import uuid
import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.services.workflow_a import WorkflowA
from app.models.project import Project, ProjectStatus

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# In-memory storage for audit tasks
audit_tasks = {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def generate_quick_preview(project_id: str) -> Dict[str, Any]:
    """
    Generate quick preview of uploaded document using Claude
    FIXED: Properly load prompt from file
    """
    logger.info(f"Generating quick preview for {project_id}")
    
    try:
        # Find uploaded file
        raw_dir = settings.DATA_DIR / "raw" / project_id
        if not raw_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Find the file
        files = list(raw_dir.glob("*"))
        if not files:
            raise HTTPException(status_code=404, detail="No files found")
        
        file_path = files[0]
        
        # Initialize Claude client
        from app.core.claude_client import ClaudeClient
        client = ClaudeClient()
        
        # Detect file format
        file_ext = file_path.suffix.lower()
        
        # Parse the file
        if file_ext == '.xml':
            # Check if it's KROS format
            with open(file_path, 'r', encoding='utf-8') as f:
                content_preview = f.read(1000)
            
            if '<TZ>' in content_preview or '<Row>' in content_preview:
                # KROS Table XML
                parsed_data = client.parse_xml(file_path, prompt_name="parsing/parse_kros_table_xml")
            elif '<unixml' in content_preview.lower():
                # KROS UNIXML
                parsed_data = client.parse_xml(file_path, prompt_name="parsing/parse_kros_unixml")
            else:
                # Generic XML
                parsed_data = client.parse_xml(file_path)
        
        elif file_ext in ['.xlsx', '.xls']:
            parsed_data = client.parse_excel(file_path)
        
        elif file_ext == '.pdf':
            parsed_data = client.parse_pdf(file_path)
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_ext}")
        
        # Load quick preview prompt from file
        prompt = client._load_prompt_from_file("analysis/quick_preview")
        
        # Prepare data for preview
        data_summary = {
            "document_type": parsed_data.get("document_info", {}).get("document_type", "Unknown"),
            "total_positions": parsed_data.get("total_positions", 0),
            "positions_sample": parsed_data.get("positions", [])[:5],  # First 5 positions
            "sections": parsed_data.get("sections", [])
        }
        
        # Add data to prompt
        full_prompt = f"""{prompt}

===== DATA Z DOKUMENTU =====
{json.dumps(data_summary, ensure_ascii=False, indent=2)}
"""
        
        # Call Claude for preview
        preview_result = client.call(full_prompt)
        
        # Save preview to curated
        curated_dir = settings.DATA_DIR / "curated" / project_id
        curated_dir.mkdir(parents=True, exist_ok=True)
        
        preview_path = curated_dir / "quick_preview.json"
        with open(preview_path, 'w', encoding='utf-8') as f:
            json.dump({
                "preview": preview_result,
                "parsed_data": parsed_data,
                "generated_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Quick preview generated successfully for {project_id}")
        
        return preview_result
        
    except Exception as e:
        logger.error(f"Preview generation error: {str(e)}")
        # Return fallback preview
        return {
            "nahrano": {
                "nazev_dokumentu": file_path.name if 'file_path' in locals() else "Unknown",
                "format": file_ext.upper() if 'file_ext' in locals() else "Unknown",
                "datum_nacteni": datetime.now().strftime("%Y-%m-%d")
            },
            "obsah": {
                "pocet_pozic": 0,
                "celkova_suma_kc": 0.0,
                "hlavni_prace": [],
                "stav": "chyba při načítání"
            },
            "co_budeme_kontrolovat": [
                "Kódy KROS/RTS",
                "Ceny",
                "Normy ČSN"
            ],
            "doporuceni": f"Chyba při generování náhledu: {str(e)}. Pokračujte na detailní analýzu.",
            "estimate_time_minutes": 5,
            "error": str(e)
        }


async def process_audit_task(project_id: str, file_path: Path, project_name: str):
    """
    Background task for processing audit
    """
    try:
        audit_tasks[project_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Starting audit..."
        }
        
        workflow_a = WorkflowA()
        
        # Run audit workflow
        result = await workflow_a.run(
            file_path=file_path,
            project_name=project_name
        )
        
        # Save results
        curated_dir = settings.DATA_DIR / "curated" / project_id
        curated_dir.mkdir(parents=True, exist_ok=True)
        
        results_path = curated_dir / "audit_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Update task status
        audit_tasks[project_id] = {
            "status": "completed",
            "progress": 100,
            "message": "Audit completed successfully",
            "results": result
        }
        
    except Exception as e:
        logger.error(f"AttributeError: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        audit_tasks[project_id] = {
            "status": "error",
            "progress": 0,
            "message": f"Error: {str(e)}"
        }


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Czech Building Audit System API",
        "version": "1.0.0"
    }


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    quick_preview: bool = Query(False),
    background_tasks: BackgroundTasks = None
):
    """
    Upload výkaz výměr (estimate) file
    
    Supports: Excel (.xlsx, .xls), XML, PDF
    """
    try:
        # Generate project ID
        project_id = str(uuid.uuid4())
        
        # Create directories
        raw_dir = settings.DATA_DIR / "raw" / project_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        file_path = raw_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"File uploaded: {file.filename} -> {project_id}")
        
        # Generate quick preview if requested
        preview = None
        if quick_preview:
            preview = await generate_quick_preview(project_id)
        
        return {
            "project_id": project_id,
            "filename": file.filename,
            "size": len(content),
            "status": "uploaded",
            "preview": preview
        }
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{project_id}")
async def get_preview(project_id: str):
    """
    Get quick preview of uploaded document
    """
    try:
        # Check if preview exists
        curated_dir = settings.DATA_DIR / "curated" / project_id
        preview_path = curated_dir / "quick_preview.json"
        
        if preview_path.exists():
            with open(preview_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("preview", {})
        
        # Generate preview if doesn't exist
        preview = await generate_quick_preview(project_id)
        return preview
        
    except Exception as e:
        logger.error(f"Preview error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audit/{project_id}/start")
async def start_audit(
    project_id: str,
    background_tasks: BackgroundTasks
):
    """
    Start full audit process
    """
    try:
        logger.info(f"Starting full audit for {project_id}")
        
        # Find uploaded file
        raw_dir = settings.DATA_DIR / "raw" / project_id
        if not raw_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        files = list(raw_dir.glob("*"))
        if not files:
            raise HTTPException(status_code=404, detail="No files found")
        
        file_path = files[0]
        
        # Start background task
        background_tasks.add_task(
            process_audit_task,
            project_id,
            file_path,
            file_path.stem
        )
        
        return {
            "project_id": project_id,
            "status": "processing",
            "message": "Audit started in background"
        }
        
    except Exception as e:
        logger.error(f"Audit start error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/{project_id}/status")
async def get_audit_status(project_id: str):
    """
    Get status of audit process
    """
    if project_id not in audit_tasks:
        # Check if results exist
        curated_dir = settings.DATA_DIR / "curated" / project_id
        results_path = curated_dir / "audit_results.json"
        
        if results_path.exists():
            with open(results_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
                return {
                    "status": "completed",
                    "progress": 100,
                    "results": results
                }
        
        return {
            "status": "not_found",
            "message": "Audit not started or project not found"
        }
    
    return audit_tasks[project_id]


@router.get("/audit/{project_id}/results")
async def get_audit_results(project_id: str):
    """
    Get full audit results
    """
    try:
        curated_dir = settings.DATA_DIR / "curated" / project_id
        results_path = curated_dir / "audit_results.json"
        
        if not results_path.exists():
            raise HTTPException(status_code=404, detail="Results not found")
        
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Results retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/status")
async def get_kb_status():
    """
    Get Knowledge Base status
    """
    from app.core.kb_loader import kb_loader
    
    return {
        "loaded": True,
        "categories": len(kb_loader.data),
        "summary": {
            category: {
                "files": len(data),
                "version": metadata.get("version", "1.0")
            }
            for category, (data, metadata) in kb_loader.data.items()
        }
    }


@router.post("/kb/reload")
async def reload_kb():
    """
    Reload Knowledge Base
    """
    try:
        from app.core.kb_loader import kb_loader
        kb_loader.load()
        
        return {
            "status": "reloaded",
            "categories": len(kb_loader.data)
        }
    except Exception as e:
        logger.error(f"KB reload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
