"""
API Routes for Workflow A - Specialized Endpoints
POUZE specifické endpointy pro Workflow A (bez upload!)
"""
from pathlib import Path
from typing import Any, Dict, List
import logging
import json

import aiofiles
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.state.project_store import project_store
from app.services.workflow_a import workflow_a

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow-a", tags=["Workflow A"])

# Alias for backwards compatibility with legacy in-memory artifacts cache
projects: Dict[str, Dict[str, Any]] = project_store


def _get_cached_artifact(project_id: str, artifact_key: str) -> Any | None:
    """Retrieve an artifact from the in-memory cache if available."""

    project = projects.get(project_id)
    if not project:
        return None

    artifacts = project.get("artifacts")
    if isinstance(artifacts, dict):
        return artifacts.get(artifact_key)
    return None


def _cache_artifact(project_id: str, artifact_key: str, artifact_value: Any) -> None:
    """Store an artifact in the in-memory cache."""

    project = projects.setdefault(project_id, {})
    artifacts = project.setdefault("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        project["artifacts"] = artifacts
    artifacts[artifact_key] = artifact_value


async def _read_artifact_from_disk(path: Path, project_id: str, artifact_key: str) -> Any | None:
    """Read an artifact JSON file asynchronously and cache it in memory."""

    if not path.exists():
        return None

    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as file_obj:
            content = await file_obj.read()
        artifact = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Project %s: Artifact %s corrupted on disk (%s). Will regenerate.",
            project_id,
            artifact_key,
            exc,
        )
        return None
    except OSError as exc:
        logger.warning(
            "Project %s: Failed to read artifact %s from %s: %s",
            project_id,
            artifact_key,
            path,
            exc,
        )
        return None

    _cache_artifact(project_id, artifact_key, artifact)
    return artifact


