"""Workflow A - Steps 1 & 2 implementation (upload + parsing)."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings
from app.models.project import ProjectStatus
from app.parsers.smart_parser import SmartParser
from app.services.project_cache import load_or_create_project_cache, save_project_cache
from app.state.project_store import project_store

logger = logging.getLogger(__name__)


class WorkflowA:
    """Handle Workflow A initialisation and parsing steps."""

    def __init__(self) -> None:
        self.smart_parser = SmartParser()

    async def execute(
        self,
        project_id: str,
        generate_summary: bool = False,
        enable_enrichment: bool = False,
    ) -> Dict[str, Any]:
        """Run upload handling and parsing for Workflow A."""
        logger.info(
            "Project %s: Starting Workflow A Step 1 (upload handling)",
            project_id,
        )

        project_meta = self._load_project_metadata(project_id)
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

        logger.info(
            "Project %s: Starting Workflow A Step 2 (parsing)",
            project_id,
        )
        parsing_summary = self._parse_cost_documents(
            project_id, uploads["cost_documents"]
        )

        cache_data["project_id"] = project_id
        cache_data["workflow"] = "A"
        cache_data["files"] = uploads["files_by_type"]
        cache_data.setdefault("diagnostics", {})
        cache_data["positions"] = parsing_summary["positions"]
        cache_data["documents"] = parsing_summary["documents"]
        cache_data["diagnostics"]["parsing"] = parsing_summary["diagnostics"]
        cache_data["updated_at"] = datetime.now().isoformat()

        save_project_cache(project_id, cache_data)

        self._update_project_store(
            project_id, parsing_summary, cache_path, uploads
        )

        diagnostics = parsing_summary["diagnostics"]
        logger.info(
            "Project %s: Completed Steps 1-2 → %s document(s), %s positions",
            project_id,
            diagnostics["documents_processed"],
            diagnostics["normalized_total"],
        )

        return {
            "project_id": project_id,
            "workflow": "A",
            "status": ProjectStatus.PARSED.value,
            "cache_path": str(cache_path),
            "documents_processed": diagnostics["documents_processed"],
            "positions_total": len(parsing_summary["positions"]),
            "parsing": diagnostics,
            "files": uploads["files_by_type"],
            "missing_files": uploads["missing_files"],
        }

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
