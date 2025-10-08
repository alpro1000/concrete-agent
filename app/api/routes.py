"""
API Routes - WITH XML, Excel, and PDF support
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional
from datetime import datetime
from pathlib import Path
import shutil
import uuid
import traceback
import logging

from app.core.config import settings
from app.services.workflow_a import workflow_a

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["audit"])
projects_db = {}


@router.post("/upload")
async def upload_project(
    name: str,
    project_pdf: UploadFile = File(..., description="PDF файл проекта"),
    vykaz_file: Optional[UploadFile] = File(None, description="Výkaz výměr (Excel/XML/PDF)")
):
    """
    Upload project files
    
    Supports výkaz in multiple formats:
    - Excel (.xlsx, .xls)
    - XML (.xml) - KROS/RTS export
    - PDF (.pdf)
    """
    project_id = str(uuid.uuid4())
    project_dir = settings.DATA_DIR / "raw" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    
    # Save PDF
    pdf_path = project_dir / f"{name}.pdf"
    with pdf_path.open("wb") as buffer:
        shutil.copyfileobj(project_pdf.file, buffer)
    uploaded_files.append({
        "filename": project_pdf.filename,
        "saved_as": pdf_path.name,
        "type": "project_pdf",
        "size": pdf_path.stat().st_size
    })
    
    # Save výkaz file (Excel/XML/PDF) if provided
    vykaz_path = None
    vykaz_format = None
    
    if vykaz_file:
        # Detect file format from filename
        original_name = vykaz_file.filename.lower()
        
        if original_name.endswith('.xlsx') or original_name.endswith('.xls'):
            vykaz_format = "excel"
            extension = ".xlsx" if original_name.endswith('.xlsx') else ".xls"
            vykaz_path = project_dir / f"{name}_vykaz{extension}"
        
        elif original_name.endswith('.xml'):
            vykaz_format = "xml"
            vykaz_path = project_dir / f"{name}_vykaz.xml"
        
        elif original_name.endswith('.pdf'):
            vykaz_format = "pdf"
            vykaz_path = project_dir / f"{name}_vykaz.pdf"
        
        else:
            # Unknown format, try to save as-is
            vykaz_format = "unknown"
            vykaz_path = project_dir / f"{name}_vykaz.{original_name.split('.')[-1]}"
        
        # Save file
        with vykaz_path.open("wb") as buffer:
            shutil.copyfileobj(vykaz_file.file, buffer)
        
        uploaded_files.append({
            "filename": vykaz_file.filename,
            "saved_as": vykaz_path.name,
            "type": f"vykaz_{vykaz_format}",
            "format": vykaz_format,
            "size": vykaz_path.stat().st_size
        })
        
        logger.info(f"Uploaded výkaz in {vykaz_format} format: {vykaz_path.name}")
    
    # Store metadata
    projects_db[project_id] = {
        "id": project_id,
        "name": name,
        "upload_timestamp": datetime.utcnow().isoformat(),
        "pdf_path": str(pdf_path),
        "vykaz_path": str(vykaz_path) if vykaz_path else None,
        "vykaz_format": vykaz_format,
        "status": "uploaded",
        "workflow": "A" if vykaz_file else "B",
        "files": uploaded_files,
        "error": None
    }
    
    return {
        "project_id": project_id,
        "name": name,
        "upload_timestamp": datetime.utcnow().isoformat(),
        "status": "uploaded",
        "workflow": "A" if vykaz_file else "B",
        "vykaz_format": vykaz_format,
        "files": uploaded_files,
        "message": f"Проект '{name}' загружен. Výkaz формат: {vykaz_format or 'отсутствует'}."
    }


@router.post("/audit/{project_id}/start")
async def start_audit(project_id: str, background_tasks: BackgroundTasks):
    """Start audit with detailed error tracking"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    project = projects_db[project_id]
    
    if project["status"] in ["processing", "completed"]:
        return {
            "project_id": project_id,
            "status": project["status"],
            "message": f"Проект уже в статусе: {project['status']}"
        }
    
    project["status"] = "processing"
    project["audit_start_time"] = datetime.utcnow().isoformat()
    project["error"] = None
    
    async def process_audit_task():
        """Background task with detailed error logging"""
        try:
            logger.info(f"Starting audit for project {project_id}")
            logger.info(f"Výkaz format: {project.get('vykaz_format', 'N/A')}")
            
            # Run Workflow A
            result = await workflow_a.run(
                project_id=project_id,
                calculate_resources=settings.ENABLE_RESOURCE_CALCULATION
            )
            
            # Success
            project["status"] = "completed"
            project["audit_end_time"] = datetime.utcnow().isoformat()
            project["audit_result"] = result
            
            logger.info(f"Audit completed for project {project_id}")
            logger.info(f"Statistics: {result.get('statistics', {})}")
        
        except FileNotFoundError as e:
            error_msg = f"Missing file: {str(e)}"
            logger.error(f"FileNotFoundError in project {project_id}: {error_msg}")
            logger.error(traceback.format_exc())
            
            project["status"] = "failed"
            project["error"] = {
                "type": "FileNotFoundError",
                "message": error_msg,
                "details": "Проверьте что výkaz загружен в поддерживаемом формате (Excel/XML/PDF)",
                "supported_formats": ["Excel (.xlsx, .xls)", "XML (.xml)", "PDF (.pdf)"],
                "traceback": traceback.format_exc()
            }
        
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            logger.error(f"{error_type} in project {project_id}: {error_msg}")
            logger.error(traceback.format_exc())
            
            project["status"] = "failed"
            project["error"] = {
                "type": error_type,
                "message": error_msg,
                "vykaz_format": project.get("vykaz_format"),
                "traceback": traceback.format_exc()
            }
    
    background_tasks.add_task(process_audit_task)
    
    return {
        "project_id": project_id,
        "status": "processing",
        "workflow": project["workflow"],
        "vykaz_format": project.get("vykaz_format"),
        "message": f"Аудит запущен (výkaz format: {project.get('vykaz_format', 'N/A')})",
        "estimated_time": "5-10 минут",
        "check_status_url": f"/api/audit/{project_id}/status"
    }