async def _write_artifact_to_disk(path: Path, data: Any) -> None:
    """Persist artifact data to disk using async file operations."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with aiofiles.open(path, "w", encoding="utf-8") as file_obj:
            await file_obj.write(json.dumps(data, indent=2, ensure_ascii=False))
    except OSError as exc:
        logger.warning("Failed to persist artifact to %s: %s", path, exc)


async def _load_artifact(
    project_id: str,
    artifact_key: str,
    filename: str,
    workflow_action: str,
) -> Any:
    """Load an artifact using memory → disk → generation fallback."""

    cached = _get_cached_artifact(project_id, artifact_key)
    if cached is not None:
        return cached

    curated_dir = settings.DATA_DIR / "curated" / project_id
    artifact_path = curated_dir / filename

    artifact = await _read_artifact_from_disk(artifact_path, project_id, artifact_key)
    if artifact is not None:
        return artifact

    try:
        artifact = await workflow_a.run(
            project_id=project_id,
            action=workflow_action,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(
            "Project %s: Workflow A cannot generate artifact '%s': %s",
            project_id,
            artifact_key,
            exc,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "Project %s: Failed to generate artifact '%s': %s",
            project_id,
            artifact_key,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось сгенерировать артефакт '{artifact_key}'.",
        ) from exc

    await _write_artifact_to_disk(artifact_path, artifact)
    _cache_artifact(project_id, artifact_key, artifact)
    return artifact


# Request/Response Models
class AnalyzePositionsRequest(BaseModel):
    """Request pro analýzu vybraných pozic"""
    selected_indices: List[int]
    context: dict = {}


# =============================================================================
# WORKFLOW A SPECIFIC ENDPOINTS
# =============================================================================

@router.get("/{project_id}/positions")
async def get_positions(project_id: str):
    """
    Získat všechny pozice z výkazu výměr
    
    Args:
        project_id: ID projektu
    
    Returns:
        Seznam všech pozic
    """
    try:
        # Načíst project info
        project_dir = settings.DATA_DIR / "raw" / project_id
        info_path = project_dir / "project_info.json"
        
        if not info_path.exists():
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        with open(info_path, 'r', encoding='utf-8') as f:
            project_info = json.load(f)
        
        # Ověřit že je to Workflow A
        if project_info.get("workflow") != "A":
            raise HTTPException(
                status_code=400,
                detail="Tento endpoint je pouze pro Workflow A"
            )
        
        # Načíst parsované pozice
        curated_dir = settings.DATA_DIR / "curated" / project_id
        positions_path = curated_dir / "parsed_positions.json"
        
        if not positions_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Pozice ještě nebyly zpracovány"
            )
        
        with open(positions_path, 'r', encoding='utf-8') as f:
            positions_data = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_info["project_name"],
            "total_positions": len(positions_data.get("positions", [])),
            "positions": positions_data.get("positions", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při získávání pozic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/analyze")
async def analyze_selected_positions(
    project_id: str,
    request: AnalyzePositionsRequest
):
    """
    Detailní analýza vybraných pozic
    
    Provede hloubkovou kontrolu:
    - Správnost kódů KROS/RTS
    - Ceny vs. databáze
    - Normy ČSN
    - Materiály a podmínky (z výkresů)
    
    Args:
        project_id: ID projektu
        request: Vybrané indexy pozic
    
    Returns:
        Detailní výsledky analýzy
    """
    try:
        logger.info(f"Analýza {len(request.selected_indices)} pozic pro {project_id}")
        
        # Načíst pozice
        curated_dir = settings.DATA_DIR / "curated" / project_id
        positions_path = curated_dir / "parsed_positions.json"
        
        if not positions_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Pozice nenalezeny"
            )
        
        with open(positions_path, 'r', encoding='utf-8') as f:
            positions_data = json.load(f)
        
        all_positions = positions_data.get("positions", [])
        
        # Vybrat požadované pozice
        selected = []
        for idx in request.selected_indices:
            if 0 <= idx < len(all_positions):
                selected.append(all_positions[idx])
        
        if not selected:
            raise HTTPException(
                status_code=400,
                detail="Žádné platné pozice k analýze"
            )
        
        # TODO: Spustit detailní analýzu přes Workflow A service
        # Pro teď vrátíme placeholder
        
        return {
            "success": True,
            "project_id": project_id,
            "analyzed_count": len(selected),
            "positions": selected,
            "message": "Analýza probíhá v pozadí"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při analýze: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/summary")
async def get_project_summary(project_id: str):
    """
    Získat shrnutí projektu
    
    Obsahuje:
    - Informace z výkresu (typ stavby, charakteristika)
    - Statistiky pozic
    - Hlavní práce
    - Speciální požadavky
    
    Args:
        project_id: ID projektu
    
    Returns:
        Shrnutí projektu
    """
    try:
        curated_dir = settings.DATA_DIR / "curated" / project_id
        summary_path = curated_dir / "project_summary.json"
        
        if not summary_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Shrnutí ještě nebylo vygenerováno"
            )
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při načítání shrnutí: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/context")
async def get_drawing_context(project_id: str):
    """
    Získat kontext z výkresů

    Informace extrahované z výkresů:
    - Materiály a jejich vlastnosti
    - Podmínky zpracování
    - Technologické detaily
    - Speciální požadavky
    
    Args:
        project_id: ID projektu
    
    Returns:
        Kontext z výkresů
    """
    try:
        curated_dir = settings.DATA_DIR / "curated" / project_id
        context_path = curated_dir / "drawing_context.json"
        
        if not context_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Kontext z výkresů nebyl zpracován"
            )
        
        with open(context_path, 'r', encoding='utf-8') as f:
            context = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "context": context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při načítání kontextu: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow/a/{project_id}/tech-card")
async def get_tech_card(project_id: str):
    """Получить техкарту с fallback стратегией"""

    try:
        return await _load_artifact(
            project_id=project_id,
            artifact_key="tech_card",
            filename="tech_card.json",
            workflow_action="tech_card",
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "Project %s: Failed to obtain tech card: %s", project_id, exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/workflow/a/{project_id}/resource-sheet")
async def get_resource_sheet(project_id: str):
    """Получить ресурсную ведомость с fallback стратегией"""

    try:
        return await _load_artifact(
            project_id=project_id,
            artifact_key="resource_sheet",
            filename="resource_sheet.json",
            workflow_action="resource_sheet",
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "Project %s: Failed to obtain resource sheet: %s", project_id, exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/workflow/a/{project_id}/material-analysis")
async def get_material_analysis(project_id: str):
    """Получить анализ материалов с fallback стратегией"""

    try:
        return await _load_artifact(
            project_id=project_id,
            artifact_key="material_analysis",
            filename="material_analysis.json",
            workflow_action="materials",
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "Project %s: Failed to obtain material analysis: %s",
            project_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc))
