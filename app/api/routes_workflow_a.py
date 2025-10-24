"""Workflow A artifact endpoints following unified API contract."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import ArtifactPaths
from app.models.project import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow-a", tags=["Workflow A"])


class PositionRequest(BaseModel):
    """Request body for position-scoped artifact generation."""

    position_id: str = Field(..., description="Identifier of the requested position")


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
        logger.warning("Failed to read artifact %s: %s", path, exc)
        return None


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


def _extract_position(payload: Any, position_id: str) -> Optional[Dict[str, Any]]:
    items: list[Dict[str, Any]] = []
    if isinstance(payload, dict):
        candidates = payload.get("items") or payload.get("positions")
        if isinstance(candidates, list):
            items = [item for item in candidates if isinstance(item, dict)]
    elif isinstance(payload, list):
        items = [item for item in payload if isinstance(item, dict)]

    for item in items:
        identifiers = (
            item.get("id"),
            item.get("position_id"),
            item.get("code"),
            item.get("position"),
        )
        if any(str(identifier) == position_id for identifier in identifiers if identifier is not None):
            return item
    return None


@router.get("/{project_id}/positions", response_model=APIResponse)
async def get_positions(project_id: str) -> APIResponse:
    """Return parsed positions for *project_id* (if available)."""

    positions_path = ArtifactPaths.parsed_positions(project_id)
    payload = _load_json(positions_path)

    if payload is None:
        logger.info("Project %s: parsed positions not ready", project_id)
        return APIResponse(
            status="success",
            data=None,
            warning="Positions not yet parsed",
            meta={"project_id": project_id},
        )

    positions: list[Dict[str, Any]]
    if isinstance(payload, dict):
        candidates = payload.get("positions") or payload.get("items") or []
        positions = [item for item in candidates if isinstance(item, dict)]
    elif isinstance(payload, list):
        positions = [item for item in payload if isinstance(item, dict)]
    else:
        positions = []

    return APIResponse(
        status="success",
        data={"items": positions},
        meta={
            "project_id": project_id,
            "count": len(positions),
            "source": str(positions_path),
        },
    )


@router.post("/{project_id}/tech-card", response_model=APIResponse)
async def generate_tech_card(project_id: str, request: PositionRequest) -> APIResponse:
    """Generate or fetch a tech card artifact for a position."""

    artifact_path = ArtifactPaths.tech_card(project_id, request.position_id)
    cached = _load_json(artifact_path)
    if cached is not None:
        return APIResponse(
            status="success",
            data={"tech_card": cached},
            meta={
                "project_id": project_id,
                "position_id": request.position_id,
                "file": str(artifact_path),
            },
        )

    audit_payload = _load_json(ArtifactPaths.audit_results(project_id))
    if audit_payload is None:
        return APIResponse(
            status="success",
            data=None,
            warning="Audit results not ready",
            meta={"project_id": project_id, "position_id": request.position_id},
        )

    position = _extract_position(audit_payload, request.position_id)
    if position is None:
        raise HTTPException(status_code=404, detail="Position not found in audit results")

    tech_card = {
        "position_id": request.position_id,
        "description": position.get("description") or position.get("name"),
        "unit": position.get("unit"),
        "quantity": position.get("quantity"),
        "classification": position.get("classification"),
        "audit": position.get("audit"),
    }
    _dump_json(artifact_path, tech_card)

    return APIResponse(
        status="success",
        data={"tech_card": tech_card},
        meta={
            "project_id": project_id,
            "position_id": request.position_id,
            "file": str(artifact_path),
            "source": "generated_from_audit",
        },
    )


@router.post("/{project_id}/tov", response_model=APIResponse)
async def generate_resource_sheet(project_id: str, request: PositionRequest) -> APIResponse:
    """Generate a resource sheet (TOV) for a position."""

    artifact_path = ArtifactPaths.resource_sheet(project_id, request.position_id)
    cached = _load_json(artifact_path)
    if cached is not None:
        return APIResponse(
            status="success",
            data={"resource_sheet": cached},
            meta={
                "project_id": project_id,
                "position_id": request.position_id,
                "file": str(artifact_path),
            },
        )

    audit_payload = _load_json(ArtifactPaths.audit_results(project_id))
    if audit_payload is None:
        return APIResponse(
            status="success",
            data=None,
            warning="Audit results not ready",
            meta={"project_id": project_id, "position_id": request.position_id},
        )

    position = _extract_position(audit_payload, request.position_id)
    if position is None:
        raise HTTPException(status_code=404, detail="Position not found in audit results")

    resources = position.get("resources") or position.get("materials") or []
    resource_sheet = {
        "position_id": request.position_id,
        "resources": resources,
        "quantity": position.get("quantity"),
        "unit": position.get("unit"),
    }
    _dump_json(artifact_path, resource_sheet)

    return APIResponse(
        status="success",
        data={"resource_sheet": resource_sheet},
        meta={
            "project_id": project_id,
            "position_id": request.position_id,
            "file": str(artifact_path),
            "source": "generated_from_audit",
        },
    )


@router.post("/{project_id}/materials", response_model=APIResponse)
async def generate_materials(project_id: str, request: PositionRequest) -> APIResponse:
    """Generate materials specification for a position."""

    artifact_path = ArtifactPaths.materials(project_id, request.position_id)
    cached = _load_json(artifact_path)
    if cached is not None:
        return APIResponse(
            status="success",
            data={"materials": cached},
            meta={
                "project_id": project_id,
                "position_id": request.position_id,
                "file": str(artifact_path),
            },
        )

    audit_payload = _load_json(ArtifactPaths.audit_results(project_id))
    if audit_payload is None:
        return APIResponse(
            status="success",
            data=None,
            warning="Audit results not ready",
            meta={"project_id": project_id, "position_id": request.position_id},
        )

    position = _extract_position(audit_payload, request.position_id)
    if position is None:
        raise HTTPException(status_code=404, detail="Position not found in audit results")

    materials = position.get("materials") or position.get("resources") or []
    material_payload = {
        "position_id": request.position_id,
        "items": materials,
    }
    _dump_json(artifact_path, material_payload)

    return APIResponse(
        status="success",
        data={"materials": material_payload},
        meta={
            "project_id": project_id,
            "position_id": request.position_id,
            "file": str(artifact_path),
            "source": "generated_from_audit",
        },
    )
