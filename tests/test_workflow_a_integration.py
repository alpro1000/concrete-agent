"""
Test workflow_a integration with routes
Validates the fix for ImportError and method signature
"""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


def test_workflow_a_import():
    """Test that workflow_a instance can be imported"""
    from app.services.workflow_a import workflow_a
    
    assert workflow_a is not None
    assert hasattr(workflow_a, 'run')
    print("✅ workflow_a instance imported successfully")


def test_workflow_a_method_signature():
    """Test that run() method has correct signature"""
    import inspect
    from app.services.workflow_a import workflow_a
    
    sig = inspect.signature(workflow_a.run)
    params = list(sig.parameters.keys())
    
    assert 'project_id' in params
    assert 'action' in params
    
    param_project_id = sig.parameters['project_id']
    param_action = sig.parameters['action']
    param_kwargs = sig.parameters['kwargs']
    
    def _normalize(annotation):
        return str if annotation == 'str' else annotation

    assert _normalize(param_project_id.annotation) is str
    assert _normalize(param_action.annotation) is str
    assert param_action.default == 'execute'
    assert param_kwargs.kind == inspect.Parameter.VAR_KEYWORD
    
    print("✅ run() method signature is correct")
    print(f"   Signature: {sig}")


def test_workflow_a_routes_import():
    """Test that routes.py can import workflow_a"""
    try:
        from app.api.routes_workflow_a import workflow_a
        assert workflow_a is not None
        print("✅ workflow_a imported in routes_workflow_a.py")
    except ImportError as e:
        pytest.fail(f"Failed to import workflow_a in routes_workflow_a: {e}")


def test_workflow_a_run_with_invalid_project():
    """Test that run() raises error for invalid project_id"""
    from app.services.workflow_a import workflow_a

    async def _invoke() -> None:
        await workflow_a.run(project_id="nonexistent-id")

    workflow_a._workflows.clear()
    with pytest.raises(ValueError, match="not found in store"):
        asyncio.run(_invoke())
    workflow_a._workflows.clear()

    print("✅ run() correctly raises error for invalid project")


