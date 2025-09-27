"""
AI Client Abstractions
Centralized AI client management for OpenAI and Anthropic
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

API_TIMEOUT = int(os.getenv("API_TIMEOUT", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

def get_openai_client() -> Optional["OpenAI"]:
    """
    Get configured OpenAI client
    
    Returns:
        OpenAI client instance or None if unavailable
    """
    try:
        from openai import OpenAI
    except Exception as e:
        logger.warning(f"OpenAI SDK import failed: {e}")
        return None
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or len(api_key) < 20:
        logger.warning("OPENAI_API_KEY is missing or too short")
        return None
    
    try:
        return OpenAI(
            api_key=api_key, 
            timeout=API_TIMEOUT, 
            max_retries=MAX_RETRIES
        )
    except Exception as e:
        logger.error(f"OpenAI client initialization failed: {e}")
        return None

def get_anthropic_client() -> Optional["Anthropic"]:
    """
    Get configured Anthropic client
    
    Returns:
        Anthropic client instance or None if unavailable
    """
    try:
        from anthropic import Anthropic
    except Exception as e:
        logger.warning(f"Anthropic SDK import failed: {e}")
        return None
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or len(api_key) < 20:
        logger.warning("ANTHROPIC_API_KEY is missing or too short")
        return None
    
    try:
        return Anthropic(
            api_key=api_key, 
            timeout=API_TIMEOUT, 
            max_retries=MAX_RETRIES
        )
    except Exception as e:
        logger.error(f"Anthropic client initialization failed: {e}")
        return None