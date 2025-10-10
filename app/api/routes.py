"""
API Routes for Czech Building Audit System
CORE endpoints - upload, status, knowledge base
ИСПРАВЛЕНО: Streaming upload, валидация, без дубликатов, фильтрация пустых файлов
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
    ProjectStatus,
    ProjectResponse,
    ProjectStatusResponse,
    WorkflowType,
    FileMetadata,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Константы
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB на файл
ALLOWED_EXTENSIONS = {
    'vykaz': {'.xml', '.xlsx', '.xls', '.pdf', '.csv'},  # Added .csv
    'vykresy': {'.pdf', '.dwg', '.dxf', '.png', '.jpg', '.jpeg', '.txt'},  # Added .txt
    'dokumentace': {'.pdf', '.doc', '.docx', '.xlsx', '.xls', '.txt'},  # Added .txt
}

# In-memory project store (в production заменить на БД)
project_store: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _normalize_optional_file(file: Any) -> Optional[UploadFile]:
    """
    Normalize optional file parameter - convert empty string to None
    
    When clients send empty form fields (e.g., -F 'rozpocet='), 
    FastAPI receives empty strings instead of None. This function
    normalizes those to None.
    
    Args:
        file: File parameter that might be UploadFile, str, or None
        
    Returns:
        UploadFile if valid file, None otherwise
    """
    if file is None:
        return None
    if isinstance(file, str):
        # Empty string or any string should be treated as None
        return None
    # Use duck typing to check if it's an UploadFile (has filename attribute)
    if hasattr(file, 'filename'):
        # Check if it has a valid filename
        if not file.filename or file.filename.strip() == "":
            return None
        return file
    return None


def _normalize_file_list(files: List[Any]) -> List[UploadFile]:
    """
    Normalize file list - filter out empty strings and invalid files
    
    When clients send empty form fields in lists (e.g., -F 'zmeny='), 
    FastAPI receives empty strings. This function filters those out.
    
    Args:
        files: List of file parameters
        
    Returns:
        List of valid UploadFile objects
    """
    if not files:
        return []
    
    result = []
    for f in files:
        if isinstance(f, str):
            # Skip empty strings
            continue
        # Use duck typing to check if it's an UploadFile (has filename attribute)
        if hasattr(f, 'filename') and f.filename and f.filename.strip():
            result.append(f)
    
    return result


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


def create_safe_file_metadata(
    file_path: Path,
    file_type: str,
    project_id: str,
    uploaded_at: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Создать безопасные метаданные файла без раскрытия путей сервера
    
    Args:
        file_path: Путь к файлу на сервере (Path объект)
        file_type: Тип файла (vykaz_vymer, vykresy, rozpocet, dokumentace, zmeny)
        project_id: ID проекта
        uploaded_at: Timestamp загрузки (по умолчанию - текущее время)
    
    Returns:
        Dict с безопасными метаданными (без абсолютных путей)
    """
    if uploaded_at is None:
        uploaded_at = datetime.now()
    
    filename = file_path.name
    file_size = file_path.stat().st_size if file_path.exists() else 0
    
    # Создать логический file_id: "project_id:file_type:filename"
    file_id = f"{project_id}:{file_type}:{filename}"
    
    return {
        "file_id": file_id,
        "filename": filename,
        "size": file_size,
        "file_type": file_type,
        "uploaded_at": uploaded_at.isoformat()
    }


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
    
    # HLAVNÍ SOUBORY - Accept Union to handle empty strings
    vykaz_vymer: Union[UploadFile, str, None] = File(
        None, 
        description="Výkaz výměr (povinné pro Workflow A)"
    ),
    
    vykresy: Union[List[UploadFile], List[str], List[Any]] = File(
        default=[],
        description="Výkresy (povinné pro oba workflows)"
    ),
    
    # VOLITELNÉ SOUBORY - Accept Union to handle empty strings
    rozpocet: Union[UploadFile, str, None] = File(
        None,
        description="Rozpočet s cenami (volitelné)"
    ),
    
    dokumentace: Union[List[UploadFile], List[str], List[Any]] = File(
        default=[],
        description="Projektová dokumentace (volitelné)"
    ),
    
    zmeny: Union[List[UploadFile], List[str], List[Any]] = File(
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
        
        # Генерация project ID
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"📤 Nové nahrání: {project_id} - {project_name} (Workflow {workflow})")
        
        # ✅ NORMALIZACE: Convert empty strings to None/empty lists
        # This handles the case where clients send -F 'rozpocet=' or -F 'zmeny='
        vykaz_vymer = _normalize_optional_file(vykaz_vymer)
        rozpocet = _normalize_optional_file(rozpocet)
        vykresy = _normalize_file_list(vykresy) if isinstance(vykresy, list) else []
        dokumentace = _normalize_file_list(dokumentace) if isinstance(dokumentace, list) else []
        zmeny = _normalize_file_list(zmeny) if isinstance(zmeny, list) else []
        
        # ✅ ИСПРАВЛЕНИЕ: Фильтруем пустые файлы ПЕРЕД валидацией
        vykresy_clean = [f for f in vykresy if f and f.filename]
        dokumentace_clean = [f for f in dokumentace if f and f.filename]
        zmeny_clean = [f for f in zmeny if f and f.filename]
        
        logger.info(
            f"Soubory po filtraci: vykresy={len(vykresy_clean)}, "
            f"dokumentace={len(dokumentace_clean)}, zmeny={len(zmeny_clean)}"
        )
        
        # VALIDACE povinných souborů (ПОСЛЕ фильтрации!)
        if workflow == "A":
            if not vykaz_vymer or not vykaz_vymer.filename:
                raise HTTPException(
                    status_code=400,
                    detail="Pro Workflow A je výkaz výměr povinný"
                )
            if len(vykresy_clean) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Pro Workflow A jsou výkresy povinné (pro kontext materiálů a podmínek)"
                )
        
        elif workflow == "B":
            if len(vykresy_clean) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Pro Workflow B jsou výkresy povinné"
                )
        
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
        
        upload_time = datetime.now()
        
        # 1. Výkaz výměr
        if vykaz_vymer and vykaz_vymer.filename:
            await _validate_file(vykaz_vymer, 'vykaz')
            
            vykaz_dir = project_dir / "vykaz_vymer"
            vykaz_dir.mkdir(exist_ok=True)
            
            vykaz_path = vykaz_dir / vykaz_vymer.filename
            size = await _save_file_streaming(vykaz_vymer, vykaz_path)
            
            # Store internal path for processing
            saved_files["vykaz_vymer"] = {
                "path": str(vykaz_path),
                "filename": vykaz_vymer.filename,
                "size": size
            }
        
        # 2. Výkresy (může být много) - используем vykresy_clean!
        if vykresy_clean:
            vykresy_dir = project_dir / "vykresy"
            vykresy_dir.mkdir(exist_ok=True)
            
            for vykres in vykresy_clean:
                await _validate_file(vykres, 'vykresy')
                
                vykres_path = vykresy_dir / vykres.filename
                size = await _save_file_streaming(vykres, vykres_path)
                
                saved_files["vykresy"].append({
                    "path": str(vykres_path),
                    "filename": vykres.filename,
                    "size": size
                })
        
        # 3. Rozpočet
        if rozpocet and rozpocet.filename:
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
        
        # 4. Dokumentace - используем dokumentace_clean!
        if dokumentace_clean:
            dok_dir = project_dir / "dokumentace"
            dok_dir.mkdir(exist_ok=True)
            
            for dok in dokumentace_clean:
                await _validate_file(dok, 'dokumentace')
                
                dok_path = dok_dir / dok.filename
                size = await _save_file_streaming(dok, dok_path)
                
                saved_files["dokumentace"].append({
                    "path": str(dok_path),
                    "filename": dok.filename,
                    "size": size
                })
        
        # 5. Změny - используем zmeny_clean!
        if zmeny_clean:
            zmeny_dir = project_dir / "zmeny"
            zmeny_dir.mkdir(exist_ok=True)
            
            for zmena in zmeny_clean:
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
        
        # Create safe file metadata for response (WITHOUT server paths)
        safe_files_list = []
        
        if saved_files["vykaz_vymer"]:
            safe_metadata = create_safe_file_metadata(
                Path(saved_files["vykaz_vymer"]["path"]),
                "vykaz_vymer",
                project_id,
                upload_time
            )
            safe_files_list.append(safe_metadata)
        
        for vykres_info in saved_files["vykresy"]:
            safe_metadata = create_safe_file_metadata(
                Path(vykres_info["path"]),
                "vykresy",
                project_id,
                upload_time
            )
            safe_files_list.append(safe_metadata)
        
        if saved_files["rozpocet"]:
            safe_metadata = create_safe_file_metadata(
                Path(saved_files["rozpocet"]["path"]),
                "rozpocet",
                project_id,
                upload_time
            )
            safe_files_list.append(safe_metadata)
        
        for dok_info in saved_files["dokumentace"]:
            safe_metadata = create_safe_file_metadata(
                Path(dok_info["path"]),
                "dokumentace",
                project_id,
                upload_time
            )
            safe_files_list.append(safe_metadata)
        
        for zmena_info in saved_files["zmeny"]:
            safe_metadata = create_safe_file_metadata(
                Path(zmena_info["path"]),
                "zmeny",
                project_id,
                upload_time
            )
            safe_files_list.append(safe_metadata)
        
        return ProjectResponse(
            project_id=project_id,
            name=project_name,
            status=status,
            upload_timestamp=datetime.now(),
            workflow=workflow_type,
            files=safe_files_list,  # Safe metadata without server paths!
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


@router.get("/api/projects/{project_id}/files")
async def list_project_files(project_id: str):
    """
    Získat seznam všech souborů projektu (bez serverových cest)
    
    Args:
        project_id: ID projektu
    
    Returns:
        Seznam bezpečných metadat souborů
    """
    if project_id not in project_store:
        raise HTTPException(status_code=404, detail="Projekt nenalezen")
    
    project = project_store[project_id]
    saved_files = project.get("files", {})
    
    safe_files_list = []
    uploaded_at = datetime.fromisoformat(project.get("uploaded_at", datetime.now().isoformat()))
    
    # Process all file types
    if saved_files.get("vykaz_vymer"):
        file_info = saved_files["vykaz_vymer"]
        safe_metadata = create_safe_file_metadata(
            Path(file_info["path"]),
            "vykaz_vymer",
            project_id,
            uploaded_at
        )
        safe_files_list.append(safe_metadata)
    
    for vykres_info in saved_files.get("vykresy", []):
        safe_metadata = create_safe_file_metadata(
            Path(vykres_info["path"]),
            "vykresy",
            project_id,
            uploaded_at
        )
        safe_files_list.append(safe_metadata)
    
    if saved_files.get("rozpocet"):
        file_info = saved_files["rozpocet"]
        safe_metadata = create_safe_file_metadata(
            Path(file_info["path"]),
            "rozpocet",
            project_id,
            uploaded_at
        )
        safe_files_list.append(safe_metadata)
    
    for dok_info in saved_files.get("dokumentace", []):
        safe_metadata = create_safe_file_metadata(
            Path(dok_info["path"]),
            "dokumentace",
            project_id,
            uploaded_at
        )
        safe_files_list.append(safe_metadata)
    
    for zmena_info in saved_files.get("zmeny", []):
        safe_metadata = create_safe_file_metadata(
            Path(zmena_info["path"]),
            "zmeny",
            project_id,
            uploaded_at
        )
        safe_files_list.append(safe_metadata)
    
    return {
        "project_id": project_id,
        "total_files": len(safe_files_list),
        "files": safe_files_list
    }


@router.get("/api/projects/{project_id}/files/{file_id}/download")
async def download_project_file(project_id: str, file_id: str):
    """
    Скачать файл проекта по безопасному file_id
    
    ЗАЩИТА:
    - Проверка что project_id в URL совпадает с project_id в file_id
    - Проверка path traversal (resolved path должен быть внутри project dir)
    - Проверка существования файла
    
    Args:
        project_id: ID проекта из URL
        file_id: Логический ID файла в формате "project_id:file_type:filename"
    
    Returns:
        FileResponse с файлом
    """
    # Проверить что проект существует
    if project_id not in project_store:
        raise HTTPException(status_code=404, detail="Projekt nenalezen")
    
    # Парсить file_id
    try:
        parts = file_id.split(":", 2)
        if len(parts) != 3:
            raise ValueError("Invalid file_id format")
        
        file_project_id, file_type, filename = parts
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Neplatný formát file_id. Očekává se: 'project_id:file_type:filename'"
        )
    
    # SECURITY: Проверка что project_id совпадает
    if file_project_id != project_id:
        logger.warning(
            f"⚠️ Cross-project access attempt: URL project_id={project_id}, "
            f"file_id project_id={file_project_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Přístup odepřen: file_id nepatří k tomuto projektu"
        )
    
    # Получить saved_files из project_store
    project = project_store[project_id]
    saved_files = project.get("files", {})
    
    # Найти файл по типу и имени
    file_path = None
    
    if file_type == "vykaz_vymer" and saved_files.get("vykaz_vymer"):
        file_info = saved_files["vykaz_vymer"]
        if file_info["filename"] == filename:
            file_path = Path(file_info["path"])
    
    elif file_type == "vykresy":
        for vykres_info in saved_files.get("vykresy", []):
            if vykres_info["filename"] == filename:
                file_path = Path(vykres_info["path"])
                break
    
    elif file_type == "rozpocet" and saved_files.get("rozpocet"):
        file_info = saved_files["rozpocet"]
        if file_info["filename"] == filename:
            file_path = Path(file_info["path"])
    
    elif file_type == "dokumentace":
        for dok_info in saved_files.get("dokumentace", []):
            if dok_info["filename"] == filename:
                file_path = Path(dok_info["path"])
                break
    
    elif file_type == "zmeny":
        for zmena_info in saved_files.get("zmeny", []):
            if zmena_info["filename"] == filename:
                file_path = Path(zmena_info["path"])
                break
    
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Soubor nenalezen: {filename} (type: {file_type})"
        )
    
    # SECURITY: Path traversal protection
    project_dir = settings.DATA_DIR / "raw" / project_id
    
    try:
        # Resolve both paths to absolute
        resolved_file = file_path.resolve()
        resolved_project_dir = project_dir.resolve()
        
        # Check that file is inside project directory
        if not str(resolved_file).startswith(str(resolved_project_dir)):
            logger.error(
                f"🚨 Path traversal attempt detected! "
                f"File: {resolved_file}, Project dir: {resolved_project_dir}"
            )
            raise HTTPException(
                status_code=403,
                detail="Přístup odepřen: neplatná cesta k souboru"
            )
        
    except Exception as e:
        logger.error(f"Path resolution error: {e}")
        raise HTTPException(status_code=403, detail="Přístup odepřen")
    
    # Проверить существование файла
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Soubor nebyl nalezen na serveru: {filename}"
        )
    
    logger.info(f"📥 Downloading file: {project_id}/{file_type}/{filename}")
    
    # Return file
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )


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
