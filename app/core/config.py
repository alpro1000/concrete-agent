"""
Application configuration
"""

import os
import logging
from functools import lru_cache
from typing import List, Optional

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised for configuration errors"""
    pass


class Settings:
    """Application settings with secure API key validation"""
    
    def __init__(self):
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.port = int(os.getenv("PORT", "8000"))
        
        # API Keys with validation
        self.anthropic_api_key = self._get_api_key("ANTHROPIC_API_KEY", required=False)
        self.openai_api_key = self._get_api_key("OPENAI_API_KEY", required=False)
        self.perplexity_api_key = self._get_api_key("PERPLEXITY_API_KEY", required=False)
        
        # Validate at least one API key is configured
        self._validate_api_keys()
        
        # CORS
        allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
        self.allowed_origins = [
            origin.strip() 
            for origin in allowed_origins_str.split(",")
        ]
        
        # File uploads
        self.upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        self.max_upload_size = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    
    def _get_api_key(self, key_name: str, required: bool = False) -> Optional[str]:
        """
        Safely retrieve and validate API key from environment
        
        Args:
            key_name: Name of the environment variable
            required: Whether this key is required
            
        Returns:
            API key value or None
            
        Raises:
            ConfigurationError: If required key is missing or invalid
        """
        value = os.getenv(key_name)
        
        if not value:
            if required:
                raise ConfigurationError(
                    f"Required environment variable {key_name} is not set"
                )
            logger.warning(f"Optional API key {key_name} is not configured")
            return None
        
        # Basic validation - check minimum length
        if len(value) < 10:
            raise ConfigurationError(
                f"Invalid {key_name}: API key is too short (minimum 10 characters)"
            )
        
        # Validate key format based on provider
        if key_name == "ANTHROPIC_API_KEY" and not value.startswith("sk-ant-"):
            logger.warning(f"{key_name} does not start with expected prefix 'sk-ant-'")
        elif key_name == "OPENAI_API_KEY" and not value.startswith("sk-"):
            logger.warning(f"{key_name} does not start with expected prefix 'sk-'")
        
        # Log key presence without exposing the actual value
        masked_key = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
        logger.info(f"{key_name} configured: {masked_key}")
        
        return value
    
    def _validate_api_keys(self):
        """Validate that at least one API key is configured"""
        configured_keys = sum([
            bool(self.anthropic_api_key),
            bool(self.openai_api_key),
            bool(self.perplexity_api_key)
        ])
        
        if configured_keys == 0:
            logger.error("No API keys configured! AI features will not be available.")
            if self.environment == "production":
                raise ConfigurationError(
                    "At least one API key (ANTHROPIC_API_KEY, OPENAI_API_KEY, or PERPLEXITY_API_KEY) "
                    "must be configured in production environment"
                )
        else:
            logger.info(f"Configured {configured_keys} API key(s)")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
