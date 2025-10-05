"""
Core module for Concrete Agent system.
Contains configuration, database, LLM service, and utilities.

All imports use full package paths (backend.app.*) for proper module resolution.
"""

from backend.app.core.config import settings
from backend.app.core.database import get_db, init_db, check_db_connection, Base
from backend.app.core.llm_service import llm_service
from backend.app.core.prompt_loader import prompt_loader
from backend.app.core.logging_config import app_logger
from backend.app.core.exceptions import (
    ConcreteAgentException,
    AgentException,
    LLMException,
    DatabaseException,
    ValidationException,
    ConfigurationException,
    RegistryException,
    StorageException,
    KnowledgeBaseException
)

__all__ = [
    "settings",
    "get_db",
    "init_db",
    "check_db_connection",
    "Base",
    "llm_service",
    "prompt_loader",
    "app_logger",
    "ConcreteAgentException",
    "AgentException",
    "LLMException",
    "DatabaseException",
    "ValidationException",
    "ConfigurationException",
    "RegistryException",
    "StorageException",
    "KnowledgeBaseException"
]
