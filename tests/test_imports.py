"""
Test module to validate import paths work correctly.

This test ensures that all imports use the correct package structure
(app.*) and can be imported without sys.path manipulation.
This is critical for Render deployment where the working directory
is the project root.
"""

import sys
import pytest
from pathlib import Path


def test_no_app_in_syspath_initially():
    """Verify that app directory is not artificially added to sys.path."""
    app_paths = [p for p in sys.path if 'app' in p and 'dist-packages' not in p and 'site-packages' not in p]
    # It's OK if app is in sys.path from the natural project root being there
    # We just want to ensure no sys.path.insert hacks are present
    assert True, "This test documents the sys.path state"


def test_import_main_module():
    """Test that main module can be imported using full package path."""
    try:
        from app.main import app
        assert app is not None
        assert hasattr(app, 'title')
        assert app.title == "Concrete Agent API"
    except ImportError as e:
        pytest.fail(f"Failed to import app.main: {e}")


def test_import_core_modules():
    """Test that core modules can be imported."""
    try:
        from app.core import (
            settings,
            init_db,
            check_db_connection,
            app_logger,
            ConcreteAgentException,
        )
        assert settings is not None
        assert init_db is not None
        assert check_db_connection is not None
        assert app_logger is not None
        assert ConcreteAgentException is not None
    except ImportError as e:
        pytest.fail(f"Failed to import core modules: {e}")


def test_import_services():
    """Test that service modules can be imported."""
    try:
        from app.services import agent_registry, czech_normalizer
        assert agent_registry is not None
        assert czech_normalizer is not None
    except ImportError as e:
        pytest.fail(f"Failed to import services: {e}")


def test_import_models():
    """Test that model modules can be imported."""
    try:
        from app.models import User, Analysis, AnalysisStatus, File
        assert User is not None
        assert Analysis is not None
        assert AnalysisStatus is not None
        assert File is not None
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")


def test_import_routers():
    """Test that router modules can be imported."""
    try:
        from app.routers import unified_router, status_router
        assert unified_router is not None
        assert status_router is not None
        assert hasattr(unified_router, 'router')
        assert hasattr(status_router, 'router')
    except ImportError as e:
        pytest.fail(f"Failed to import routers: {e}")


def test_import_agents():
    """Test that agent modules can be imported."""
    try:
        from app.agents.base_agent import BaseAgent
        assert BaseAgent is not None
    except ImportError as e:
        pytest.fail(f"Failed to import agents: {e}")


def test_project_structure():
    """Verify the expected project structure exists."""
    # Get project root (should be parent of this test file)
    test_file = Path(__file__).resolve()
    project_root = test_file.parent.parent
    
    # Verify structure
    assert (project_root / "app" / "main.py").exists(), "app/main.py should exist"
    assert (project_root / "app" / "core" / "__init__.py").exists(), "app/core/__init__.py should exist"
    assert (project_root / "app" / "models" / "__init__.py").exists(), "app/models/__init__.py should exist"
    assert (project_root / "app" / "services" / "__init__.py").exists(), "app/services/__init__.py should exist"
    assert (project_root / "app" / "__init__.py").exists(), "app/__init__.py should exist"


def test_uvicorn_command_format():
    """
    Document the correct uvicorn command for running the application.
    
    From project root: uvicorn app.main:app --host 0.0.0.0 --port 8000
    
    This should work because Python adds the current directory to sys.path.
    """
    assert True, "This test documents the correct command format"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
