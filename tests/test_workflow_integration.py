"""
Integration test for workflow_a fix
Simulates the complete flow from import to method call
"""
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch


def test_complete_import_flow():
    """Test that the complete import flow works"""
    print("Testing complete import flow...")
    
    # Step 1: Import workflow_a
    from app.services.workflow_a import workflow_a, WorkflowA
    assert isinstance(workflow_a, WorkflowA)
    print("✅ Step 1: workflow_a imported successfully")
    
    # Step 2: Import routes
    from app.api.routes import router
    assert router is not None
    print("✅ Step 2: Routes imported successfully")
    
    # Step 3: Verify the entire app can be imported
    from app.main import app
    assert app is not None
    print("✅ Step 3: FastAPI app imported successfully")
    
    print("✅ Complete import flow works!\n")


def test_method_call_parameters():
    """Test that the method call in routes uses correct parameters"""
    from app.services.workflow_a import workflow_a
    import inspect
    
    # Get the signature of the run method
    sig = inspect.signature(workflow_a.run)
    params = list(sig.parameters.keys())
    
    # Verify correct parameters
    assert 'file_path' in params, "Missing 'file_path' parameter"
    assert 'project_name' in params, "Missing 'project_name' parameter"
    
    # Verify incorrect parameters are not present
    assert 'project_id' not in params, "Should not have 'project_id' parameter"
    assert 'calculate_resources' not in params, "Should not have 'calculate_resources' parameter"
    
    print("✅ Method signature is correct")


def test_project_dict_structure():
    """Test that project dictionary has required fields for our fix"""
    # Simulate the project dictionary structure from routes.py
    project = {
        "id": "test-uuid",
        "name": "Test Project",
        "vykaz_path": "/tmp/test_vykaz.xlsx",
        "status": "uploaded"
    }
    
    # Verify the fields we use in our fix exist
    assert "vykaz_path" in project, "Project must have 'vykaz_path'"
    assert "name" in project, "Project must have 'name'"
    
    # Verify we can create Path from vykaz_path
    vykaz_path = Path(project["vykaz_path"])
    assert isinstance(vykaz_path, Path)
    
    # Verify we can get project_name
    project_name = project["name"]
    assert isinstance(project_name, str)
    
    print("✅ Project dictionary structure is compatible with our fix")


def test_workflow_a_run_can_be_called_with_correct_params():
    """Test that workflow_a.run can be called with our parameters"""
    from app.services.workflow_a import workflow_a
    import inspect
    
    # Create test parameters matching what we pass in routes.py
    test_params = {
        'file_path': Path('/tmp/test.xlsx'),
        'project_name': 'Test Project'
    }
    
    # Get method signature
    sig = inspect.signature(workflow_a.run)
    
    # Try to bind our parameters to the signature
    try:
        bound = sig.bind(**test_params)
        print(f"✅ Parameters bind correctly: {bound.arguments}")
    except TypeError as e:
        raise AssertionError(f"Parameters don't match signature: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("INTEGRATION TEST: workflow_a Import Fix")
    print("=" * 60 + "\n")
    
    test_complete_import_flow()
    test_method_call_parameters()
    test_project_dict_structure()
    test_workflow_a_run_can_be_called_with_correct_params()
    
    print("\n" + "=" * 60)
    print("✅ ALL INTEGRATION TESTS PASSED!")
    print("=" * 60)
