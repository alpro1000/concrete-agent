"""
LLM Service alias for backward compatibility
Re-exports the centralized LLM service from app.core.llm_service
"""

# Import everything from the core service
from app.core.llm_service import (
    LLMService,
    LLMProvider, 
    get_llm_service,
    claude_models,
    openai_models
)

__all__ = [
    "LLMService", 
    "LLMProvider", 
    "get_llm_service",
    "claude_models",
    "openai_models"
]