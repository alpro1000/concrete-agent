"""
Test workflow_a import and signature fix
This validates the fix for ImportError issue
"""


def test_workflow_a_import():
    """Test that workflow_a instance can be imported"""
    try:
        from app.services.workflow_a import workflow_a
        assert workflow_a is not None
        print("✅ workflow_a instance imported successfully")
    except ImportError as e:
        raise AssertionError(f"Failed to import workflow_a: {e}")


def test_workflow_a_is_instance():
    """Test that workflow_a is an instance of WorkflowA class"""
    from app.services.workflow_a import workflow_a, WorkflowA
    
    assert isinstance(workflow_a, WorkflowA)
    print("✅ workflow_a is an instance of WorkflowA")


def test_workflow_a_has_run_method():
    """Test that workflow_a has the run method"""
    from app.services.workflow_a import workflow_a
    
    assert hasattr(workflow_a, 'run')
    assert callable(workflow_a.run)
    print("✅ workflow_a has callable run method")


def test_workflow_a_run_signature():
    """Test that workflow_a.run has correct signature"""
    import inspect
    from app.services.workflow_a import workflow_a
    
    sig = inspect.signature(workflow_a.run)
    params = list(sig.parameters.keys())
    
    # Should have file_path and project_name parameters
    assert 'file_path' in params, "run() should have 'file_path' parameter"
    assert 'project_name' in params, "run() should have 'project_name' parameter"
    
    # Should NOT have project_id or calculate_resources
    assert 'project_id' not in params, "run() should not have 'project_id' parameter"
    assert 'calculate_resources' not in params, "run() should not have 'calculate_resources' parameter"
    
    print("✅ workflow_a.run has correct signature")


def test_routes_import():
    """Test that routes module can import workflow_a"""
    try:
        from app.api.routes import router, workflow_a
        assert router is not None
        assert workflow_a is not None
        print("✅ Routes module imports workflow_a successfully")
    except ImportError as e:
        raise AssertionError(f"Failed to import from routes: {e}")


if __name__ == "__main__":
    # Run tests when called directly
    test_workflow_a_import()
    test_workflow_a_is_instance()
    test_workflow_a_has_run_method()
    test_workflow_a_run_signature()
    test_routes_import()
    print("\n✅ All tests passed!")
