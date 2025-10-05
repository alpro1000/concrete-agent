"""
Core configuration module for Concrete Agent system.
Loads environment variables and provides centralized configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Server Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    environment: str = "production"
    
    # Database Configuration
    database_url: str = "sqlite:///./concrete_agent.db"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # LLM API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_primary_provider: str = "anthropic"
    llm_fallback_provider: str = "openai"
    llm_model_anthropic: str = "claude-3-5-sonnet-20241022"
    llm_model_openai: str = "gpt-4o-mini"
    
    # Security
    secret_key: str = "development-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    # CORS Settings
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    cors_credentials: bool = True
    
    # File Storage
    upload_dir: str = "/tmp/uploads"
    max_upload_size: int = 10485760  # 10MB
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # Knowledge Base
    knowledge_base_path: str = "app/knowledgebase"
    norms_update_interval: int = 86400  # 24 hours
    
    # Agent Configuration
    agent_timeout: int = 300  # 5 minutes
    agent_max_retries: int = 3
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def ensure_directories(self):
        """Create required directories if they don't exist."""
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        os.makedirs(self.knowledge_base_path, exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_directories()
