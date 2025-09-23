# config/settings.py
import os
from typing import Optional

class Settings:
    """Настройки приложения"""
    
    # Claude API
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    USE_CLAUDE: bool = os.getenv("USE_CLAUDE", "true").lower() == "true"
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229")
    
    # Лимиты
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB
    MAX_DOCUMENTS: int = int(os.getenv("MAX_DOCUMENTS", "10"))
    
    # Директории
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    LOGS_DIR: str = os.getenv("LOGS_DIR", "logs")
    
    # Безопасность
    ALLOWED_EXTENSIONS: set = {'.pdf', '.docx', '.doc', '.txt', '.xml', '.xls', '.xlsx', '.csv'}
    
    # Логирование
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def is_claude_enabled(cls) -> bool:
        """Проверка доступности Claude"""
        return bool(cls.ANTHROPIC_API_KEY) and cls.USE_CLAUDE

# Глобальные настройки
settings = Settings()
