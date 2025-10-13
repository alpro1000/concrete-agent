"""
API Routes - UPDATED with Enrichment Support
Добавлена поддержка обогащения позиций из чертежей
"""
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
import logging
import uuid
import aiofiles

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form, Query
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.services.workflow_a import WorkflowA
from app.services.workflow_b import WorkflowB
from app.models.project import (
    Project,
    ProjectStatus,
    ProjectResponse,
    ProjectStatusResponse,
    WorkflowType,
    FileMetadata,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {
    'vykaz': {'.xml', '.xlsx', '.xls', '.pdf', '.csv'},
    'vykresy': {'.pdf', '.dwg', '.dxf', '.png', '.jpg', '.jpeg', '.txt'},
    'dokumentace': {'.pdf', '.doc', '.docx', '.xlsx', '.xls', '.txt', '.csv'},
}

# In-memory project store
project_store: Dict[str, Dict[str, Any]] = {}


def _normalize_optional_file(file: Any) -> Optional[UploadFile]:
    """Convert empty string to None"""
    if file is None:
        return None
    if isinstance(file, str) and file == "":
        return None
    if isinstance(file, UploadFile) and not file.filename:
        return None
    return file if isinstance(file, UploadFile) else None


def _normalize_file_list(files: Any) -> List[UploadFile]:
    """Convert file list, filtering empty values"""
    if files is None:
        return []
    if isinstance(files, str) and files == "":
        return []
    if not isinstance(files, list):
        files = [files]
    
    result = []
    for f in files:
        if isinstance(f, UploadFile) and f.filename:
            result.append(f)
    
    return result


async def _save_file_streaming(
    file: UploadFile, 
    save_path: Path
) -> FileMetadata:
    """Save uploaded file with streaming"""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    async with aiofiles.open(save_path, 'wb') as f:
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                save_path.unlink(missing_ok=True)
                raise HTTPException(400, f"File {file.filename} exceeds 50MB limit")
            await f.write(chunk)
    
    return FileMetadata(
        filename=file.filename,
        size=file_size,
        uploaded_at=datetime.now().isoformat(),
        file_type=Path(file.filename).suffix[1:]
    )


@router.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Czech Building Audit System",
        "status": "running",
        "version": "2.0.0",
        "features": {
            "workflow_a": settings.ENABLE_WORKFLOW_A,
            "workflow_b": settings.ENABLE_WORKFLOW_B,
            "drawing_enrichment": True,  # NEW FEATURE
            "csn_validation": True        # NEW FEATURE
        }
    }


