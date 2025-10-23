"""Workflow A - Steps 1–6 implementation (upload → audit)."""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.models.project import ProjectStatus
from app.parsers.smart_parser import SmartParser
from app.parsers.drawing_specs_parser import DrawingSpecsParser
from app.services.audit_classifier import AuditClassifier
from app.services.position_enricher import PositionEnricher
from app.services.project_cache import (
    load_or_create_project_cache,
    save_field,
    save_project_cache,
)
from app.services.specifications_validator import SpecificationsValidator
from app.validators import PositionValidator
from app.state.project_store import project_store
from app.utils.audit_contracts import build_audit_contract

logger = logging.getLogger(__name__)


def _classify_position(position: Dict[str, Any]) -> str:
    """Classify a position according to validation and enrichment results."""

    if (
        position.get("validation_status") == "failed"
        or position.get("validation_error")
    ):
        return "RED"

    enrichment_block = position.get("enrichment") or {}
    match = (enrichment_block.get("match") or "none").lower()
    if match == "exact":
        return "GREEN"
    if match == "partial":
        return "AMBER"
    if match == "none":
        return "RED"
    return "AMBER"


class WorkflowA:
    """Handle Workflow A initialisation and parsing steps."""

    def __init__(self) -> None:
        self.smart_parser = SmartParser()
        self.drawing_parser = DrawingSpecsParser()
        self.validator = SpecificationsValidator()
        self.audit_classifier = AuditClassifier()
        self.schema_validator = PositionValidator()

    async def execute(
        self,
        project_id: str,
        generate_summary: bool = False,
        enable_enrichment: Optional[bool] = None,
        *,
        action: str = "execute",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run upload handling and parsing for Workflow A."""
        if action != "execute":
            logger.debug(
                "Project %s: Workflow A execute() received action '%s'",
                project_id,
                action,
            )

        if kwargs:
            logger.debug(
                "Project %s: Workflow A execute() received extra kwargs: %s",
                project_id,
                sorted(kwargs.keys()),
            )

        project_meta = self._load_project_metadata(project_id)

        if action != "execute":
            cached_artifact = self._get_cached_artifact(project_meta, action)
            if cached_artifact is not None and not kwargs:
                logger.info(
                    "Project %s: Returning cached Workflow A artifact '%s'",
                    project_id,
                    action,
                )
                return cached_artifact

        logger.info(
            "Project %s: Starting Workflow A Step 1 (upload handling)",
            project_id,
        )

        uploads = self._resolve_uploads(project_id, project_meta)

        base_cache = {
            "project_id": project_id,
            "workflow": "A",
            "files": uploads["files_by_type"],
        }
        cache_data, cache_path, cache_created = load_or_create_project_cache(
            project_id, base_cache
        )

        logger.info(
            "Project %s: Cache %s at %s",
            project_id,
            "created" if cache_created else "loaded",
            cache_path,
        )

        if enable_enrichment is None:
            enable_enrichment = settings.ENRICHMENT_ENABLED

        cache_data["enable_enrichment"] = enable_enrichment

        logger.info(
            "Project %s: Starting Workflow A Step 2 (parsing)",
            project_id,
        )
        parsing_summary = self._parse_cost_documents(
            project_id, uploads["cost_documents"]
        )

        schema_result = self.schema_validator.validate(parsing_summary["positions"])

        logger.info(
            "Project %s: Step 3 schema validation deduplicated=%s invalid=%s duplicates_removed=%s",
            project_id,
            schema_result.stats.get("deduplicated_total", 0),
            schema_result.stats.get("invalid_total", 0),
            schema_result.stats.get("duplicates_removed", 0),
        )

        cache_data["project_id"] = project_id
        cache_data["workflow"] = "A"
        cache_data["files"] = uploads["files_by_type"]
        parsing_summary["diagnostics"]["schema_validation"] = schema_result.stats

        cache_data.setdefault("diagnostics", {})
        cache_data["diagnostics"]["parsing"] = parsing_summary["diagnostics"]
        cache_data["diagnostics"]["schema_validation"] = schema_result.stats

        positions = schema_result.positions
        cache_data["positions"] = positions
        cache_data["documents"] = parsing_summary["documents"]
        cache_data["updated_at"] = datetime.now().isoformat()

        save_project_cache(project_id, cache_data)

        self._update_project_store(
            project_id, parsing_summary, cache_path, uploads
        )

        # ------------------------------------------------------------------
        # Steps 3–6: Drawing enrichment → validation → audit
        # ------------------------------------------------------------------

        drawing_summary = self._extract_drawing_specs(
            project_id, uploads.get("drawing_files", [])
        )

        logger.info(
            "Project %s: Drawing specs detected=%s",
            project_id,
            len(drawing_summary["specifications"]),
        )

        enricher = PositionEnricher(enabled=enable_enrichment)
        enriched_positions, enrichment_stats = enricher.enrich(
            positions, drawing_summary["specifications"]
        )

        validated_positions, validation_stats = self.validator.validate(
            enriched_positions
        )

        audited_positions, audit_stats = self.audit_classifier.classify(
            validated_positions
        )

        logger.info(
            "Project %s: Audit summary GREEN=%s, AMBER=%s, RED=%s",
            project_id,
            audit_stats.get("green", 0),
            audit_stats.get("amber", 0),
            audit_stats.get("red", 0),
        )

        audit_payload = self._build_audit_payload(
            audited_positions,
            enrichment_stats,
            validation_stats,
            audit_stats,
            schema_result.stats,
        )

        totals = audit_payload.get("totals", {})
        meta = audit_payload.get("meta", {})
        audit_meta = meta.get("audit", {})
        preview = audit_payload.get("preview", [])

        cache_data["positions"] = audit_payload.get("items", [])
        cache_data["positions_preview"] = preview
        cache_data["enrichment"] = meta.get("enrichment", {})
        cache_data["validation"] = meta.get("validation", {})
        cache_data["audit"] = audit_meta
        cache_data["audit_results"] = audit_payload
        cache_data["green_count"] = audit_meta.get("green", totals.get("g", 0))
        cache_data["amber_count"] = audit_meta.get("amber", totals.get("a", 0))
        cache_data["red_count"] = audit_meta.get("red", totals.get("r", 0))
        cache_data["drawing_specs"] = drawing_summary
        cache_data["status"] = "AUDITED"
        cache_data["progress"] = 90
        cache_data["message"] = (
            "Parsed + Enriched + Validated + Audited (Steps 1–6). Ready to export."
        )
        cache_data["updated_at"] = datetime.now().isoformat()

        artifacts_bundle = self._build_artifacts(
            project_id=project_id,
            project_meta=project_meta,
            audit_payload=audit_payload,
            parsing_summary=parsing_summary,
            drawing_summary=drawing_summary,
            uploads=uploads,
        )
        if artifacts_bundle:
            cache_data["artifacts"] = artifacts_bundle
            project_meta.setdefault("artifacts", {}).update(artifacts_bundle)

        save_field(project_id, "audit_results", audit_payload)

        logger.info(
            "audit_results normalized: total=%d g=%d a=%d r=%d",
            totals.get("total", 0),
            totals.get("g", 0),
            totals.get("a", 0),
            totals.get("r", 0),
        )

        save_project_cache(project_id, cache_data)

        self._update_project_store_after_audit(
            project_id=project_id,
            cache_path=cache_path,
            uploads=uploads,
            audit_payload=audit_payload,
            enable_enrichment=enable_enrichment,
            parsing_diagnostics=parsing_summary["diagnostics"],
            drawing_diagnostics=drawing_summary["diagnostics"],
            drawing_summary=drawing_summary,
        )

        diagnostics = parsing_summary["diagnostics"]
        logger.info(
            "Project %s: Completed Steps 1–6 → %s document(s), %s positions",
            project_id,
            diagnostics["documents_processed"],
            diagnostics["normalized_total"],
        )

        result = {
            "project_id": project_id,
            "workflow": "A",
            "status": "AUDITED",
            "cache_path": str(cache_path),
            "documents_processed": diagnostics["documents_processed"],
            "positions_total": totals.get("total", len(audited_positions)),
            "parsing": diagnostics,
            "files": uploads["files_by_type"],
            "missing_files": uploads["missing_files"],
            "enrichment": meta.get("enrichment", enrichment_stats),
            "validation": meta.get("validation", validation_stats),
            "audit": audit_meta or audit_stats,
            "audit_results": audit_payload,
            "drawing_specs": drawing_summary["diagnostics"],
            "progress": 90,
            "message": "Parsed + Enriched + Validated + Audited (Steps 1–6). Ready to export.",
        }

        if artifacts_bundle:
            result["artifacts"] = artifacts_bundle

        if action == "execute":
            return result

        artifact = artifacts_bundle.get(action)
        if artifact is None:
            raise ValueError(f"Unknown action for Workflow A: {action}")
        return artifact

    def _build_audit_payload(
        self,
        positions: List[Dict[str, Any]],
        enrichment_stats: Dict[str, Any],
        validation_stats: Dict[str, Any],
        audit_stats: Dict[str, Any],
        schema_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalise audit output for cache, API and export."""

        non_preview_positions: List[Dict[str, Any]] = []
        for pos in positions or []:
            if not isinstance(pos, dict):
                continue
            if pos.get("is_preview") or pos.get("preview"):
                continue
            non_preview_positions.append(pos)

        enriched_payload = build_audit_contract(
            non_preview_positions,
            enrichment_stats=enrichment_stats,
            validation_stats=validation_stats,
            audit_stats=audit_stats,
            schema_stats=schema_stats,
            classify=_classify_position,
        )

        return enriched_payload

    def _build_artifacts(
        self,
        *,
        project_id: str,
        project_meta: Dict[str, Any],
        audit_payload: Dict[str, Any],
        parsing_summary: Dict[str, Any],
        drawing_summary: Dict[str, Any],
        uploads: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Derive Workflow A artifacts from the normalized audit payload."""

        positions = [
            item
            for item in audit_payload.get("items", [])
            if isinstance(item, dict)
        ]
        totals = dict(audit_payload.get("totals") or {})
        meta = dict(audit_payload.get("meta") or {})
        parsing_diagnostics = dict(parsing_summary.get("diagnostics") or {})
        documents = list(parsing_summary.get("documents") or [])

        artifacts = {
            "tech_card": self._build_tech_card_artifact(
                project_id=project_id,
                project_meta=project_meta,
                positions=positions,
                totals=totals,
                meta=meta,
                parsing_diagnostics=parsing_diagnostics,
                documents=documents,
                drawing_summary=drawing_summary or {},
                uploads=uploads or {},
            ),
            "resource_sheet": self._build_resource_sheet_artifact(
                project_id=project_id,
                project_meta=project_meta,
                positions=positions,
                totals=totals,
                meta=meta,
                parsing_diagnostics=parsing_diagnostics,
                documents=documents,
                drawing_summary=drawing_summary or {},
                uploads=uploads or {},
            ),
            "materials": self._build_materials_artifact(
                project_id=project_id,
                project_meta=project_meta,
                positions=positions,
                totals=totals,
                meta=meta,
                parsing_diagnostics=parsing_diagnostics,
                documents=documents,
                drawing_summary=drawing_summary or {},
                uploads=uploads or {},
            ),
        }

        return artifacts

    def _build_tech_card_artifact(
        self,
        *,
        project_id: str,
        project_meta: Dict[str, Any],
        positions: List[Dict[str, Any]],
        totals: Dict[str, Any],
        meta: Dict[str, Any],
        parsing_diagnostics: Dict[str, Any],
        documents: List[Dict[str, Any]],
        drawing_summary: Dict[str, Any],
        uploads: Dict[str, Any],
    ) -> Dict[str, Any]:
        project_name = (
            project_meta.get("project_name")
            or project_meta.get("name")
            or project_id
        )
        now_iso = datetime.now().isoformat()
        totals_block = {
            "green": int(totals.get("g", 0)),
            "amber": int(totals.get("a", 0)),
            "red": int(totals.get("r", 0)),
            "total": int(totals.get("total", len(positions))),
        }

        meta_block = dict(meta)
        audit_meta = dict(meta_block.get("audit") or {})
        if not audit_meta:
            audit_meta = {
                "green": totals_block["green"],
                "amber": totals_block["amber"],
                "red": totals_block["red"],
            }
        validation_stats = dict(meta_block.get("validation") or {})
        enrichment_stats = dict(meta_block.get("enrichment") or {})
        schema_stats = dict(meta_block.get("schema_validation") or {})

        drawing_specs = list(drawing_summary.get("specifications") or [])
        drawing_diagnostics = dict(drawing_summary.get("diagnostics") or {})
        documents_processed = int(parsing_diagnostics.get("documents_processed", len(documents)))

        focus_position = self._select_focus_position(positions)
        focus_overview: Dict[str, Any] = {
            "code": None,
            "description": None,
            "unit": None,
            "quantity": None,
            "status": None,
            "issues": [],
            "provenance": {},
        }
        if focus_position:
            focus_overview = {
                "code": focus_position.get("code"),
                "description": focus_position.get("description"),
                "unit": focus_position.get("unit"),
                "quantity": focus_position.get("quantity"),
                "status": focus_position.get("status"),
                "issues": list(focus_position.get("issues") or []),
                "provenance": dict(focus_position.get("provenance") or {}),
            }

        documents_overview = [
            {
                "filename": doc.get("filename"),
                "file_type": doc.get("file_type"),
                "positions_count": doc.get("positions_count"),
            }
            for doc in documents
            if isinstance(doc, dict)
        ]

        recent_positions = [
            {
                "code": item.get("code"),
                "description": item.get("description"),
                "status": item.get("status"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
            }
            for item in positions[:5]
        ]

        steps = [
            {
                "name": "Cost document parsing",
                "status": "completed",
                "details": {
                    "documents_processed": documents_processed,
                    "raw_positions": parsing_diagnostics.get("raw_total"),
                },
            },
            {
                "name": "Schema validation",
                "status": "completed",
                "details": schema_stats,
            },
            {
                "name": "Drawing enrichment",
                "status": "completed" if drawing_specs else "skipped",
                "details": {
                    "specifications_detected": len(drawing_specs),
                    "files_processed": drawing_diagnostics.get("files_processed", 0),
                },
            },
            {
                "name": "Audit classification",
                "status": "completed",
                "details": audit_meta,
            },
        ]

        tech_card = {
            "type": "tech_card",
            "project_id": project_id,
            "project_name": project_name,
            "workflow": project_meta.get("workflow", "A"),
            "generated_at": now_iso,
            "summary": {
                "positions_total": totals_block["total"],
                "status_breakdown": totals_block,
                "documents_processed": documents_processed,
                "drawing_specs_detected": len(drawing_specs),
            },
            "focus_position": focus_overview,
            "recent_positions": recent_positions,
            "quality": {
                "schema_validation": schema_stats,
                "validation": validation_stats,
                "enrichment": enrichment_stats,
                "audit": audit_meta,
            },
            "source_documents": documents_overview,
            "drawing_diagnostics": drawing_diagnostics,
            "steps": steps,
            "issues": focus_overview.get("issues", []),
        }

        files_by_type = uploads.get("files_by_type")
        if isinstance(files_by_type, dict):
            tech_card["input_files"] = {
                key: len(value) if isinstance(value, list) else 0
                for key, value in files_by_type.items()
            }

        return tech_card

    def _build_resource_sheet_artifact(
        self,
        *,
        project_id: str,
        project_meta: Dict[str, Any],
        positions: List[Dict[str, Any]],
        totals: Dict[str, Any],
        meta: Dict[str, Any],  # noqa: ARG002 - kept for consistent signature
        parsing_diagnostics: Dict[str, Any],
        documents: List[Dict[str, Any]],
        drawing_summary: Dict[str, Any],  # noqa: ARG002
        uploads: Dict[str, Any],
    ) -> Dict[str, Any]:
        project_name = (
            project_meta.get("project_name")
            or project_meta.get("name")
            or project_id
        )
        now_iso = datetime.now().isoformat()

        sections: defaultdict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in positions:
            provenance = item.get("provenance") or {}
            section_name = provenance.get("section") or "Unassigned"
            sections[section_name].append(item)

        section_payload: List[Dict[str, Any]] = []
        for section_name in sorted(sections.keys()):
            section_positions = sections[section_name]
            status_counts = Counter(
                ((pos.get("status") or "UNKNOWN").upper()) for pos in section_positions
            )
            total_quantity = 0.0
            for pos in section_positions:
                quantity = pos.get("quantity")
                if isinstance(quantity, (int, float)):
                    total_quantity += float(quantity)

            section_payload.append(
                {
                    "section": section_name,
                    "positions_count": len(section_positions),
                    "status_breakdown": {
                        "green": status_counts.get("GREEN", 0),
                        "amber": status_counts.get("AMBER", 0),
                        "red": status_counts.get("RED", 0),
                    },
                    "total_quantity": total_quantity,
                    "positions": [
                        {
                            "code": pos.get("code"),
                            "description": pos.get("description"),
                            "unit": pos.get("unit"),
                            "quantity": pos.get("quantity"),
                            "status": pos.get("status"),
                        }
                        for pos in section_positions[:20]
                    ],
                }
            )

        flagged_positions = sum(
            1
            for pos in positions
            if (pos.get("status") or "").upper() in {"AMBER", "RED"}
        )

        documents_payload = [
            {
                "filename": doc.get("filename"),
                "file_type": doc.get("file_type"),
                "positions_count": doc.get("positions_count"),
            }
            for doc in documents
            if isinstance(doc, dict)
        ]

        files_snapshot: List[Dict[str, Any]] = []
        files_by_type = uploads.get("files_by_type")
        if isinstance(files_by_type, dict):
            for file_type, entries in files_by_type.items():
                files_snapshot.append(
                    {
                        "file_type": file_type,
                        "count": len(entries) if isinstance(entries, list) else 0,
                    }
                )

        resource_sheet = {
            "type": "resource_sheet",
            "project_id": project_id,
            "project_name": project_name,
            "workflow": project_meta.get("workflow", "A"),
            "generated_at": now_iso,
            "summary": {
                "total_positions": len(positions),
                "sections": len(section_payload),
                "flagged_positions": flagged_positions,
                "documents_processed": int(
                    parsing_diagnostics.get("documents_processed", len(documents))
                ),
                "status_breakdown": {
                    "green": int(totals.get("g", 0)),
                    "amber": int(totals.get("a", 0)),
                    "red": int(totals.get("r", 0)),
                },
            },
            "sections": section_payload,
            "documents": documents_payload,
            "files": files_snapshot,
        }

        return resource_sheet

    def _build_materials_artifact(
        self,
        *,
        project_id: str,
        project_meta: Dict[str, Any],
        positions: List[Dict[str, Any]],
        totals: Dict[str, Any],
        meta: Dict[str, Any],  # noqa: ARG002
        parsing_diagnostics: Dict[str, Any],  # noqa: ARG002
        documents: List[Dict[str, Any]],  # noqa: ARG002
        drawing_summary: Dict[str, Any],
        uploads: Dict[str, Any],  # noqa: ARG002
    ) -> Dict[str, Any]:
        project_name = (
            project_meta.get("project_name")
            or project_meta.get("name")
            or project_id
        )
        now_iso = datetime.now().isoformat()

        unit_totals: defaultdict[str, float] = defaultdict(float)
        status_counts = Counter()
        issues_total = 0
        for item in positions:
            status = (item.get("status") or "GREEN").upper()
            status_counts[status] += 1
            issues_total += len(item.get("issues") or [])
            quantity = item.get("quantity")
            if isinstance(quantity, (int, float)):
                unit = str(item.get("unit") or "").strip() or "UNSPECIFIED"
                unit_totals[unit] += float(quantity)

        unit_summary = [
            {
                "unit": unit,
                "quantity": round(total, 6),
            }
            for unit, total in sorted(unit_totals.items())
        ]

        top_positions = sorted(
            [
                item
                for item in positions
                if isinstance(item.get("quantity"), (int, float))
            ],
            key=lambda item: float(item.get("quantity") or 0),
            reverse=True,
        )[:10]

        top_payload = [
            {
                "code": item.get("code"),
                "description": item.get("description"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
                "status": item.get("status"),
                "issues": list(item.get("issues") or []),
            }
            for item in top_positions
        ]

        drawing_specs = list(drawing_summary.get("specifications") or [])
        drawing_diag = dict(drawing_summary.get("diagnostics") or {})

        materials = {
            "type": "material_analysis",
            "project_id": project_id,
            "project_name": project_name,
            "workflow": project_meta.get("workflow", "A"),
            "generated_at": now_iso,
            "summary": {
                "total_positions": len(positions),
                "status_breakdown": {
                    "green": status_counts.get("GREEN", int(totals.get("g", 0))),
                    "amber": status_counts.get("AMBER", int(totals.get("a", 0))),
                    "red": status_counts.get("RED", int(totals.get("r", 0))),
                },
                "units_tracked": len(unit_summary),
                "issues_detected": issues_total,
            },
            "unit_totals": unit_summary,
            "top_positions": top_payload,
            "drawing_context": {
                "specifications_detected": len(drawing_specs),
                "files_processed": drawing_diag.get("files_processed", 0),
            },
        }

        return materials

    @staticmethod
    def _select_focus_position(
        positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        for item in positions:
            status = (item.get("status") or "").upper()
            if status in {"AMBER", "RED"}:
                return item
        return positions[0] if positions else {}

    @staticmethod
    def _get_cached_artifact(
        project_meta: Dict[str, Any], action: str
    ) -> Optional[Dict[str, Any]]:
        artifacts = project_meta.get("artifacts")
        if isinstance(artifacts, dict):
            cached = artifacts.get(action)
            if cached is not None:
                return cached
        return None

    @staticmethod
    def _load_project_metadata(project_id: str) -> Dict[str, Any]:
        project_meta = project_store.get(project_id)
        if not project_meta:
            raise ValueError(f"Project {project_id} not found in store")
        return project_meta

    def _resolve_uploads(
        self, project_id: str, project_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        file_locations = project_meta.get("file_locations") or {}
        metadata_list = project_meta.get("files_metadata") or []

        files_by_type: Dict[str, List[Dict[str, Any]]] = {
            "vykaz_vymer": [],
            "rozpocet": [],
            "vykresy": [],
            "dokumentace": [],
            "zmeny": [],
        }
        all_files: List[Dict[str, Any]] = []
        missing_files: List[Dict[str, Any]] = []

        for meta in metadata_list:
            file_type = meta.get("file_type", "unknown")
            file_id = meta.get("file_id")
            path_str = file_locations.get(file_id)

            if not path_str:
                logger.warning(
                    "Project %s: Missing stored path for %s (%s)",
                    project_id,
                    meta.get("filename"),
                    file_type,
                )
                missing_files.append(
                    {
                        "filename": meta.get("filename"),
                        "file_type": file_type,
                        "reason": "missing_location",
                    }
                )
                continue

            path = Path(path_str)
            exists = path.exists()
            relative_path = self._safe_relative_path(path)

            file_entry = {
                "filename": meta.get("filename"),
                "file_type": file_type,
                "path": str(path),
                "relative_path": relative_path,
                "size": meta.get("size", 0),
                "uploaded_at": meta.get("uploaded_at"),
                "exists": exists,
            }

            if not exists:
                logger.warning(
                    "Project %s: File not found on disk %s (%s)",
                    project_id,
                    path,
                    file_type,
                )
                missing_files.append(
                    {
                        "filename": meta.get("filename"),
                        "file_type": file_type,
                        "path": str(path),
                        "reason": "file_missing",
                    }
                )

            files_by_type.setdefault(file_type, []).append(file_entry)
            all_files.append(file_entry)

        cost_documents = (
            files_by_type.get("vykaz_vymer", [])
            + files_by_type.get("rozpocet", [])
        )
        drawing_files = files_by_type.get("vykresy", [])

        logger.info(
            "Project %s: Resolved %s cost document(s) and %s drawing(s)",
            project_id,
            len(cost_documents),
            len(drawing_files),
        )

        if missing_files:
            logger.info(
                "Project %s: %s file(s) marked as missing",
                project_id,
                len(missing_files),
            )

        return {
            "files_by_type": files_by_type,
            "cost_documents": cost_documents,
            "drawing_files": drawing_files,
            "all_files": all_files,
            "missing_files": missing_files,
        }

    def _parse_cost_documents(
        self, project_id: str, cost_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        positions: List[Dict[str, Any]] = []
        documents: List[Dict[str, Any]] = []
        diagnostics: Dict[str, Any] = {
            "documents_processed": 0,
            "raw_total": 0,
            "normalized_total": 0,
            "skipped_total": 0,
            "total_positions": 0,
            "files": [],
            "errors": [],
        }

        if not cost_documents:
            logger.warning(
                "Project %s: No Rozpočet or Výkaz výmer files found for parsing",
                project_id,
            )
            return {
                "positions": positions,
                "documents": documents,
                "diagnostics": diagnostics,
            }

        for doc in cost_documents:
            if not doc.get("exists"):
                diagnostics["errors"].append(
                    {
                        "filename": doc.get("filename"),
                        "file_type": doc.get("file_type"),
                        "error": "file_missing",
                    }
                )
                continue

            file_path = Path(doc["path"])
            logger.info(
                "Project %s: Parsing %s (%s)",
                project_id,
                doc.get("filename"),
                doc.get("file_type"),
            )

            try:
                parsed = self.smart_parser.parse(file_path, project_id=project_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Project %s: Failed parsing %s (%s): %s",
                    project_id,
                    doc.get("filename"),
                    doc.get("file_type"),
                    exc,
                )
                diagnostics["errors"].append(
                    {
                        "filename": doc.get("filename"),
                        "file_type": doc.get("file_type"),
                        "error": str(exc),
                    }
                )
                continue

            file_positions = parsed.get("positions") or []
            doc_info = parsed.get("document_info") or {}
            doc_diag = parsed.get("diagnostics") or {}

            documents.append(
                {
                    "filename": doc.get("filename"),
                    "file_type": doc.get("file_type"),
                    "document_info": doc_info,
                    "positions_count": len(file_positions),
                }
            )

            diagnostics["files"].append(
                {
                    "filename": doc.get("filename"),
                    "file_type": doc.get("file_type"),
                    "document_info": doc_info,
                    "diagnostics": doc_diag,
                    "positions_count": len(file_positions),
                }
            )

            diagnostics["raw_total"] += doc_diag.get(
                "raw_total", len(file_positions)
            )
            diagnostics["normalized_total"] += doc_diag.get(
                "normalized_total", len(file_positions)
            )
            diagnostics["skipped_total"] += doc_diag.get("skipped_total", 0)

            positions.extend(file_positions)

            logger.info(
                "Project %s: Parsed %s positions from %s",
                project_id,
                doc_diag.get("normalized_total", len(file_positions)),
                doc.get("filename"),
            )

        diagnostics["documents_processed"] = len(documents)
        diagnostics["total_positions"] = len(positions)

        return {
            "positions": positions,
            "documents": documents,
            "diagnostics": diagnostics,
        }

    def _update_project_store(
        self,
        project_id: str,
        parsing_summary: Dict[str, Any],
        cache_path: Path,
        uploads: Dict[str, Any],
    ) -> None:
        now_iso = datetime.now().isoformat()
        diagnostics = parsing_summary["diagnostics"]
        total_positions = len(parsing_summary["positions"])

        project_meta = project_store.get(project_id)
        if not project_meta:
            project_store[project_id] = {
                "project_id": project_id,
                "workflow": "A",
                "status": ProjectStatus.PARSED,
                "created_at": now_iso,
                "updated_at": now_iso,
                "progress": 50,
                "positions_total": total_positions,
                "positions_processed": total_positions,
                "positions_raw": diagnostics.get("raw_total", total_positions),
                "positions_skipped": diagnostics.get("skipped_total", 0),
                "diagnostics": {"parsing": diagnostics},
                "cache_path": str(cache_path),
                "files_snapshot": uploads["files_by_type"],
                "missing_files": uploads["missing_files"],
                "green_count": 0,
                "amber_count": 0,
                "red_count": 0,
                "message": "Cost documents parsed",
                "error": None,
            }
            return

        project_meta["status"] = ProjectStatus.PARSED
        project_meta["progress"] = max(project_meta.get("progress", 0), 50)
        project_meta["positions_total"] = total_positions
        project_meta["positions_processed"] = total_positions
        project_meta["positions_raw"] = diagnostics.get(
            "raw_total", total_positions
        )
        project_meta["positions_skipped"] = diagnostics.get("skipped_total", 0)
        project_meta["updated_at"] = now_iso
        project_meta["cache_path"] = str(cache_path)
        project_meta.setdefault("diagnostics", {})
        project_meta["diagnostics"]["parsing"] = diagnostics
        project_meta["files_snapshot"] = uploads["files_by_type"]
        project_meta["missing_files"] = uploads["missing_files"]
        project_meta["message"] = "Cost documents parsed"
        project_meta["error"] = None

    @staticmethod
    def _safe_relative_path(path: Path) -> str:
        try:
            return str(path.relative_to(settings.DATA_DIR))
        except ValueError:
            return path.name

    def _extract_drawing_specs(
        self, project_id: str, drawing_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not drawing_files:
            logger.info("Project %s: No drawing files available for enrichment", project_id)
            return {"specifications": [], "diagnostics": {"files_processed": 0, "specifications_found": 0, "errors": []}}

        logger.info(
            "Project %s: Extracting drawing specifications from %s file(s)",
            project_id,
            len(drawing_files),
        )

        result = self.drawing_parser.parse_files(drawing_files)

        return result

    def _update_project_store_after_audit(
        self,
        project_id: str,
        cache_path: Path,
        uploads: Dict[str, Any],
        audit_payload: Dict[str, Any],
        enable_enrichment: bool,
        parsing_diagnostics: Dict[str, Any],
        drawing_diagnostics: Dict[str, Any],
        drawing_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        now_iso = datetime.now().isoformat()
        project_meta = project_store.setdefault(project_id, {})

        items = audit_payload.get("items", [])
        totals = audit_payload.get("totals", {})
        meta = audit_payload.get("meta", {})
        enrichment_stats = meta.get("enrichment", {})
        validation_stats = meta.get("validation", {})
        schema_stats = meta.get("schema_validation", {})
        audit_stats = meta.get("audit") or {
            "green": totals.get("g", 0),
            "amber": totals.get("a", 0),
            "red": totals.get("r", 0),
        }
        positions_preview = audit_payload.get("preview") or items[:100]
        total_positions = totals.get("total", len(items))

        project_meta.update(
            {
                "project_id": project_id,
                "workflow": "A",
                "status": ProjectStatus.AUDITED,
                "updated_at": now_iso,
                "progress": 90,
                "cache_path": str(cache_path),
                "files_snapshot": uploads.get("files_by_type", {}),
                "missing_files": uploads.get("missing_files", []),
                "positions_total": total_positions,
                "positions_processed": total_positions,
                "green_count": audit_stats.get("green", totals.get("g", 0)),
                "amber_count": audit_stats.get("amber", totals.get("a", 0)),
                "red_count": audit_stats.get("red", totals.get("r", 0)),
                "enable_enrichment": enable_enrichment,
                "message": "Parsed + Enriched + Validated + Audited (Steps 1–6). Ready to export.",
            }
        )

        project_meta.setdefault("diagnostics", {})
        project_meta["diagnostics"].update(
            {
                "parsing": parsing_diagnostics,
                "drawing_specs": drawing_diagnostics,
                "enrichment": enrichment_stats,
                "validation": validation_stats,
                "audit": audit_stats,
                "schema_validation": schema_stats,
            }
        )

        project_meta["audit_results"] = audit_payload
        project_meta["positions_preview"] = positions_preview

        drawing_summary = drawing_summary or {}
        drawing_spec_count = len(drawing_summary.get("specifications", []))
        page_states = dict(drawing_summary.get("diagnostics", {}).get("page_states", {}))
        page_states.setdefault("status", "completed")
        recovery_meta = {
            "used_pdfium": drawing_summary.get("used_pdfium", 0),
            "used_poppler": drawing_summary.get("used_poppler", 0),
            "ocr_pages": drawing_summary.get("ocr_pages", []),
        }

        project_meta["drawing_specs_detected"] = drawing_spec_count
        project_meta["drawing_page_states"] = {
            "good_text": page_states.get("good_text", 0),
            "encoded_text": page_states.get("encoded_text", 0),
            "image_only": page_states.get("image_only", 0),
            "status": page_states.get("status", "completed"),
        }
        project_meta["drawing_text_recovery"] = recovery_meta

        project_meta["summary"] = {
            "positions_total": total_positions,
            "green": audit_stats.get("green", totals.get("g", 0)),
            "amber": audit_stats.get("amber", totals.get("a", 0)),
            "red": audit_stats.get("red", totals.get("r", 0)),
        }


class WorkflowAService:
    """Синглтон сервис для Workflow A"""

    def __init__(self):
        self._workflows = {}  # Кэш активных workflow

    async def run(
        self, project_id: str, action: str = "execute", **kwargs: Any
    ) -> Dict[str, Any]:
        """Dispatch all actions through WorkflowA.execute"""

        workflow = self._workflows.get(project_id)
        if workflow is None:
            workflow = WorkflowA()
            self._workflows[project_id] = workflow

        return await workflow.execute(
            project_id=project_id,
            action=action,
            **kwargs,
        )

    async def execute(self, project_id: str, **kwargs):
        """Алиас для совместимости"""
        return await self.run(project_id, **kwargs)


# Создаём синглтон
workflow_a = WorkflowAService()


# Экспортируем
__all__ = ['WorkflowA', 'workflow_a']
