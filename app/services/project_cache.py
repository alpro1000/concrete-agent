"""Project cache utilities for Workflow A."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


def _ensure_cache_dir() -> Path:
    """Ensure the project cache directory exists."""
    cache_dir = settings.DATA_DIR / "projects"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_path(project_id: str) -> Path:
    """Return the cache path for a project."""
    return _ensure_cache_dir() / f"{project_id}.json"


def load_project_cache(project_id: str) -> Tuple[Optional[Dict[str, Any]], Path]:
    """Load the cache for a project if it exists."""
    cache_path = get_cache_path(project_id)
    if cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            logger.info("Project %s: Loaded cache from %s", project_id, cache_path)
            audit_payload = data.get("audit_results")
            migrated = _migrate_legacy_audit_results(audit_payload)
            if migrated != audit_payload:
                data["audit_results"] = migrated
                save_project_cache(project_id, data)
            return data, cache_path
        except json.JSONDecodeError as exc:
            logger.warning(
                "Project %s: Cache at %s is corrupt (%s). Re-initialising.",
                project_id,
                cache_path,
                exc,
            )
    return None, cache_path


def save_project_cache(project_id: str, cache_data: Dict[str, Any]) -> Path:
    """Persist project cache to disk."""
    cache_path = get_cache_path(project_id)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cache_data = dict(cache_data)
    cache_data.setdefault("project_id", project_id)
    cache_data["updated_at"] = cache_data.get("updated_at") or datetime.now().isoformat()

    with cache_path.open("w", encoding="utf-8") as fp:
        json.dump(cache_data, fp, ensure_ascii=False, indent=2)

    logger.info("Project %s: Cache saved to %s", project_id, cache_path)
    return cache_path


def load_or_create_project_cache(
    project_id: str, base_data: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], Path, bool]:
    """Load an existing cache or create a new one with base data."""
    existing_cache, cache_path = load_project_cache(project_id)
    if existing_cache is not None:
        return existing_cache, cache_path, False

    cache_payload: Dict[str, Any] = dict(base_data or {})
    cache_payload.setdefault("project_id", project_id)
    now_iso = datetime.now().isoformat()
    cache_payload.setdefault("created_at", now_iso)
    cache_payload["updated_at"] = now_iso

    save_project_cache(project_id, cache_payload)
    logger.info("Project %s: Created new project cache at %s", project_id, cache_path)
    return cache_payload, cache_path, True


def save_field(project_id: str, field: str, value: Any) -> None:
    """Persist a single field update to the project cache."""

    cache_payload, cache_path = load_project_cache(project_id)
    if cache_payload is None:
        cache_payload = {"project_id": project_id}

    cache_payload[field] = value
    save_project_cache(project_id, cache_payload)
    logger.info(
        "Project %s: Cache field '%s' updated via save_field (path=%s)",
        project_id,
        field,
        cache_path,
    )


def _is_new_audit_format(audit_results: Dict[str, Any] | None) -> bool:
    try:
        if not isinstance(audit_results, dict):
            return False
        positions = audit_results.get("positions")
        if not isinstance(positions, list) or not positions:
            return False
        first = positions[0] or {}
        return "classification" in first
    except Exception:  # noqa: BLE001
        return False


def _migrate_legacy_audit_results(old: Dict[str, Any] | None) -> Dict[str, Any]:
    if not old:
        return {
            "total_positions": 0,
            "green": 0,
            "amber": 0,
            "red": 0,
            "positions": [],
            "audit": {"green": 0, "amber": 0, "red": 0},
            "positions_preview": [],
        }

    if _is_new_audit_format(old):
        payload = dict(old)
        payload.setdefault("audit", {
            "green": payload.get("green", 0),
            "amber": payload.get("amber", 0),
            "red": payload.get("red", 0),
        })
        payload.setdefault("positions_preview", payload.get("positions", [])[:100])
        return payload

    summary = old.get("summary") or {}
    green = summary.get("green", 0)
    amber = summary.get("amber", 0)
    red = summary.get("red", 0)
    preview = old.get("preview") or []

    positions = [
        {
            "position_id": p.get("id", "unknown"),
            "code": p.get("code", ""),
            "description": p.get("description", ""),
            "unit": p.get("unit", ""),
            "quantity": p.get("quantity", 0),
            "section": p.get("section", ""),
            "classification": p.get("status", "AMBER"),
            "notes": "",
        }
        for p in preview
        if isinstance(p, dict)
    ]

    total = green + amber + red if (green or amber or red) else len(positions)
    migrated = {
        "total_positions": total,
        "green": green,
        "amber": amber,
        "red": red,
        "positions": positions,
        "audit": {"green": green, "amber": amber, "red": red},
        "positions_preview": positions[:100],
    }

    return migrated
