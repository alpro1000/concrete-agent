"""
API Routes - WITH Quick Preview (Shrnutí) after upload
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
from app.core.claude_client import ClaudeClient
from app.core.prompt_manager import prompt_manager
from app.services.workflow_a import workflow_a

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["audit"])
projects_db = {}


@router.post("/upload")
async def upload_project(
    name: str,
    project_pdf: UploadFile = File(..., description="PDF файл проекта"),
    vykaz_file: Optional[UploadFile] = File(None, description="Výkaz výměr (Excel/XML/PDF)"),
    quick_preview: bool = True  # ← NEW: Auto-generate preview
):
    """
    Upload project files and get QUICK PREVIEW (Shrnutí)
    
    Returns:
    - Upload confirmation
    - Quick analysis (if quick_preview=True)
    - What was found in document
    - What will be analyzed
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
    
    # Save výkaz file if provided
    vykaz_path = None
    vykaz_format = None
    
    if vykaz_file:
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
            vykaz_format = "unknown"
            vykaz_path = project_dir / f"{name}_vykaz.{original_name.split('.')[-1]}"
        
        with vykaz_path.open("wb") as buffer:
            shutil.copyfileobj(vykaz_file.file, buffer)
        
        uploaded_files.append({
            "filename": vykaz_file.filename,
            "saved_as": vykaz_path.name,
            "type": f"vykaz_{vykaz_format}",
            "format": vykaz_format,
            "size": vykaz_path.stat().st_size
        })
    
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
        "error": None,
        "preview": None  # Will be filled if quick_preview
    }
    
    response = {
        "project_id": project_id,
        "name": name,
        "upload_timestamp": datetime.utcnow().isoformat(),
        "status": "uploaded",
        "workflow": "A" if vykaz_file else "B",
        "vykaz_format": vykaz_format,
        "files": uploaded_files,
        "message": f"Projekt '{name}' nahrán. Formát výkazu: {vykaz_format or 'chybí'}."
    }
    
    # Generate QUICK PREVIEW if requested
    if quick_preview and vykaz_path:
        try:
            logger.info(f"Generating quick preview for {project_id}")
            preview = await _generate_quick_preview(project_id, vykaz_path, vykaz_format)
            
            # Store preview
            projects_db[project_id]["preview"] = preview
            
            # Add to response
            response["preview"] = preview
            response["message"] += " Shrnutí vygenerováno."
        
        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            response["preview_error"] = str(e)
            response["message"] += " Varování: Shrnutí se nepodařilo vygenerovat."
    
    return response


async def _generate_quick_preview(
    project_id: str,
    vykaz_path: Path,
    vykaz_format: str
) -> dict:
    """
    Generate QUICK PREVIEW (Shrnutí) of výkaz
    
    Returns Czech summary:
    - What was uploaded
    - How many positions found
    - Total sum
    - What will be checked
    """
    claude = ClaudeClient()
    
    # Quick parsing prompt (lighter than full audit)
    preview_prompt = """Analyzuj tento dokument výkazu výměr a vytvoř RYCHLÉ SHRNUTÍ v češtině.

ÚKOL:
1. Počet pozic v dokumentu
2. Celková suma projektu (pokud je uvedena)
3. Hlavní typy prací (např. betonové, zednické, zemní)
4. Stav dokumentu (kompletní/nekompletní)

VÝSTUP musí být JSON:
{
  "nahrano": {
    "nazev_dokumentu": "...",
    "format": "Excel/XML/PDF",
    "datum_nacteni": "2025-10-08"
  },
  "obsah": {
    "pocet_pozic": 45,
    "celkova_suma_kc": 1250000.00,
    "hlavni_prace": ["Betonové konstrukce", "Zednické práce", "Zemní práce"],
    "stav": "kompletní"
  },
  "co_budeme_kontrolovat": [
    "Kódy KROS/RTS pro všechny pozice",
    "Srovnání cen s trhem",
    "Kontrola norem ČSN",
    "Výpočet spotřeby materiálu a práce"
  ],
  "doporuceni": "Dokument je připraven k analýze. Klikněte na 'Spustit Audit' pro detailní kontrolu.",
  "estimate_time_minutes": 5
}

Vrať POUZE JSON, bez markdown.
"""
    
    try:
        # Parse based on format
        if vykaz_format == "xml":
            result = claude.parse_xml(vykaz_path, preview_prompt)
        elif vykaz_format in ["excel", "xlsx", "xls"]:
            result = claude.parse_excel(vykaz_path, preview_prompt)
        elif vykaz_format == "pdf":
            result = claude.parse_pdf(vykaz_path, preview_prompt)
        else:
            # Try Excel with fallback
            result = claude.parse_excel(vykaz_path, preview_prompt)
        
        # Ensure we have the expected structure
        if not isinstance(result, dict):
            raise ValueError("Preview result is not a dict")
        
        return result
    
    except Exception as e:
        logger.error(f"Preview generation error: {e}")
        
        # Return minimal preview
        return {
            "nahrano": {
                "nazev_dokumentu": vykaz_path.name,
                "format": vykaz_format,
                "datum_nacteni": datetime.utcnow().strftime("%Y-%m-%d")
            },
            "obsah": {
                "pocet_pozic": "?",
                "celkova_suma_kc": None,
                "hlavni_prace": [],
                "stav": "nepodařilo se analyzovat"
            },
            "co_budeme_kontrolovat": [
                "Kódy KROS/RTS",
                "Ceny",
                "Normy ČSN"
            ],
            "doporuceni": f"Dokument nahrán, ale rychlá analýza selhala: {str(e)}. Můžete pokračovat s plným auditem.",
            "estimate_time_minutes": 10,
            "error": str(e)
        }


