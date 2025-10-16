"""Utilities to normalise audit result payloads."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from app.core.config import settings


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return 0.0
    text = str(value).strip().replace(" ", "")
    if not text:
        return 0.0
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _normalise_classification(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"GREEN", "AMBER", "RED"}:
        return text
    return "GREEN"


def _collect_notes(position: Dict[str, Any]) -> str | None:
    buckets: List[str] = []

    def _extend(item: Any) -> None:
        if isinstance(item, str):
            text = item.strip()
            if text:
                buckets.append(text)
        elif isinstance(item, (list, tuple, set)):
            for entry in item:
                _extend(entry)

    for key in ("notes", "reason", "audit_notes", "compliance_notes"):
        _extend(position.get(key))

    if isinstance(position.get("issues"), list):
        _extend(position["issues"])

    validation_results = position.get("validation_results")
    if isinstance(validation_results, dict):
        for key in ("errors", "warnings"):
            _extend(validation_results.get(key))

    unique: List[str] = []
    seen = set()
    for note in buckets:
        if note not in seen:
            seen.add(note)
            unique.append(note)

    if not unique:
        return None

    return "; ".join(unique)


def _ensure_enrichment_block(position: Dict[str, Any]) -> Dict[str, Any]:
    block = position.get("enrichment")
    if isinstance(block, dict):
        evidence = block.get("evidence") or []
        if isinstance(evidence, list):
            block["evidence"] = evidence[: settings.ENRICH_MAX_EVIDENCE]
        match = str(block.get("match") or "").lower()
        if match not in {"exact", "partial", "none"}:
            status = str(position.get("enrichment_status") or "").lower()
            if status == "matched":
                block["match"] = "exact"
            elif status == "partial":
                block["match"] = "partial"
            else:
                block["match"] = "none"
        score = block.get("score")
        try:
            block["score"] = round(float(score or 0.0), 4)
        except (TypeError, ValueError):
            block["score"] = 0.0
        return block

    status = str(position.get("enrichment_status") or "").lower()
    match: str
    if status == "matched":
        match = "exact"
    elif status == "partial":
        match = "partial"
    else:
        match = "none"

    score = position.get("enrichment_score") or position.get("enrichment_confidence") or 0.0
    try:
        score_value = round(float(score or 0.0), 4)
    except (TypeError, ValueError):
        score_value = 0.0

    return {"match": match, "score": score_value, "evidence": []}


def build_flat_positions(positions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert raw position list into the export contract structure."""

    flattened: List[Dict[str, Any]] = []
    for index, raw_position in enumerate(positions or [], start=1):
        if not isinstance(raw_position, dict):
            continue

        entry = dict(raw_position)
        position_id = (
            entry.get("position_id")
            or entry.get("id")
            or entry.get("position_number")
            or entry.get("code")
            or f"pos-{index:04d}"
        )
        entry["position_id"] = str(position_id)
        entry["code"] = entry.get("code") or entry.get("position_code") or ""
        entry["description"] = entry.get("description") or entry.get("name") or ""
        entry["unit"] = entry.get("unit") or entry.get("unit_of_measure") or ""
        entry["quantity"] = _to_float(entry.get("quantity"))
        entry["section"] = entry.get("section") or entry.get("section_name") or ""
        classification = _normalise_classification(
            entry.get("classification") or entry.get("audit")
        )
        entry["classification"] = classification
        entry["notes"] = _collect_notes(entry)

        enrichment_block = _ensure_enrichment_block(entry)
        entry["enrichment"] = enrichment_block

        match = enrichment_block.get("match") or "none"
        if match == "exact":
            entry["enrichment_status"] = "matched"
        elif match == "partial":
            entry["enrichment_status"] = "partial"
        else:
            entry["enrichment_status"] = "unmatched"
        entry["enrichment_score"] = enrichment_block.get("score", 0.0)

        flattened.append(entry)

    return flattened


def summarise_totals(positions: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    positions_list = list(positions)
    totals = {"green": 0, "amber": 0, "red": 0}
    for position in positions_list:
        label = _normalise_classification(position.get("classification"))
        if label in totals:
            totals[label.lower()] += 1
    totals["total_positions"] = len(positions_list)
    return totals


def ensure_audit_contract(
    audit_results: Dict[str, Any] | None,
    fallback_positions: Iterable[Dict[str, Any]] | None = None,
) -> Tuple[Dict[str, Any], bool]:
    """Return audit payload matching the flat export contract.

    Args:
        audit_results: Raw audit payload.
        fallback_positions: Optional list of positions if payload misses them.

    Returns:
        Tuple of (normalised_payload, changed_flag).
    """

    payload = dict(audit_results or {})
    changed = False

    positions = payload.get("positions")
    if not isinstance(positions, list) or not positions:
        positions = list(fallback_positions or [])
        if positions:
            changed = True

    flattened = build_flat_positions(positions)
    if flattened != positions:
        changed = True

    totals = summarise_totals(flattened)

    if payload.get("total_positions") != totals["total_positions"]:
        payload["total_positions"] = totals["total_positions"]
        changed = True
    if payload.get("green") != totals["green"]:
        payload["green"] = totals["green"]
        changed = True
    if payload.get("amber") != totals["amber"]:
        payload["amber"] = totals["amber"]
        changed = True
    if payload.get("red") != totals["red"]:
        payload["red"] = totals["red"]
        changed = True

    payload["positions"] = flattened
    preview = flattened[:100]
    if payload.get("positions_preview") != preview:
        payload["positions_preview"] = preview
        changed = True

    payload.setdefault("enrichment_stats", {})
    payload.setdefault("validation_stats", {})
    payload.setdefault("schema_validation", {})
    payload.setdefault("audit", {
        "green": payload.get("green", 0),
        "amber": payload.get("amber", 0),
        "red": payload.get("red", 0),
    })

    return payload, changed
