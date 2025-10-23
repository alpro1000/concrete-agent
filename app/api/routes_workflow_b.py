"""
API Routes for Workflow B - Specialized Endpoints
POUZE specifické endpointy pro Workflow B (bez upload!)
"""
from pathlib import Path
from typing import Any, Dict
import logging
import json

import aiofiles
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.state.project_store import project_store
from app.services.workflow_b import workflow_b

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow-b", tags=["Workflow B"])

# Alias for backwards compatibility with legacy in-memory artifacts cache
projects: Dict[str, Dict[str, Any]] = project_store


def _validate_workflow_b_project(project_id: str) -> None:
    """Ensure the project belongs to Workflow B when metadata is available."""

    project = projects.get(project_id)
    if project and project.get("workflow") not in (None, "B"):
        raise HTTPException(
            status_code=400,
            detail="Tento endpoint je pouze pro Workflow B",
        )


def _get_cached_artifact(project_id: str, artifact_key: str) -> Any | None:
    """Return artifact from in-memory cache if present."""

    project = projects.get(project_id)
    if not project:
        return None

    artifacts = project.get("artifacts")
    if isinstance(artifacts, dict):
        return artifacts.get(artifact_key)
    return None


def _cache_artifact(project_id: str, artifact_key: str, artifact_value: Any) -> None:
    """Persist artifact in the in-memory cache."""

    project = projects.setdefault(project_id, {})
    artifacts = project.setdefault("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        project["artifacts"] = artifacts
    artifacts[artifact_key] = artifact_value


async def _read_artifact_from_disk(path: Path, project_id: str, artifact_key: str) -> Any | None:
    """Read JSON artifact from disk and hydrate the in-memory cache."""

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
    """Persist artifact data to disk using async I/O."""

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
    """Load artifact with memory → disk → generation fallback."""

    cached = _get_cached_artifact(project_id, artifact_key)
    if cached is not None:
        return cached

    curated_dir = settings.DATA_DIR / "curated" / project_id
    artifact_path = curated_dir / filename

    artifact = await _read_artifact_from_disk(artifact_path, project_id, artifact_key)
    if artifact is not None:
        return artifact

    try:
        artifact = await workflow_b.run(
            project_id=project_id,
            action=workflow_action,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(
            "Project %s: Workflow B cannot generate artifact '%s': %s",
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


# =============================================================================
# WORKFLOW B SPECIFIC ENDPOINTS
# =============================================================================


@router.get("/{project_id}/tech-card")
async def get_tech_card(project_id: str):
    """Retrieve the technology card using the memory → disk → generation fallback."""

    _validate_workflow_b_project(project_id)

    try:
        tech_card = await _load_artifact(
            project_id=project_id,
            artifact_key="tech_card",
            filename="tech_card.json",
            workflow_action="tech_card",
        )
        return {
            "success": True,
            "project_id": project_id,
            "tech_card": tech_card,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Project %s: Unexpected error while obtaining tech card: %s",
            project_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{project_id}/calculations")
async def get_material_calculations(project_id: str):
    """Retrieve material calculations with fallback strategy."""

    _validate_workflow_b_project(project_id)

    try:
        calculations = await _load_artifact(
            project_id=project_id,
            artifact_key="material_calculations",
            filename="material_calculations.json",
            workflow_action="material_calculations",
        )
        return {
            "success": True,
            "project_id": project_id,
            "calculations": calculations,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Project %s: Unexpected error while obtaining material calculations: %s",
            project_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{project_id}/drawing-analysis")
async def get_drawing_analysis(project_id: str):
    """Retrieve drawing analysis with fallback strategy."""

    _validate_workflow_b_project(project_id)

    try:
        analysis = await _load_artifact(
            project_id=project_id,
            artifact_key="drawing_analysis",
            filename="drawing_analysis.json",
            workflow_action="drawing_analysis",
        )
        return {
            "success": True,
            "project_id": project_id,
            "analysis": analysis,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Project %s: Unexpected error while obtaining drawing analysis: %s",
            project_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{project_id}/generated-vykaz")
async def get_generated_vykaz(project_id: str):
    """Retrieve the generated bill of quantities with fallback strategy."""

    _validate_workflow_b_project(project_id)

    try:
        vykaz = await _load_artifact(
            project_id=project_id,
            artifact_key="generated_vykaz",
            filename="generated_vykaz.json",
            workflow_action="generated_vykaz",
        )
        total_positions = vykaz.get("total_positions")
        if total_positions is None:
            total_positions = len(vykaz.get("positions", []))

        return {
            "success": True,
            "project_id": project_id,
            "vykaz": vykaz,
            "total_positions": total_positions,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Project %s: Unexpected error while obtaining generated vykaz: %s",
            project_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{project_id}/comparison")
async def compare_with_similar_projects(project_id: str):
    """
    Porovnat s podobnými projekty

    Porovnání:
    - Podobné projekty z historie
    - Rozdíly v množstvích
    - Cenové srovnání
    - Doporučení

    Args:
        project_id: ID projektu

    Returns:
        Srovnání s podobnými projekty
    """

    try:
        # TODO: Implementovat logiku porovnání
        # Pro teď placeholder

        return {
            "success": True,
            "project_id": project_id,
            "similar_projects": [],
            "message": "Funkce bude implementována v příští verzi",
        }

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Chyba při porovnání: {e}")
        raise HTTPException(status_code=500, detail=str(e))
