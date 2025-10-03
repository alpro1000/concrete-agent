"""
Tests for PromptLoader enhancements
"""

import pytest
from pathlib import Path
from app.core.prompt_loader import PromptLoader, get_prompt_loader


def test_get_prompt_config_tzd():
    """Test get_prompt_config returns valid config for tzd"""
    loader = PromptLoader()
    config = loader.get_prompt_config("tzd")
    
    assert isinstance(config, dict)
    assert "model" in config
    assert "max_tokens" in config
    assert config["model"] == "claude-3-5-sonnet-20241022"
    assert config["max_tokens"] == 4000


def test_get_prompt_config_default():
    """Test get_prompt_config returns default config for unknown names"""
    loader = PromptLoader()
    config = loader.get_prompt_config("unknown_config")
    
    assert isinstance(config, dict)
    assert "model" in config
    assert config["model"] == "gpt-4o-mini"


def test_get_system_prompt():
    """Test get_system_prompt method"""
    loader = PromptLoader()
    prompt = loader.get_system_prompt("tzd")
    
    # Should return empty string if file doesn't exist (expected behavior)
    assert isinstance(prompt, str)


def test_singleton_pattern():
    """Test get_prompt_loader returns same instance"""
    loader1 = get_prompt_loader()
    loader2 = get_prompt_loader()
    
    assert loader1 is loader2


def test_load_prompt_nonexistent():
    """Test load_prompt with non-existent file"""
    loader = PromptLoader()
    prompt = loader.load_prompt("nonexistent_prompt")
    
    assert prompt == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