@router.get("/audit/{project_id}/status")
async def get_audit_status(project_id: str):
    """Get audit status with error details"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    project = projects_db[project_id]
    
    progress = {
        "uploaded": 0,
        "processing": 50,
        "completed": 100,
        "failed": 0
    }.get(project["status"], 0)
    
    current_step = {
        "uploaded": "Ожидание запуска",
        "processing": "Анализ позиций с помощью Claude",
        "completed": "Аудит завершен",
        "failed": "Ошибка обработки"
    }.get(project["status"], "Неизвестный статус")
    
    response = {
        "project_id": project_id,
        "name": project["name"],
        "status": project["status"],
        "workflow": project["workflow"],
        "vykaz_format": project.get("vykaz_format"),
        "progress": progress,
        "current_step": current_step,
        "upload_timestamp": project["upload_timestamp"],
        "audit_start_time": project.get("audit_start_time"),
        "audit_end_time": project.get("audit_end_time")
    }
    
    # Add error details if failed
    if project["status"] == "failed" and project.get("error"):
        response["error"] = project["error"]
    
    return response


@router.get("/audit/{project_id}/results")
async def get_audit_results(project_id: str):
    """Get audit results"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    project = projects_db[project_id]
    
    if project["status"] == "failed":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Аудит завершился с ошибкой",
                "error": project.get("error", "Unknown error"),
                "vykaz_format": project.get("vykaz_format")
            }
        )
    
    if project["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Аудит еще не завершен. Статус: {project['status']}"
        )
    
    audit_result = project.get("audit_result", {})
    
    return {
        "project_id": project_id,
        "name": project["name"],
        "workflow": project["workflow"],
        "vykaz_format": project.get("vykaz_format"),
        "audit_timestamp": project.get("audit_end_time"),
        "summary": audit_result.get("statistics", {}),
        "positions": audit_result.get("positions", []),
        "download_url": f"/api/download/{project_id}/report",
        "message": "Результаты аудита готовы"
    }


@router.get("/projects")
async def list_projects(status: Optional[str] = None, limit: int = 10):
    """List all projects"""
    projects = list(projects_db.values())
    
    if status:
        projects = [p for p in projects if p["status"] == status]
    
    projects.sort(key=lambda x: x["upload_timestamp"], reverse=True)
    projects = projects[:limit]
    
    return {
        "total": len(projects),
        "projects": projects
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete project"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    project = projects_db[project_id]
    
    # Delete files
    project_dir = settings.DATA_DIR / "raw" / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
    
    results_dir = settings.DATA_DIR / "results" / project_id
    if results_dir.exists():
        shutil.rmtree(results_dir)
    
    del projects_db[project_id]
    
    return {
        "message": f"Проект '{project['name']}' удален",
        "project_id": project_id
    }
