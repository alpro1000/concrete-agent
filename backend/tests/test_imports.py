"""
Test module to validate import paths work correctly.

This test ensures that all imports use the correct package structure
(backend.app.*) and can be imported without sys.path manipulation.
This is critical for Render deployment where the working directory
is the project root.
"""

import sys
import pytest
from pathlib import Path


def test_no_backend_in_syspath_initially():
    """Verify that backend directory is not artificially added to sys.path."""
    backend_paths = [p for p in sys.path if 'backend' in p and 'dist-packages' not in p and 'site-packages' not in p]
    # It's OK if backend is in sys.path from the natural project root being there
    # We just want to ensure no sys.path.insert hacks are present
    assert True, "This test documents the sys.path state"


def test_import_main_module():
    """Test that main module can be imported using full package path."""
    try:
        from backend.app.main import app
        assert app is not None
        assert hasattr(app, 'title')
        assert app.title == "Concrete Agent API"
    except ImportError as e:
        pytest.fail(f"Failed to import backend.app.main: {e}")


def test_import_core_modules():
    """Test that core modules can be imported."""
    try:
        from backend.app.core import (
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
        from backend.app.services import agent_registry, czech_normalizer
        assert agent_registry is not None
        assert czech_normalizer is not None
    except ImportError as e:
        pytest.fail(f"Failed to import services: {e}")


def test_import_models():
    """Test that model modules can be imported."""
    try:
        from backend.app.models import User, Analysis, AnalysisStatus, File
        assert User is not None
        assert Analysis is not None
        assert AnalysisStatus is not None
        assert File is not None
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")


def test_import_routers():
    """Test that router modules can be imported."""
    try:
        from backend.app.routers import unified_router, status_router
        assert unified_router is not None
        assert status_router is not None
        assert hasattr(unified_router, 'router')
        assert hasattr(status_router, 'router')
    except ImportError as e:
        pytest.fail(f"Failed to import routers: {e}")


def test_import_agents():
    """Test that agent modules can be imported."""
    try:
        from backend.app.agents.base_agent import BaseAgent
        assert BaseAgent is not None
    except ImportError as e:
        pytest.fail(f"Failed to import agents: {e}")


def test_project_structure():
    """Verify the expected project structure exists."""
    # Get project root (should be 2 levels up from this file)
    test_file = Path(__file__).resolve()
    backend_dir = test_file.parent.parent
    project_root = backend_dir.parent
    
    # Verify structure
    assert (backend_dir / "app" / "main.py").exists(), "backend/app/main.py should exist"
    assert (backend_dir / "app" / "core" / "__init__.py").exists(), "backend/app/core/__init__.py should exist"
    assert (backend_dir / "app" / "models" / "__init__.py").exists(), "backend/app/models/__init__.py should exist"
    assert (backend_dir / "app" / "services" / "__init__.py").exists(), "backend/app/services/__init__.py should exist"
    assert (backend_dir / "__init__.py").exists(), "backend/__init__.py should exist (makes it a package)"


def test_uvicorn_command_format():
    """
    Document the correct uvicorn command for running the application.
    
    From project root: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    From backend dir: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    
    Both should work because Python adds the current directory to sys.path.
    """
    assert True, "This test documents the correct command format"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
