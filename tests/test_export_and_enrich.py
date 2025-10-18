import types
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.position_enricher import PositionEnricher
from app.services.workflow_a import _classify_position


def _build_audit_payload(positions):
    classifications = [_classify_position(position) for position in positions]
    return {
        "positions": positions,
        "total_positions": len(positions),
        "green": classifications.count("GREEN"),
        "amber": classifications.count("AMBER"),
        "red": classifications.count("RED"),
    }


def test_export_contract_not_empty():
    sample_positions = [
        {"validation_status": "ok", "enrichment": {"match": "exact"}},
        {"validation_status": "ok", "enrichment": {"match": "partial"}},
        {"validation_status": "failed", "enrichment": {"match": "none"}},
    ]

    audit = _build_audit_payload(sample_positions)
    assert audit["total_positions"] > 0
    assert {"green", "amber", "red", "positions"} <= set(audit.keys())
    assert audit["green"] == 1
    assert audit["amber"] == 1
    assert audit["red"] == 1


def test_classification_logic_examples():
    red = {"validation_status": "failed"}
    exact = {"validation_status": "ok", "enrichment": {"match": "exact"}}
    partial = {"validation_status": "ok", "enrichment": {"match": "partial"}}
    none = {"validation_status": "ok", "enrichment": {"match": "none"}}

    assert _classify_position(red) == "RED"
    assert _classify_position(exact) == "GREEN"
    assert _classify_position(partial) == "AMBER"
    assert _classify_position(none) == "RED"


def test_enrichment_optional_no_kb():
    empty_kb = types.SimpleNamespace(kb_b1={})
    enricher = PositionEnricher(enabled=True, kb_loader=empty_kb)
    enriched, _ = enricher.enrich([{"description": "", "unit": "m3"}], drawing_payload=[])
    match = enriched[0]["enrichment"]["match"]
    assert match in {"none", "partial", "exact"}
