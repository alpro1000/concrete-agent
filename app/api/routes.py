"""
Czech Building Audit System - API Routes
Endpoints for file upload, audit processing, and results
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
from pathlib import Path
import shutil
import uuid

from app.core.config import settings
from app.services.workflow_a import workflow_a

# Create router
router = APIRouter(prefix="/api", tags=["audit"])

# In-memory storage for demo (replace with database later)
projects_db = {}


@router.post("/upload")
async def upload_project(
    name: str,
    project_pdf: UploadFile = File(..., description="PDF файл проекта"),
    vykaz_excel: Optional[UploadFile] = File(None, description="Výkaz výměr Excel (опционально)")
):
    """
    Загрузить проект для аудита
    """
    # Generate project ID
    project_id = str(uuid.uuid4())
    
    # Create project directory
    project_dir = settings.DATA_DIR / "raw" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded files
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
    
    # Save Excel if provided
    excel_path = None
    if vykaz_excel:
        excel_path = project_dir / f"{name}_vykaz.xlsx"
        with excel_path.open("wb") as buffer:
            shutil.copyfileobj(vykaz_excel.file, buffer)
        uploaded_files.append({
            "filename": vykaz_excel.filename,
            "saved_as": excel_path.name,
            "type": "vykaz_excel",
            "size": excel_path.stat().st_size
        })
    
    # Store project metadata
    projects_db[project_id] = {
        "id": project_id,
        "name": name,
        "upload_timestamp": datetime.utcnow().isoformat(),
        "pdf_path": str(pdf_path),
        "excel_path": str(excel_path) if excel_path else None,
        "status": "uploaded",
        "workflow": "A" if vykaz_excel else "B",
        "files": uploaded_files
    }
    
    return {
        "project_id": project_id,
        "name": name,
        "upload_timestamp": datetime.utcnow().isoformat(),
        "status": "uploaded",
        "workflow": "A" if vykaz_excel else "B",
        "files": uploaded_files,
        "message": f"Проект '{name}' успешно загружен. Используется Workflow {'A (с výkaz)' if vykaz_excel else 'B (без výkaz)'}."
    }


@router.post("/audit/{project_id}/start")
async def start_audit(project_id: str, background_tasks: BackgroundTasks):
    """Запустить аудит проекта"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    project = projects_db[project_id]
    
    if project["status"] in ["processing", "completed"]:
        return {
            "project_id": project_id,
            "status": project["status"],
            "message": f"Проект уже в статусе: {project['status']}"
        }
    
    # Update status
    project["status"] = "processing"
    project["audit_start_time"] = datetime.utcnow().isoformat()
    
    # Background task для реального аудита
    async def process_audit_task():
        try:
            # Запустить Workflow A
            result = await workflow_a.run(
                project_id=project_id,
                calculate_resources=settings.ENABLE_RESOURCE_CALCULATION
            )
            
            # Update status
            project["status"] = "completed"
            project["audit_end_time"] = datetime.utcnow().isoformat()
            project["audit_result"] = result
        
        except Exception as e:
            project["status"] = "failed"
            project["error"] = str(e)
    
    background_tasks.add_task(process_audit_task)
    
    return {
        "project_id": project_id,
        "status": "processing",
        "workflow": project["workflow"],
        "message": f"Аудит запущен с использованием Workflow {project['workflow']}",
        "estimated_time": "5-10 минут",
        "check_status_url": f"/api/audit/{project_id}/status"
    }


@router.get("/audit/{project_id}/status")
async def get_audit_status(project_id: str):
    """Получить статус аудита проекта"""
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
    
    return {
        "project_id": project_id,
        "name": project["name"],
        "status": project["status"],
        "workflow": project["workflow"],
        "progress": progress,
        "current_step": current_step,
        "upload_timestamp": project["upload_timestamp"],
        "audit_start_time": project.get("audit_start_time"),
        "audit_end_time": project.get("audit_end_time")
    }


@router.get("/audit/{project_id}/results")
async def get_audit_results(project_id: str):
    """Получить результаты аудита"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    project = projects_db[project_id]
    
    if project["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Аудит еще не завершен. Текущий статус: {project['status']}"
        )
    
    # Return audit result
    audit_result = project.get("audit_result", {})
    
    return {
        "project_id": project_id,
        "name": project["name"],
        "workflow": project["workflow"],
        "audit_timestamp": project.get("audit_end_time"),
        "summary": audit_result.get("statistics", {}),
        "positions": audit_result.get("positions", []),
        "download_url": f"/api/download/{project_id}/report",
        "message": "Результаты аудита. Для полного отчета скачайте Excel файл."
    }


@router.get("/projects")
async def list_projects(status: Optional[str] = None, limit: int = 10):
    """Получить список всех проектов"""
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
    """Удалить проект и все его файлы"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    project = projects_db[project_id]
    
    # Delete project directory
    project_dir = settings.DATA_DIR / "raw" / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
    
    results_dir = settings.DATA_DIR / "results" / project_id
    if results_dir.exists():
        shutil.rmtree(results_dir)
    
    del projects_db[project_id]
    
    return {
        "message": f"Проект '{project['name']}' успешно удален",
        "project_id": project_id
    }