@router.post("/api/upload", response_model=ProjectResponse)
async def upload_project(
    background_tasks: BackgroundTasks,
    
    # Required parameters
    project_name: str = Form(..., description="Project name"),
    workflow: str = Form(..., description="Workflow type: 'A' or 'B'"),
    
    # Main files
    vykaz_vymer: Union[UploadFile, str, None] = File(
        None, 
        description="Výkaz výměr (required for Workflow A)"
    ),
    
    vykresy: Union[List[UploadFile], List[str], List[Any]] = File(
        default=[],
        description="Drawings (required for both workflows)"
    ),
    
    # Optional files
    rozpocet: Union[UploadFile, str, None] = File(
        None,
        description="Budget with prices (optional)"
    ),
    
    dokumentace: Union[List[UploadFile], List[str], List[Any]] = File(
        default=[],
        description="Project documentation (optional)"
    ),
    
    zmeny: Union[List[UploadFile], List[str], List[Any]] = File(
        default=[],
        description="Changes and amendments (optional)"
    ),
    
    # Options
    generate_summary: bool = Form(default=True, description="Generate summary"),
    auto_start_audit: bool = Form(default=True, description="Auto-start audit"),
    
    # ✨ NEW: Enrichment option
    enable_enrichment: bool = Form(
        default=True,
        description="Enable position enrichment with drawing specifications"
    )
    
) -> ProjectResponse:
    """
    Upload project for audit
    
    **NEW in v2.0:** Drawing Enrichment Support
    - Automatically extracts material specifications from drawings
    - Matches positions with drawing specs using AI
    - Validates against ČSN standards
    - Enriches positions with technical parameters
    
    Set enable_enrichment=true to use this feature (default: true)
    """
    
    try:
        # Validate workflow
        workflow = workflow.upper()
        if workflow not in ['A', 'B']:
            raise HTTPException(400, "workflow must be 'A' or 'B'")
        
        # Normalize files
        vykaz_vymer = _normalize_optional_file(vykaz_vymer)
        rozpocet = _normalize_optional_file(rozpocet)
        vykresy_files = _normalize_file_list(vykresy)
        dokumentace_files = _normalize_file_list(dokumentace)
        zmeny_files = _normalize_file_list(zmeny)
        
        # Validate required files
        if workflow == 'A' and not vykaz_vymer:
            raise HTTPException(400, "vykaz_vymer required for Workflow A")
        
        if workflow == 'B' and not vykresy_files:
            raise HTTPException(400, "vykresy required for Workflow B")
        
        # Create project ID
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        
        logger.info(
            f"📤 Nové nahrání: {project_id} - {project_name} "
            f"(Workflow {workflow}, Enrichment: {'enabled' if enable_enrichment else 'disabled'})"
        )
        logger.info(
            f"Soubory po filtraci: "
            f"vykresy={len(vykresy_files)}, "
            f"dokumentace={len(dokumentace_files)}, "
            f"zmeny={len(zmeny_files)}"
        )
        
        # Create project directory
        project_dir = settings.DATA_DIR / "raw" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Save files
        vykaz_vymer_meta = None
        if vykaz_vymer:
            vykaz_dir = project_dir / "vykaz_vymer"
            vykaz_path = vykaz_dir / vykaz_vymer.filename
            
            vykaz_vymer_meta = await _save_file_streaming(vykaz_vymer, vykaz_path)
            logger.info(
                f"✅ Validace OK: {vykaz_vymer.filename} "
                f"({vykaz_vymer_meta.size / 1024:.1f} KB)"
            )
            logger.info(f"💾 Uloženo: {vykaz_vymer.filename} ({vykaz_vymer_meta.size / 1024:.1f} KB)")
        
        rozpocet_meta = None
        if rozpocet:
            rozpocet_dir = project_dir / "rozpocet"
            rozpocet_path = rozpocet_dir / rozpocet.filename
            
            rozpocet_meta = await _save_file_streaming(rozpocet, rozpocet_path)
            logger.info(f"💾 Uloženo: {rozpocet.filename} ({rozpocet_meta.size / 1024:.1f} KB)")
        
        # Save vykresy
        vykresy_dir = project_dir / "vykresy"
        for vykres in vykresy_files:
            vykres_path = vykresy_dir / vykres.filename
            await _save_file_streaming(vykres, vykres_path)
            logger.info(f"💾 Uloženo: {vykres.filename}")
        
        # Save dokumentace
        dokumentace_dir = project_dir / "dokumentace"
        for doc in dokumentace_files:
            doc_path = dokumentace_dir / doc.filename
            await _save_file_streaming(doc, doc_path)
            logger.info(f"💾 Uloženo: {doc.filename}")
        
        # Save zmeny
        zmeny_dir = project_dir / "zmeny"
        for zmena in zmeny_files:
            zmena_path = zmeny_dir / zmena.filename
            await _save_file_streaming(zmena, zmena_path)
            logger.info(f"💾 Uloženo: {zmena.filename}")
        
        # Store project metadata
        project_store[project_id] = {
            "project_id": project_id,
            "project_name": project_name,
            "workflow": workflow,
            "status": ProjectStatus.PENDING,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "enable_enrichment": enable_enrichment,  # ✨ NEW
            "files": {
                "vykaz_vymer": vykaz_vymer_meta.model_dump() if vykaz_vymer_meta else None,
                "rozpocet": rozpocet_meta.model_dump() if rozpocet_meta else None,
                "vykresy": [f.filename for f in vykresy_files],
                "dokumentace": [f.filename for f in dokumentace_files],
                "zmeny": [f.filename for f in zmeny_files]
            },
            "project_dir": str(project_dir)
        }
        
        logger.info(f"✅ Nahrání dokončeno: {project_id}")
        
        # Start processing in background if requested
        if auto_start_audit:
            logger.info(
                f"🚀 Začínám zpracování projektu {project_id} "
                f"(Workflow {workflow}, Enrichment: {'ON' if enable_enrichment else 'OFF'})"
            )
            
            if workflow == 'A':
                workflow_service = WorkflowA()
                background_tasks.add_task(
                    workflow_service.execute,
                    project_id,
                    generate_summary,
                    enable_enrichment  # ✨ NEW: Pass enrichment flag
                )
            elif workflow == 'B':
                workflow_service = WorkflowB()
                background_tasks.add_task(
                    workflow_service.execute,
                    project_id
                )
        
        # ✅ Return project_id in response
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_name,
            "workflow": workflow,
            "uploaded_at": datetime.now().isoformat(),
            "files_uploaded": {
                "vykaz_vymer": vykaz_vymer_meta is not None,
                "vykresy": len(vykresy_files),
                "rozpocet": rozpocet_meta is not None,
                "dokumentace": len(dokumentace_files),
                "zmeny": len(zmeny_files)
            },
            "enrichment_enabled": enable_enrichment,  # ✨ NEW
            "message": f"Project uploaded successfully. ID: {project_id}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.get("/api/projects/{project_id}/status", response_model=ProjectStatusResponse)
