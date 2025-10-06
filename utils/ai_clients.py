"""
Legacy AI clients - Stub implementation
The system now uses centralized LLM service from app.core.llm_service
These are only kept for backward compatibility and will return None
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_openai_client() -> Optional[object]:
    """
    Get OpenAI client (legacy stub)
    
    Returns None as the system now uses centralized LLMService
    """
    logger.info("Legacy OpenAI client requested - returning None (use LLMService instead)")
    return None


def get_anthropic_client() -> Optional[object]:
    """
    Get Anthropic client (legacy stub)
    
    Returns None as the system now uses centralized LLMService
    """
    logger.info("Legacy Anthropic client requested - returning None (use LLMService instead)")
    return None
