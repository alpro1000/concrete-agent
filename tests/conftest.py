# tests/conftest.py
"""
Common pytest fixtures and configuration for all tests
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_path():
    """Provide the project root path for tests"""
    return project_root


@pytest.fixture(scope="session")
def tests_dir():
    """Provide the tests directory path"""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def test_data_dir(tests_dir):
    """Provide the test_data directory path"""
    return tests_dir / "test_data"