async def get_project_status(project_id: str):
    """Get project processing status"""
    
    if project_id not in project_store:
        raise HTTPException(404, f"Project {project_id} not found")
    
    project = project_store[project_id]
    
    return {
        "project_id": project_id,
        "project_name": project["project_name"],
        "status": project["status"],
        "workflow": project["workflow"],
        "created_at": project["created_at"],
        "updated_at": project["updated_at"],
        "progress": project.get("progress", 0),
        "positions_total": project.get("positions_total", 0),
        "positions_processed": project.get("positions_processed", 0)
    }


@router.get("/api/projects/{project_id}/results")
async def get_project_results(project_id: str):
    """
    Get detailed project results including enriched positions
    
    ✨ NEW: Returns enriched positions with technical specifications
    """
    
    if project_id not in project_store:
        raise HTTPException(404, f"Project {project_id} not found")
    
    project = project_store[project_id]
    
    # Check if processing is complete
    if project["status"] != ProjectStatus.COMPLETED:
        return {
            "project_id": project_id,
            "status": project["status"],
            "message": "Project is still processing"
        }
    
    # Return full results
    return {
        "project_id": project_id,
        "project_name": project["project_name"],
        "workflow": project["workflow"],
        "status": project["status"],
        "completed_at": project.get("completed_at"),
        "enrichment_enabled": project.get("enable_enrichment", False),
        "audit_results": project.get("audit_results", {}),
        "summary": project.get("summary", "")
    }


@router.get("/api/projects")
async def list_projects(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List all projects with pagination"""
    
    all_projects = list(project_store.values())
    total = len(all_projects)
    
    # Sort by created_at desc
    all_projects.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Paginate
    projects = all_projects[offset:offset + limit]
    
    return {
        "projects": [
            {
                "project_id": p["project_id"],
                "project_name": p["project_name"],
                "workflow": p["workflow"],
                "status": p["status"],
                "enrichment_enabled": p.get("enable_enrichment", False),
                "created_at": p["created_at"],
                "positions_count": p.get("positions_total", 0)
            }
            for p in projects
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/api/projects/{project_id}/export/excel")
async def export_to_excel(project_id: str):
    """
    Export project results to Excel
    
    ✨ NEW: Includes enriched technical specifications in export
    """
    
    if project_id not in project_store:
        raise HTTPException(404, f"Project {project_id} not found")
    
    project = project_store[project_id]
    
    if project["status"] != ProjectStatus.COMPLETED:
        raise HTTPException(400, "Project not completed yet")
    
    # Generate Excel file
    try:
        from app.utils.excel_exporter import export_enriched_results
        
        excel_path = await export_enriched_results(project)
        
        return FileResponse(
            path=excel_path,
            filename=f"{project['project_name']}_audit_results.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Export failed: {str(e)}")


@router.get("/api/health")
async def health_check():
    """
    Detailed health check with system status
    """
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "workflow_a": settings.ENABLE_WORKFLOW_A,
            "workflow_b": settings.ENABLE_WORKFLOW_B,
            "drawing_enrichment": True,
            "csn_validation": True
        },
        "stats": {
            "total_projects": len(project_store),
            "pending": sum(1 for p in project_store.values() if p["status"] == ProjectStatus.PENDING),
            "processing": sum(1 for p in project_store.values() if p["status"] == ProjectStatus.PROCESSING),
            "completed": sum(1 for p in project_store.values() if p["status"] == ProjectStatus.COMPLETED),
            "failed": sum(1 for p in project_store.values() if p["status"] == ProjectStatus.FAILED)
        }
    }
