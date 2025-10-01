"""
Tests for security features in configuration
"""

import pytest
import os
from unittest.mock import patch
from app.core.config import Settings, ConfigurationError, get_settings


class TestAPIKeySecurity:
    """Test API key validation and security"""
    
    def test_api_key_minimum_length_validation(self, monkeypatch):
        """Test that API keys must meet minimum length"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "short")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Settings()
        
        assert "too short" in str(exc_info.value).lower()
    
    def test_api_key_format_warning_anthropic(self, monkeypatch, caplog):
        """Test warning for invalid Anthropic key format"""
        # Valid length but wrong format
        monkeypatch.setenv("ANTHROPIC_API_KEY", "invalid_key_format_1234")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-valid_key_1234567890")
        
        settings = Settings()
        
        # Should create settings but log warning
        assert settings.anthropic_api_key == "invalid_key_format_1234"
        assert "does not start with expected prefix" in caplog.text
    
    def test_api_key_format_warning_openai(self, monkeypatch, caplog):
        """Test warning for invalid OpenAI key format"""
        monkeypatch.setenv("OPENAI_API_KEY", "invalid_key_format_1234")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid_key_1234567890")
        
        settings = Settings()
        
        # Should create settings but log warning
        assert settings.openai_api_key == "invalid_key_format_1234"
        assert "does not start with expected prefix" in caplog.text
    
    def test_valid_anthropic_key_no_warning(self, monkeypatch, caplog):
        """Test valid Anthropic key format doesn't trigger warning"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz")
        
        settings = Settings()
        
        assert settings.anthropic_api_key.startswith("sk-ant-")
        # Should not have format warning (only info about key presence)
        assert "does not start with expected prefix" not in caplog.text
    
    def test_valid_openai_key_no_warning(self, monkeypatch, caplog):
        """Test valid OpenAI key format doesn't trigger warning"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-1234567890abcdefghijklmnopqrstuvwxyz")
        
        settings = Settings()
        
        assert settings.openai_api_key.startswith("sk-")
        assert "does not start with expected prefix" not in caplog.text
    
    def test_no_api_keys_development_allowed(self, monkeypatch, caplog):
        """Test that no API keys in development is allowed with warning"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        settings = Settings()
        
        # Should work in development but log error
        assert "No API keys configured" in caplog.text
    
    def test_no_api_keys_production_fails(self, monkeypatch):
        """Test that no API keys in production raises error"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value).lower()
        assert "at least one" in error_msg and "api key" in error_msg
    
    def test_api_key_logging_masked(self, monkeypatch, caplog):
        """Test that API keys are masked in logs"""
        import logging
        caplog.set_level(logging.INFO)
        
        test_key = "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz12345678"
        monkeypatch.setenv("ANTHROPIC_API_KEY", test_key)
        
        settings = Settings()
        
        # Full key should NOT appear in logs
        assert test_key not in caplog.text
        
        # Check that something was logged about the key
        assert "ANTHROPIC_API_KEY" in caplog.text or "anthropic" in caplog.text.lower()
    
    def test_multiple_api_keys_configured(self, monkeypatch, caplog):
        """Test that multiple API keys can be configured"""
        import logging
        caplog.set_level(logging.INFO)
        
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-1234567890abcdefghijklmnopqrstuvwxyz")
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-1234567890abcdefghijklmnopqrstuvwxyz")
        
        settings = Settings()
        
        assert settings.anthropic_api_key is not None
        assert settings.openai_api_key is not None
        assert settings.perplexity_api_key is not None
        
        # Check that logging mentions configured keys
        assert "configured" in caplog.text.lower() or "api key" in caplog.text.lower()
    
    def test_optional_api_keys_logged_as_not_configured(self, monkeypatch, caplog):
        """Test that missing optional keys are logged appropriately"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        
        settings = Settings()
        
        assert "OPENAI_API_KEY is not configured" in caplog.text
        assert "PERPLEXITY_API_KEY is not configured" in caplog.text
    
    def test_settings_cached(self, monkeypatch):
        """Test that settings are cached properly"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz")
        
        # Clear cache first
        get_settings.cache_clear()
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be the same instance due to caching
        assert settings1 is settings2
    
    def test_max_upload_size_configuration(self, monkeypatch):
        """Test max upload size configuration"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz")
        monkeypatch.setenv("MAX_UPLOAD_SIZE", "52428800")  # 50MB
        
        settings = Settings()
        
        assert settings.max_upload_size == 52428800
    
    def test_upload_dir_configuration(self, monkeypatch):
        """Test upload directory configuration"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz")
        monkeypatch.setenv("UPLOAD_DIR", "/custom/upload/path")
        
        settings = Settings()
        
        assert settings.upload_dir == "/custom/upload/path"
