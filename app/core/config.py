"""
Application configuration
"""

import os
from functools import lru_cache
from typing import List


class Settings:
    """Application settings"""
    
    def __init__(self):
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.port = int(os.getenv("PORT", "8000"))
        
        # API Keys
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        
        # CORS
        allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
        self.allowed_origins = [
            origin.strip() 
            for origin in allowed_origins_str.split(",")
        ]
        
        # File uploads
        self.upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        self.max_upload_size = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
