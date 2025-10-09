"""
Test workflow_a integration with routes
Validates the fix for ImportError and method signature
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


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
    
    # Should have project_id and calculate_resources (excluding self)
    assert 'project_id' in params
    assert 'calculate_resources' in params
    
    # Check parameter types
    param_project_id = sig.parameters['project_id']
    param_calc_resources = sig.parameters['calculate_resources']
    
    assert param_project_id.annotation == str
    assert param_calc_resources.annotation == bool
    assert param_calc_resources.default == False
    
    print("✅ run() method signature is correct")
    print(f"   Signature: {sig}")


def test_workflow_a_routes_import():
    """Test that routes.py can import workflow_a"""
    try:
        from app.api.routes import workflow_a
        assert workflow_a is not None
        print("✅ workflow_a imported in routes.py")
    except ImportError as e:
        pytest.fail(f"Failed to import workflow_a in routes: {e}")


@pytest.mark.asyncio
async def test_workflow_a_run_with_invalid_project():
    """Test that run() raises error for invalid project_id"""
    from app.services.workflow_a import workflow_a
    
    with pytest.raises(ValueError, match="not found in database"):
        await workflow_a.run(project_id="nonexistent-id", calculate_resources=False)
    
    print("✅ run() correctly raises error for invalid project")


@pytest.mark.asyncio
async def test_workflow_a_run_with_mock_project():
    """Test that run() can be called with correct signature"""
    from app.services.workflow_a import workflow_a, WorkflowA
    from app.api import routes
    
    # Create a mock project
    test_project_id = "test-project-123"
    test_file_path = Path("/tmp/test_vykaz.xlsx")
    
    # Create mock file
    test_file_path.touch()
    
    # Mock the projects_db
    original_db = routes.projects_db.copy()
    routes.projects_db[test_project_id] = {
        "id": test_project_id,
        "name": "Test Project",
        "vykaz_path": str(test_file_path),
        "vykaz_format": "excel"
    }
    
    try:
        # Mock the internal methods to avoid actual API calls
        with patch.object(WorkflowA, '_detect_format', return_value='excel'):
            with patch.object(WorkflowA, '_parse_document', return_value=[]):
                result = await workflow_a.run(
                    project_id=test_project_id,
                    calculate_resources=True
                )
                
                # Check result structure
                assert isinstance(result, dict)
                assert "success" in result
                print("✅ run() executed with correct signature")
                print(f"   Result keys: {list(result.keys())}")
    
    finally:
        # Cleanup
        routes.projects_db.clear()
        routes.projects_db.update(original_db)
        if test_file_path.exists():
            test_file_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