def test_workflow_a_run_with_mock_project():
    """Test that run() forwards calls to WorkflowA.execute"""
    from app.services.workflow_a import workflow_a, WorkflowA

    test_project_id = "test-project-123"

    async def _invoke():
        return await workflow_a.run(
            project_id=test_project_id,
            action="tech_card",
            extra_option=True,
        )

    workflow_a._workflows.clear()
    with patch.object(WorkflowA, 'execute', new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = {"success": True, "artifact": "tech_card"}
        result = asyncio.run(_invoke())

    assert result == {"success": True, "artifact": "tech_card"}
    mock_execute.assert_awaited_once_with(
        project_id=test_project_id,
        action="tech_card",
        extra_option=True,
    )
    workflow_a._workflows.clear()

    print("✅ run() executed via WorkflowA.execute with forwarded kwargs")


def test_workflow_a_build_artifacts_structure():
    """WorkflowA can derive artifacts from the audit payload."""
    from app.services.workflow_a import WorkflowA

    workflow = WorkflowA()
    project_meta = {"project_id": "demo", "project_name": "Demo Project", "workflow": "A"}

    audit_payload = {
        "items": [
            {
                "code": "P-001",
                "description": "Concrete works",
                "unit": "m3",
                "quantity": 12.5,
                "status": "AMBER",
                "issues": ["Missing reinforcement specification"],
                "provenance": {"section": "SO-101"},
            },
            {
                "code": "P-002",
                "description": "Formwork",
                "unit": "m2",
                "quantity": 45,
                "status": "GREEN",
                "issues": [],
                "provenance": {"section": "SO-101"},
            },
        ],
        "totals": {"g": 1, "a": 1, "r": 0, "total": 2},
        "meta": {
            "audit": {"green": 1, "amber": 1, "red": 0},
            "validation": {"invalid_total": 0},
            "enrichment": {"matched": 1},
            "schema_validation": {"duplicates_removed": 0},
        },
    }

    parsing_summary = {
        "diagnostics": {"documents_processed": 1, "raw_total": 2, "normalized_total": 2},
        "documents": [
            {
                "filename": "vykaz.xlsx",
                "file_type": "vykaz_vymer",
                "positions_count": 2,
            }
        ],
    }

    drawing_summary = {
        "specifications": [{"id": "D-1"}],
        "diagnostics": {"files_processed": 1},
    }

    uploads = {"files_by_type": {"vykaz_vymer": [{}], "rozpocet": []}}

    artifacts = workflow._build_artifacts(
        project_id="demo",
        project_meta=project_meta,
        audit_payload=audit_payload,
        parsing_summary=parsing_summary,
        drawing_summary=drawing_summary,
        uploads=uploads,
    )

    assert set(artifacts.keys()) == {"tech_card", "resource_sheet", "materials"}

    tech_card = artifacts["tech_card"]
    assert tech_card["type"] == "tech_card"
    assert tech_card["summary"]["positions_total"] == 2
    assert tech_card["focus_position"]["status"] == "AMBER"

    resource_sheet = artifacts["resource_sheet"]
    assert resource_sheet["summary"]["flagged_positions"] == 1
    assert resource_sheet["sections"]

    materials = artifacts["materials"]
    assert materials["type"] == "material_analysis"
    assert any(entry["unit"] == "m3" for entry in materials["unit_totals"])


def test_workflow_a_execute_returns_requested_artifact(monkeypatch):
    """execute() should return specialised artifact responses when requested."""
    from app.services.workflow_a import WorkflowA, project_store

    workflow = WorkflowA()
    project_id = "artifact-project"
    project_store[project_id] = {
        "project_id": project_id,
        "workflow": "A",
        "file_locations": {},
        "files_metadata": [],
    }

    monkeypatch.setattr(
        "app.services.workflow_a.load_or_create_project_cache",
        lambda project_id, base_cache: ({}, Path("/tmp/cache.json"), True),
    )
    monkeypatch.setattr(
        "app.services.workflow_a.save_project_cache",
        lambda project_id, cache: None,
    )
    monkeypatch.setattr(
        "app.services.workflow_a.save_field",
        lambda project_id, field, value: None,
    )

    def _fake_resolve(self, _project_id, _project_meta):
        return {
            "files_by_type": {},
            "cost_documents": [],
            "drawing_files": [],
            "all_files": [],
            "missing_files": [],
        }

    monkeypatch.setattr(WorkflowA, "_resolve_uploads", _fake_resolve)

    def _fake_parse(self, _project_id, _docs):
        return {
            "positions": [],
            "documents": [],
            "diagnostics": {
                "documents_processed": 0,
                "raw_total": 0,
                "normalized_total": 0,
                "skipped_total": 0,
                "total_positions": 0,
                "files": [],
                "errors": [],
            },
        }

    monkeypatch.setattr(WorkflowA, "_parse_cost_documents", _fake_parse)

    class _DummySchemaResult:
        def __init__(self):
            self.positions = []
            self.stats = {}

    monkeypatch.setattr(
        workflow.schema_validator,
        "validate",
        lambda positions: _DummySchemaResult(),
    )
    monkeypatch.setattr(
        workflow.validator,
        "validate",
        lambda positions: (positions, {}),
    )
    monkeypatch.setattr(
        workflow.audit_classifier,
        "classify",
        lambda positions: (positions, {}),
    )

    class _DummyEnricher:
        def __init__(self, enabled: bool = True) -> None:
            self.enabled = enabled

        def enrich(self, positions, specs):
            return positions, {}

    monkeypatch.setattr("app.services.workflow_a.PositionEnricher", _DummyEnricher)
    monkeypatch.setattr(
        workflow.drawing_parser,
        "parse_files",
        lambda drawing_files: {"specifications": [], "diagnostics": {}},
    )

    artifacts_stub = {
        "tech_card": {"type": "tech_card"},
        "resource_sheet": {"type": "resource_sheet"},
        "materials": {"type": "material_analysis"},
    }

    monkeypatch.setattr(
        WorkflowA,
        "_build_artifacts",
        lambda self, **kwargs: artifacts_stub,
    )

    async def _invoke():
        return await workflow.execute(project_id, action="tech_card")

    result = asyncio.run(_invoke())

    assert result == {"type": "tech_card"}
    assert project_store[project_id]["artifacts"]["tech_card"] == {"type": "tech_card"}

    project_store.pop(project_id, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