@router.get("/preview/{project_id}")
async def get_preview(project_id: str):
    """
    Get quick preview (Shrnutí) for project
    
    If preview wasn't generated during upload, generate it now
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projekt nenalezen")
    
    project = projects_db[project_id]
    
    # Return existing preview
    if project.get("preview"):
        return {
            "project_id": project_id,
            "name": project["name"],
            "preview": project["preview"]
        }
    
    # Generate preview if not exists
    if project.get("vykaz_path"):
        vykaz_path = Path(project["vykaz_path"])
        vykaz_format = project.get("vykaz_format", "unknown")
        
        try:
            preview = await _generate_quick_preview(project_id, vykaz_path, vykaz_format)
            projects_db[project_id]["preview"] = preview
            
            return {
                "project_id": project_id,
                "name": project["name"],
                "preview": preview
            }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Nepodařilo se vygenerovat shrnutí: {str(e)}"
            )
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Projekt nemá výkaz výměr"
        )


@router.post("/audit/{project_id}/start")
async def start_audit(project_id: str, background_tasks: BackgroundTasks):
    """Start full audit (after seeing preview)"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projekt nenalezen")
    
    project = projects_db[project_id]
    
    if project["status"] in ["processing", "completed"]:
        return {
            "project_id": project_id,
            "status": project["status"],
            "message": f"Projekt již ve stavu: {project['status']}"
        }
    
    project["status"] = "processing"
    project["audit_start_time"] = datetime.utcnow().isoformat()
    project["error"] = None
    
    async def process_audit_task():
        try:
            logger.info(f"Starting full audit for {project_id}")
            
            result = await workflow_a.run(
                project_id=project_id,
                calculate_resources=settings.ENABLE_RESOURCE_CALCULATION
            )
            
            project["status"] = "completed"
            project["audit_end_time"] = datetime.utcnow().isoformat()
            project["audit_result"] = result
            
            logger.info(f"Audit completed: {result.get('statistics', {})}")
        
        except FileNotFoundError as e:
            error_msg = f"Chybí soubor: {str(e)}"
            logger.error(f"FileNotFoundError: {error_msg}")
            logger.error(traceback.format_exc())
            
            project["status"] = "failed"
            project["error"] = {
                "type": "FileNotFoundError",
                "message": error_msg,
                "details": "Zkontrolujte že výkaz je v podporovaném formátu (Excel/XML/PDF)",
                "supported_formats": ["Excel (.xlsx, .xls)", "XML (.xml)", "PDF (.pdf)"],
                "traceback": traceback.format_exc()
            }
        
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            logger.error(f"{error_type}: {error_msg}")
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
        "message": "Plný audit zahájen",
        "estimated_time": "5-10 minut",
        "check_status_url": f"/api/audit/{project_id}/status"
    }


@router.get("/audit/{project_id}/status")
async def get_audit_status(project_id: str):
    """Get audit status"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projekt nenalezen")
    
    project = projects_db[project_id]
    
    progress = {
        "uploaded": 0,
        "processing": 50,
        "completed": 100,
        "failed": 0
    }.get(project["status"], 0)
    
    current_step = {
        "uploaded": "Čeká na spuštění",
        "processing": "Analýza pozic pomocí Claude AI",
        "completed": "Audit dokončen",
        "failed": "Chyba zpracování"
    }.get(project["status"], "Neznámý stav")
    
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
    
    if project["status"] == "failed" and project.get("error"):
        response["error"] = project["error"]
    
    return response


@router.get("/audit/{project_id}/results")
async def get_audit_results(project_id: str):
    """Get full audit results"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projekt nenalezen")
    
    project = projects_db[project_id]
    
    if project["status"] == "failed":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Audit skončil chybou",
                "error": project.get("error", "Neznámá chyba")
            }
        )
    
    if project["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Audit ještě není dokončen. Stav: {project['status']}"
        )
    
    audit_result = project.get("audit_result", {})
    
    return {
        "project_id": project_id,
        "name": project["name"],
        "workflow": project["workflow"],
        "audit_timestamp": project.get("audit_end_time"),
        "summary": audit_result.get("statistics", {}),
        "positions": audit_result.get("positions", []),
        "download_url": f"/api/download/{project_id}/report",
        "message": "Výsledky auditu připraveny"
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
        raise HTTPException(status_code=404, detail="Projekt nenalezen")
    
    project = projects_db[project_id]
    
    project_dir = settings.DATA_DIR / "raw" / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
    
    results_dir = settings.DATA_DIR / "results" / project_id
    if results_dir.exists():
        shutil.rmtree(results_dir)
    
    del projects_db[project_id]
    
    return {
        "message": f"Projekt '{project['name']}' smazán",
        "project_id": project_id
    }
