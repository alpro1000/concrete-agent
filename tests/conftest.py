# tests/conftest.py
"""
Common pytest fixtures and configuration for all tests
"""
import pytest
import sys
import os
import tempfile
import shutil
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
    data_dir = tests_dir / "test_data"
    data_dir.mkdir(exist_ok=True)  # Auto-create if missing
    return data_dir

@pytest.fixture
def temp_dir():
    """Provide a temporary directory that auto-cleans"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def mock_api_keys(monkeypatch):
    """Mock API keys for tests without actual credentials"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-perplexity-key")
    return {
        "anthropic": "test-anthropic-key",
        "openai": "test-openai-key",
        "perplexity": "test-perplexity-key"
    }

@pytest.fixture(scope="session")
def sample_test_file(test_data_dir):
    """Create a reusable test file"""
    test_file = test_data_dir / "sample.txt"
    if not test_file.exists():
        test_file.write_text("Sample test content\nBeton C30/37\n", encoding="utf-8")
    return test_file

# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_api: mark test as requiring API keys")
