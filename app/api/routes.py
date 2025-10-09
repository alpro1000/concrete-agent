"""
API Routes for Czech Building Audit System
CORE endpoints - upload, status, knowledge base
ИСПРАВЛЕНО: Streaming upload, валидация, без дубликатов
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
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
    ProjectStatus,
    ProjectResponse,
    ProjectStatusResponse,
    WorkflowType,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Константы
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB на файл
ALLOWED_EXTENSIONS = {
    'vykaz': {'.xml', '.xlsx', '.xls', '.pdf'},
    'vykresy': {'.pdf', '.dwg', '.dxf', '.png', '.jpg', '.jpeg'},
    'dokumentace': {'.pdf', '.doc', '.docx', '.xlsx', '.xls'},
}

# In-memory project store (в production заменить на БД)
project_store: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _validate_file(
    file: UploadFile, 
    file_type: str,
    max_size: int = MAX_FILE_SIZE
) -> None:
    """
    Валидация загружаемого файла
    
    Args:
        file: Загружаемый файл
        file_type: Тип файла ('vykaz', 'vykresy', 'dokumentace')
        max_size: Максимальный размер в байтах
    
    Raises:
        ValueError: Если файл не прошел валидацию
    """
    # Проверка расширения
    file_ext = Path(file.filename).suffix.lower()
    allowed = ALLOWED_EXTENSIONS.get(file_type, set())
    
    if file_ext not in allowed:
        raise ValueError(
            f"Nepodporovaný formát pro {file_type}: {file_ext}. "
            f"Povolené: {', '.join(allowed)}"
        )
    
    # Проверка размера (через seek - без загрузки в память)
    file.file.seek(0, 2)  # Конец файла
    size = file.file.tell()
    file.file.seek(0)  # Вернуться в начало
    
    if size > max_size:
        raise ValueError(
            f"Soubor {file.filename} je příliš velký: {size / 1024 / 1024:.1f} MB. "
            f"Maximum: {max_size / 1024 / 1024:.0f} MB"
        )
    
    logger.info(f"✅ Validace OK: {file.filename} ({size / 1024:.1f} KB)")


async def _save_file_streaming(file: UploadFile, save_path: Path) -> int:
    """
    Сохранить файл используя streaming (память-эффективно)
    
    Args:
        file: Загружаемый файл
        save_path: Путь для сохранения
    
    Returns:
        Размер сохраненного файла в байтах
    """
    CHUNK_SIZE = 1024 * 1024  # 1 MB chunks
    total_size = 0
    
    try:
        async with aiofiles.open(save_path, 'wb') as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                await f.write(chunk)
                total_size += len(chunk)
        
        logger.info(f"💾 Uloženo: {save_path.name} ({total_size / 1024:.1f} KB)")
        return total_size
        
    except Exception as e:
        # Удалить частично сохраненный файл
        if save_path.exists():
            save_path.unlink()
        raise


async def _process_project_background(
    project_id: str,
    workflow: str,
    vykaz_path: Optional[Path],
    vykresy_paths: List[Path],
    project_name: str
):
    """
    Фоновая обработка проекта
    
    Args:
        project_id: ID проекта
        workflow: Тип workflow ("A" или "B")
        vykaz_path: Путь к выказу (для Workflow A)
        vykresy_paths: Пути к чертежам
        project_name: Название проекта
    """
    import gc
    
    try:
        logger.info(f"🚀 Začínám zpracování projektu {project_id} (Workflow {workflow})")
        
        # Обновить статус
        if project_id in project_store:
            project_store[project_id]["status"] = ProjectStatus.PROCESSING
        
        # Выбрать и запустить workflow
        if workflow == "A":
            workflow_service = WorkflowA()
            result = await workflow_service.execute(
                project_id=project_id,
                vykaz_path=vykaz_path,
                vykresy_paths=vykresy_paths,
                project_name=project_name
            )
        else:  # workflow == "B"
            workflow_service = WorkflowB()
            result = await workflow_service.execute(
                project_id=project_id,
                vykresy_paths=vykresy_paths,
                project_name=project_name
            )
        
        # Сохранить результаты
        results_dir = settings.DATA_DIR / "results" / project_id
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results_path = results_dir / f"audit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        async with aiofiles.open(results_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Обновить статус
        if project_id in project_store:
            project_store[project_id].update({
                "status": ProjectStatus.COMPLETED,
                "results_path": str(results_path),
                "total_positions": result.get("total_positions", 0),
                "green_count": result.get("green_count", 0),
                "amber_count": result.get("amber_count", 0),
                "red_count": result.get("red_count", 0),
                "completed_at": datetime.now().isoformat()
            })
        
        logger.info(f"✅ Projekt {project_id} dokončen úspěšně")
        
    except Exception as e:
        logger.error(f"❌ Chyba při zpracování projektu {project_id}: {str(e)}", exc_info=True)
        
        if project_id in project_store:
            project_store[project_id].update({
                "status": ProjectStatus.FAILED,
                "error": str(e)
            })
    
    finally:
        # Освободить память
        gc.collect()


# =============================================================================
# MAIN ENDPOINTS
# =============================================================================

@router.get("/")
@router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Czech Building Audit System",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "limits": {
            "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
            "supported_formats": {
                "vykaz": list(ALLOWED_EXTENSIONS['vykaz']),
                "vykresy": list(ALLOWED_EXTENSIONS['vykresy']),
                "dokumentace": list(ALLOWED_EXTENSIONS['dokumentace'])
            }
        }
    }


@router.post("/api/upload", response_model=ProjectResponse)
async def upload_project(
    background_tasks: BackgroundTasks,
    
    # ZÁKLADNÍ PARAMETRY
    project_name: str = Form(..., description="Název projektu"),
    workflow: str = Form(..., description="Typ workflow: 'A' nebo 'B'"),
    
    # HLAVNÍ SOUBORY
    vykaz_vymer: Optional[UploadFile] = File(
        None, 
        description="Výkaz výměr (povinné pro Workflow A)"
    ),
    
    vykresy: List[UploadFile] = File(
        default=[],
        description="Výkresy (povinné pro oba workflows)"
    ),
    
    # VOLITELNÉ SOUBORY
    rozpocet: Optional[UploadFile] = File(
        None,
        description="Rozpočet s cenami (volitelné)"
    ),
    
    dokumentace: List[UploadFile] = File(
        default=[],
        description="Projektová dokumentace (volitelné)"
    ),
    
    zmeny: List[UploadFile] = File(
        default=[],
        description="Změny a dodatky (volitelné)"
    ),
    
    # MOŽNOSTI
    generate_summary: bool = Form(default=True, description="Generovat summary"),
    auto_start_audit: bool = Form(default=True, description="Automaticky spustit audit")
    
) -> ProjectResponse:
    """
    Nahrání projektu pro audit
    
    **Workflow A (Mám výkaz výměr):**
    - ✅ vykaz_vymer (POVINNÉ) - pozice a množství
    - ✅ vykresy (POVINNÉ) - materiály, podmínky, kontext
    - 📄 rozpocet, dokumentace, zmeny (volitelné)
    
    **Workflow B (Vytvořit z výkresů):**
    - ✅ vykresy (POVINNÉ) - generování výkazu z výkresů
    - 📄 dokumentace, zmeny (volitelné)
    
    **Limity:**
    - Maximální velikost souboru: 50 MB
    - Podporované formáty viz /api/health
    """
    try:
        # VALIDACE workflow
        workflow = workflow.upper()
        if workflow not in ["A", "B"]:
            raise HTTPException(
                status_code=400,
                detail="Workflow musí být 'A' nebo 'B'"
            )
        
        # VALIDACE povinných souborů
        if workflow == "A":
            if not vykaz_vymer:
                raise HTTPException(
                    status_code=400,
                    detail="Pro Workflow A je výkaz výměr povinný"
                )
            if not vykresy or len(vykresy) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Pro Workflow A jsou výkresy povinné (pro kontext materiálů a podmínek)"
                )
        
        elif workflow == "B":
            if not vykresy or len(vykresy) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Pro Workflow B jsou výkresy povinné"
                )
        
        # Генерация project ID
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"📤 Nové nahrání: {project_id} - {project_name} (Workflow {workflow})")
        
        # Создание директорий
        project_dir = settings.DATA_DIR / "raw" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # ULOŽENÍ SOUBORŮ
        saved_files = {
            "vykaz_vymer": None,
            "vykresy": [],
            "rozpocet": None,
            "dokumentace": [],
            "zmeny": []
        }
        
        # 1. Výkaz výměr
        if vykaz_vymer:
            await _validate_file(vykaz_vymer, 'vykaz')
            
            vykaz_dir = project_dir / "vykaz_vymer"
            vykaz_dir.mkdir(exist_ok=True)
            
            vykaz_path = vykaz_dir / vykaz_vymer.filename
            size = await _save_file_streaming(vykaz_vymer, vykaz_path)
            
            saved_files["vykaz_vymer"] = {
                "path": str(vykaz_path),
                "filename": vykaz_vymer.filename,
                "size": size
            }
        
        # 2. Výkresy (může быть много)
        if vykresy:
            vykresy_dir = project_dir / "vykresy"
            vykresy_dir.mkdir(exist_ok=True)
            
            for vykres in vykresy:
                await _validate_file(vykres, 'vykresy')
                
                vykres_path = vykresy_dir / vykres.filename
                size = await _save_file_streaming(vykres, vykres_path)
                
                saved_files["vykresy"].append({
                    "path": str(vykres_path),
                    "filename": vykres.filename,
                    "size": size
                })
        
        # 3. Rozpočet
        if rozpocet:
            await _validate_file(rozpocet, 'vykaz')
            
            rozpocet_dir = project_dir / "rozpocet"
            rozpocet_dir.mkdir(exist_ok=True)
            
            rozpocet_path = rozpocet_dir / rozpocet.filename
            size = await _save_file_streaming(rozpocet, rozpocet_path)
            
            saved_files["rozpocet"] = {
                "path": str(rozpocet_path),
                "filename": rozpocet.filename,
                "size": size
            }
        
        # 4. Dokumentace
        if dokumentace:
            dok_dir = project_dir / "dokumentace"
            dok_dir.mkdir(exist_ok=True)
            
            for dok in dokumentace:
                await _validate_file(dok, 'dokumentace')
                
                dok_path = dok_dir / dok.filename
                size = await _save_file_streaming(dok, dok_path)
                
                saved_files["dokumentace"].append({
                    "path": str(dok_path),
                    "filename": dok.filename,
                    "size": size
                })
        
        # 5. Změny
        if zmeny:
            zmeny_dir = project_dir / "zmeny"
            zmeny_dir.mkdir(exist_ok=True)
            
            for zmena in zmeny:
                await _validate_file(zmena, 'dokumentace')
                
                zmena_path = zmeny_dir / zmena.filename
                size = await _save_file_streaming(zmena, zmena_path)
                
                saved_files["zmeny"].append({
                    "path": str(zmena_path),
                    "filename": zmena.filename,
                    "size": size
                })
        
        # Сохранить project info
        project_info = {
            "project_id": project_id,
            "project_name": project_name,
            "workflow": workflow,
            "uploaded_at": datetime.now().isoformat(),
            "status": ProjectStatus.UPLOADED,
            "files": saved_files,
            "options": {
                "generate_summary": generate_summary,
                "auto_start_audit": auto_start_audit
            }
        }
        
        info_path = project_dir / "project_info.json"
        async with aiofiles.open(info_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(project_info, ensure_ascii=False, indent=2))
        
        # Сохранить в store
        project_store[project_id] = project_info.copy()
        
        # Запустить обработку в фоне
        if auto_start_audit:
            vykaz_path = Path(saved_files["vykaz_vymer"]["path"]) if saved_files["vykaz_vymer"] else None
            vykresy_paths = [Path(v["path"]) for v in saved_files["vykresy"]]
            
            background_tasks.add_task(
                _process_project_background,
                project_id=project_id,
                workflow=workflow,
                vykaz_path=vykaz_path,
                vykresy_paths=vykresy_paths,
                project_name=project_name
            )
            
            status = ProjectStatus.PROCESSING
            message = "Projekt nahrán a zpracování zahájeno"
        else:
            status = ProjectStatus.UPLOADED
            message = "Projekt nahrán úspěšně"
        
        logger.info(f"✅ Nahrání dokončeno: {project_id}")
        
        # Convert workflow string to WorkflowType enum
        workflow_type = WorkflowType.A if workflow == "A" else WorkflowType.B
        
        # Format files list for response
        files_list = []
        if saved_files["vykaz_vymer"]:
            files_list.append(saved_files["vykaz_vymer"])
        files_list.extend(saved_files["vykresy"])
        if saved_files["rozpocet"]:
            files_list.append(saved_files["rozpocet"])
        files_list.extend(saved_files["dokumentace"])
        files_list.extend(saved_files["zmeny"])
        
        return ProjectResponse(
            project_id=project_id,
            name=project_name,
            status=status,
            upload_timestamp=datetime.now(),
            workflow=workflow_type,
            files=files_list,
            message=message
        )
        
    except ValueError as e:
        logger.error(f"Chyba validace: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Chyba při nahrávání: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chyba serveru: {str(e)}")


@router.get("/api/projects/{project_id}/status", response_model=ProjectStatusResponse)
async def get_project_status(project_id: str) -> ProjectStatusResponse:
    """
    Získat stav projektu
    
    Args:
        project_id: ID projektu
    
    Returns:
        Aktuální stav zpracování
    """
    if project_id not in project_store:
        raise HTTPException(status_code=404, detail="Projekt nenalezen")
    
    project = project_store[project_id]
    status = project.get("status", ProjectStatus.UPLOADED)
    
    # Vypočítat progress
    progress_map = {
        ProjectStatus.UPLOADED: 10,
        ProjectStatus.PROCESSING: 50,
        ProjectStatus.COMPLETED: 100,
        ProjectStatus.FAILED: 0,
    }
    progress = progress_map.get(status, 0)
    
    # Zpráva podle stavu
    messages = {
        ProjectStatus.UPLOADED: "Projekt nahrán, čeká na zpracování",
        ProjectStatus.PROCESSING: "Probíhá zpracování...",
        ProjectStatus.COMPLETED: "Zpracování dokončeno",
        ProjectStatus.FAILED: f"Chyba: {project.get('error', 'Neznámá chyba')}",
    }
    
    return ProjectStatusResponse(
        project_id=project_id,
        status=status,
        progress=progress,
        message=messages.get(status, "Neznámý stav"),
        positions_total=project.get("total_positions", 0),
        positions_processed=project.get("total_positions", 0) if status == ProjectStatus.COMPLETED else 0,
        green_count=project.get("green_count", 0),
        amber_count=project.get("amber_count", 0),
        red_count=project.get("red_count", 0)
    )


@router.get("/api/projects/{project_id}/results")
async def get_project_results(project_id: str):
    """
    Získat výsledky auditu
    
    Args:
        project_id: ID projektu
    
    Returns:
        Excel soubor s výsledky nebo JSON
    """
    if project_id not in project_store:
        raise HTTPException(status_code=404, detail="Projekt nenalezen")
    
    project = project_store[project_id]
    
    if project.get("status") != ProjectStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Projekt ještě není dokončen. Aktuální stav: {project.get('status')}"
        )
    
    results_path = project.get("results_path")
    if not results_path or not Path(results_path).exists():
        raise HTTPException(status_code=404, detail="Výsledky nenalezeny")
    
    # Vrátit JSON s výsledky
    async with aiofiles.open(results_path, 'r', encoding='utf-8') as f:
        content = await f.read()
        results = json.loads(content)
    
    return results


# =============================================================================
# KNOWLEDGE BASE ENDPOINTS
# =============================================================================

@router.get("/api/kb/status")
async def get_kb_status():
    """Získat stav Knowledge Base"""
    from app.core.kb_loader import get_knowledge_base
    
    kb = get_knowledge_base()
    
    categories = {}
    for category in kb.data:
        data = kb.data[category]
        metadata = kb.metadata.get(category, {})
        categories[category] = {
            "files": len(data) if isinstance(data, dict) else 1,
            "version": metadata.get("version", "1.0"),
            "loaded_at": metadata.get("loaded_at", "unknown")
        }
    
    return {
        "status": "loaded",
        "total_categories": len(categories),
        "categories": categories
    }


@router.post("/api/kb/reload")
async def reload_kb():
    """Znovu načíst Knowledge Base"""
    try:
        from app.core.kb_loader import get_knowledge_base
        from app.core import kb_loader as kb_module
        
        # Reset singleton
        kb_module._kb_instance = None
        
        # Reload KB
        kb = get_knowledge_base()
        
        return {
            "status": "reloaded",
            "message": "Knowledge Base byla úspěšně znovu načtena",
            "categories": len(kb.data)
        }
    except Exception as e:
        logger.error(f"Chyba při načítání KB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
