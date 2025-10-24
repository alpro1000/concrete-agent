"""Workflow B artifact endpoints with unified API response format."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import ArtifactPaths
from app.models.project import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow-b", tags=["Workflow B"])


class PositionRequest(BaseModel):
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


def _load_generated_positions(project_id: str) -> Optional[list[Dict[str, Any]]]:
    payload = _load_json(ArtifactPaths.generated_positions(project_id))
    if payload is None:
        return None
    if isinstance(payload, dict):
        candidates = payload.get("items") or payload.get("positions")
        if isinstance(candidates, list):
            return [item for item in candidates if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return None


def _extract_generated_position(project_id: str, position_id: str) -> Optional[Dict[str, Any]]:
    positions = _load_generated_positions(project_id) or []
    for item in positions:
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
async def get_generated_positions(project_id: str) -> APIResponse:
    positions = _load_generated_positions(project_id)
    if positions is None:
        return APIResponse(
            status="success",
            data=None,
            warning="Generated positions not yet available",
            meta={"project_id": project_id},
        )

    return APIResponse(
        status="success",
        data={"items": positions},
        meta={
            "project_id": project_id,
            "count": len(positions),
            "source": str(ArtifactPaths.generated_positions(project_id)),
        },
    )


@router.post("/{project_id}/tech-card", response_model=APIResponse)
async def get_workflow_b_tech_card(project_id: str, request: PositionRequest) -> APIResponse:
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

    position = _extract_generated_position(project_id, request.position_id)
    if position is None:
        return APIResponse(
            status="success",
            data=None,
            warning="Generated positions not yet available",
            meta={"project_id": project_id, "position_id": request.position_id},
        )

    tech_card = {
        "position_id": request.position_id,
        "description": position.get("description") or position.get("name"),
        "unit": position.get("unit"),
        "quantity": position.get("quantity"),
        "materials": position.get("materials"),
    }
    _dump_json(artifact_path, tech_card)

    return APIResponse(
        status="success",
        data={"tech_card": tech_card},
        meta={
            "project_id": project_id,
            "position_id": request.position_id,
            "file": str(artifact_path),
            "source": "generated_positions",
        },
    )


@router.post("/{project_id}/tov", response_model=APIResponse)
async def get_workflow_b_resource_sheet(project_id: str, request: PositionRequest) -> APIResponse:
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

    position = _extract_generated_position(project_id, request.position_id)
    if position is None:
        return APIResponse(
            status="success",
            data=None,
            warning="Generated positions not yet available",
            meta={"project_id": project_id, "position_id": request.position_id},
        )

    resources = position.get("resources") or position.get("materials") or []
    payload = {
        "position_id": request.position_id,
        "resources": resources,
    }
    _dump_json(artifact_path, payload)

    return APIResponse(
        status="success",
        data={"resource_sheet": payload},
        meta={
            "project_id": project_id,
            "position_id": request.position_id,
            "file": str(artifact_path),
            "source": "generated_positions",
        },
    )
