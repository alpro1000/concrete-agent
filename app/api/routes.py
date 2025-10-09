"""
API Routes - WITH Quick Preview (Shrnutí) after upload
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional, List
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


def validate_project_id(project_id: str) -> None:
    """Validate project ID format and existence"""
    # Check UUID format
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Neplatné ID projektu (musí být UUID formát)"
        )
    
    # Check existence
    if project_id not in projects_db:
        raise HTTPException(
            status_code=404,
            detail="Projekt nenalezen"
        )


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
        
        # Detect format from extension
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
        
        # Save file
        with vykaz_path.open("wb") as buffer:
            shutil.copyfileobj(vykaz_file.file, buffer)
        
        # Validate file size (max 50MB)
        file_size = vykaz_path.stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            vykaz_path.unlink()  # Delete the file
            raise HTTPException(
                status_code=413,
                detail=f"Soubor je příliš velký ({file_size / 1024 / 1024:.1f}MB). Maximum: 50MB"
            )
        
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
    validate_project_id(project_id)
    
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
    validate_project_id(project_id)
    
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
    validate_project_id(project_id)
    
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
    validate_project_id(project_id)
    
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


# ==========================================
# NEW: Position Selection Endpoints
# ==========================================

@router.post("/positions/import/{project_id}")
async def import_all_positions(project_id: str):
    """
    Import ALL positions from document without limits
    Returns all positions for user to select
    """
    validate_project_id(project_id)
    
    try:
        # Import all positions
        result = await workflow_a.import_all_positions(project_id)
        
        if result.get("success"):
            # Store imported positions in project
            projects_db[project_id]["imported_positions"] = result.get("positions", [])
            projects_db[project_id]["import_timestamp"] = datetime.utcnow().isoformat()
            
        return result
    
    except Exception as e:
        logger.error(f"Failed to import positions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Import pozic selhal: {str(e)}"
        )


@router.get("/positions/{project_id}")
async def get_positions(project_id: str):
    """
    Get all imported positions for selection
    """
    validate_project_id(project_id)
    
    project = projects_db[project_id]
    
    if not project.get("imported_positions"):
        raise HTTPException(
            status_code=400,
            detail="Pozice nejsou importovány. Použijte /positions/import/{project_id}"
        )
    
    return {
        "project_id": project_id,
        "project_name": project["name"],
        "total_positions": len(project["imported_positions"]),
        "positions": project["imported_positions"],
        "message": f"📊 {len(project['imported_positions'])} pozic připraveno k výběru"
    }


@router.post("/positions/analyze/{project_id}")
async def analyze_selected_positions(
    project_id: str,
    selected_positions: List[str]
):
    """
    Analyze only user-selected positions
    
    Args:
        project_id: ID projektu
        selected_positions: List of position numbers selected by user
    """
    validate_project_id(project_id)
    
    if not selected_positions:
        raise HTTPException(
            status_code=400,
            detail="Není vybráno žádná pozice"
        )
    
    try:
        # Analyze only selected positions
        result = await workflow_a.analyze_selected_positions(
            project_id=project_id,
            selected_position_numbers=selected_positions
        )
        
        if result.get("success"):
            # Store analysis result
            projects_db[project_id]["analysis_result"] = result
            projects_db[project_id]["analysis_timestamp"] = datetime.utcnow().isoformat()
            projects_db[project_id]["status"] = "analyzed"
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to analyze positions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analýza pozic selhala: {str(e)}"
        )


# ==========================================
# NEW: Drawing Analysis Endpoints
# ==========================================

@router.post("/drawings/upload")
async def upload_drawing(
    project_id: str,
    drawing_file: UploadFile = File(..., description="Výkres (PDF, PNG, JPG)"),
    drawing_type: str = "general"
):
    """
    Upload construction drawing for OCR/Vision analysis
    
    Supports: PDF, PNG, JPG, DWG (converted)
    """
    validate_project_id(project_id)
    
    project = projects_db[project_id]
    project_dir = Path(project["pdf_path"]).parent
    
    # Create drawings subdirectory
    drawings_dir = project_dir / "drawings"
    drawings_dir.mkdir(exist_ok=True)
    
    # Save drawing file
    file_ext = Path(drawing_file.filename).suffix.lower()
    
    if file_ext not in ['.pdf', '.png', '.jpg', '.jpeg', '.dwg']:
        raise HTTPException(
            status_code=400,
            detail=f"Nepodporovaný formát souboru: {file_ext}. Použijte PDF, PNG, JPG nebo DWG."
        )
    
    drawing_filename = f"drawing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    drawing_path = drawings_dir / drawing_filename
    
    with drawing_path.open("wb") as buffer:
        shutil.copyfileobj(drawing_file.file, buffer)
    
    return {
        "success": True,
        "project_id": project_id,
        "drawing_path": str(drawing_path),
        "drawing_type": drawing_type,
        "message": f"Výkres nahrán: {drawing_filename}",
        "next_step": f"Použijte POST /api/drawings/analyze pro analýzu"
    }


@router.post("/drawings/analyze")
async def analyze_drawing(
    project_id: str,
    drawing_path: str,
    drawing_type: str = "general"
):
    """
    Analyze construction drawing using GPT-4 Vision
    
    Extracts:
    - Construction elements (PILOTY, ZÁKLADY, PILÍŘE, OPĚRY)
    - Materials (BETON, OCEL, OPÁLUBKA)
    - Standards (ČSN EN 206+A2, TKP KAP. 18)
    - Exposure classes (XA2+XC2, XF3+XC2)
    - Surface categories (Aa, C1a, C2d, Bd, E)
    """
    validate_project_id(project_id)
    
    from app.services.drawing_analyzer import drawing_analyzer
    
    drawing_file_path = Path(drawing_path)
    
    if not drawing_file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Výkres nenalezen: {drawing_path}"
        )
    
    try:
        # Analyze drawing
        result = await drawing_analyzer.upload_and_analyze_drawing(
            project_id=project_id,
            drawing_file_path=drawing_file_path,
            drawing_type=drawing_type
        )
        
        if result.get("success"):
            # Store drawing analysis in project
            if "drawings" not in projects_db[project_id]:
                projects_db[project_id]["drawings"] = []
            
            projects_db[project_id]["drawings"].append({
                "drawing_id": result["drawing_id"],
                "path": str(drawing_file_path),
                "type": drawing_type,
                "analysis": result["analysis"],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Drawing analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analýza výkresu selhala: {str(e)}"
        )


@router.post("/drawings/link-estimate")
async def link_drawing_to_estimate(
    project_id: str,
    drawing_id: str
):
    """
    Link drawing elements to estimate positions
    
    Creates automatic associations between construction elements
    from drawings and positions in estimate
    """
    validate_project_id(project_id)
    
    from app.services.drawing_analyzer import drawing_analyzer
    
    project = projects_db[project_id]
    
    # Find drawing
    drawing = None
    for dwg in project.get("drawings", []):
        if dwg["drawing_id"] == drawing_id:
            drawing = dwg
            break
    
    if not drawing:
        raise HTTPException(
            status_code=404,
            detail=f"Výkres {drawing_id} nenalezen v projektu"
        )
    
    # Get estimate positions
    estimate_positions = project.get("imported_positions", [])
    
    if not estimate_positions:
        raise HTTPException(
            status_code=400,
            detail="Projekt nemá importované pozice. Nejprve importujte pozice."
        )
    
    try:
        # Create links
        links = await drawing_analyzer.link_drawing_to_estimate(
            drawing_id=drawing_id,
            drawing_analysis=drawing["analysis"],
            estimate_positions=estimate_positions
        )
        
        # Store links
        if "drawing_links" not in projects_db[project_id]:
            projects_db[project_id]["drawing_links"] = []
        
        projects_db[project_id]["drawing_links"].extend([
            link.dict() for link in links
        ])
        
        return {
            "success": True,
            "project_id": project_id,
            "drawing_id": drawing_id,
            "links_created": len(links),
            "links": [link.dict() for link in links],
            "message": f"Vytvořeno {len(links)} propojení mezi výkresem a smetou"
        }
    
    except Exception as e:
        logger.error(f"Failed to link drawing to estimate: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Propojení selhalo: {str(e)}"
        )

