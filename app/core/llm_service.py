"""
Centralized LLM Service for Construction Analysis API
Provides unified interface for Claude, OpenAI GPT, and Perplexity Search API

Author: Senior Python Developer
Version: 2.0.0
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, Literal
from enum import Enum
from dataclasses import dataclass, asdict
import threading

import anthropic
from openai import AsyncOpenAI
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

# Type aliases
ProviderType = Literal["claude", "gpt", "openai", "perplexity"]

# Model mappings - consider moving to config file or environment
CLAUDE_MODELS = {
    "opus": "claude-opus-4-1-20250805",
    "sonnet": "claude-sonnet-4-20250514",
    "default": "claude-sonnet-4-20250514"
}

OPENAI_MODELS = {
    "gpt5": "gpt-5-2025-08-07",
    "gpt5-mini": "gpt-5-mini-2025-08-07",
    "gpt5-codex": "gpt-5-codex-2025-09-15",
    "gpt4.1": "gpt-4.1-2025-04-14",
    "o3": "o3-2025-04-16",
    "o3-pro": "o3-pro-2025-04-16",
    "default": "gpt-5-2025-08-07"
}

PERPLEXITY_MODELS = {
    "sonar-large": "llama-3.1-sonar-large-128k-online",
    "default": "llama-3.1-sonar-large-128k-online"
}

# Configuration
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TIMEOUT = 60.0
MAX_RETRY_ATTEMPTS = 3


class LLMServiceError(Exception):
    """Base exception for LLM service errors"""
    pass


class ProviderNotAvailableError(LLMServiceError):
    """Raised when required provider is not configured"""
    pass


class InvalidModelError(LLMServiceError):
    """Raised when invalid model is specified"""
    pass


class APICallError(LLMServiceError):
    """Raised when API call fails"""
    pass


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    provider: str
    model: str
    content: str
    success: bool
    usage: Dict[str, Any]
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    CLAUDE = "claude"
    GPT = "gpt"
    OPENAI = "openai"  # alias for GPT
    PERPLEXITY = "perplexity"


class LLMService:
    """
    Centralized async service for LLM API calls
    
    Thread-safe singleton with proper async client management
    """
    
    def __init__(self):
        """Initialize LLM service with API clients"""
        # Load API keys
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        
        # Initialize async clients
        self._claude_client = None
        self._openai_client = None
        self._http_client = None
        self._initialized = False
        
        logger.info(
            f"LLMService initialized. "
            f"Available providers: {', '.join(self.get_available_providers())}"
        )
    
    async def _ensure_initialized(self) -> None:
        """Lazy initialization of async clients"""
        if self._initialized:
            return
        
        # Initialize Anthropic async client
        if self.anthropic_api_key:
            self._claude_client = anthropic.AsyncAnthropic(
                api_key=self.anthropic_api_key,
                timeout=httpx.Timeout(DEFAULT_TIMEOUT)
            )
        
        # Initialize OpenAI async client
        if self.openai_api_key:
            self._openai_client = AsyncOpenAI(
                api_key=self.openai_api_key,
                timeout=DEFAULT_TIMEOUT
            )
        
        # Initialize httpx client for Perplexity
        if self.perplexity_api_key:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(DEFAULT_TIMEOUT)
            )
        
        self._initialized = True
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_initialized()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self) -> None:
        """Close all async clients"""
        if self._http_client:
            await self._http_client.aclose()
        # Anthropic and OpenAI clients don't need explicit closing
        self._initialized = False
        logger.info("LLMService clients closed")
    
    def _validate_provider(self, provider: str) -> None:
        """Validate provider is available"""
        provider_lower = provider.lower()
        
        if provider_lower == "claude" and not self.anthropic_api_key:
            raise ProviderNotAvailableError(
                "Claude provider not available. Set ANTHROPIC_API_KEY environment variable."
            )
        elif provider_lower in ["gpt", "openai"] and not self.openai_api_key:
            raise ProviderNotAvailableError(
                "OpenAI provider not available. Set OPENAI_API_KEY environment variable."
            )
        elif provider_lower == "perplexity" and not self.perplexity_api_key:
            raise ProviderNotAvailableError(
                "Perplexity provider not available. Set PERPLEXITY_API_KEY environment variable."
            )
    
    def _resolve_model(self, provider: str, model: Optional[str]) -> str:
        """Resolve model name from alias or use default"""
        provider_lower = provider.lower()
        
        if provider_lower == "claude":
            return CLAUDE_MODELS.get(model or "default", model or CLAUDE_MODELS["default"])
        elif provider_lower in ["gpt", "openai"]:
            return OPENAI_MODELS.get(model or "default", model or OPENAI_MODELS["default"])
        elif provider_lower == "perplexity":
            return PERPLEXITY_MODELS.get(model or "default", model or PERPLEXITY_MODELS["default"])
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((APICallError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def call_claude(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Call Claude API
        
        Args:
            prompt: User prompt
            model: Model name or alias
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt (optional)
            
        Returns:
            LLMResponse object
            
        Raises:
            ProviderNotAvailableError: If Claude is not configured
            APICallError: If API call fails
        """
        await self._ensure_initialized()
        self._validate_provider("claude")
        
        resolved_model = self._resolve_model("claude", model)
        
        try:
            messages = [{"role": "user", "content": prompt}]
            kwargs = {
                "model": resolved_model,
                "max_tokens": max_tokens,
                "messages": messages
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            response = await self._claude_client.messages.create(**kwargs)
            
            # Extract content safely
            content = ""
            if response.content:
                content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            
            # Convert usage to dict safely
            usage = {}
            if hasattr(response, 'usage'):
                usage = {
                    'input_tokens': getattr(response.usage, 'input_tokens', 0),
                    'output_tokens': getattr(response.usage, 'output_tokens', 0)
                }
            
            return LLMResponse(
                provider="claude",
                model=resolved_model,
                content=content,
                success=True,
                usage=usage
            )
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise APICallError(f"Claude API failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error calling Claude: {e}", exc_info=True)
            return LLMResponse(
                provider="claude",
                model=resolved_model,
                content="",
                success=False,
                usage={},
                error=str(e)
            )
    
    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((APICallError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def call_gpt(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Call OpenAI GPT API
        
        Args:
            prompt: User prompt
            model: Model name or alias
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt (optional)
            
        Returns:
            LLMResponse object
            
        Raises:
            ProviderNotAvailableError: If OpenAI is not configured
            APICallError: If API call fails
        """
        await self._ensure_initialized()
        self._validate_provider("openai")
        
        resolved_model = self._resolve_model("openai", model)
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self._openai_client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                max_tokens=max_tokens
            )
            
            # Extract content safely
            content = ""
            if response.choices:
                content = response.choices[0].message.content or ""
            
            # Convert usage to dict safely
            usage = {}
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0),
                    'completion_tokens': getattr(response.usage, 'completion_tokens', 0),
                    'total_tokens': getattr(response.usage, 'total_tokens', 0)
                }
            
            return LLMResponse(
                provider="gpt",
                model=resolved_model,
                content=content,
                success=True,
                usage=usage
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            raise APICallError(f"OpenAI API failed: {str(e)}") from e
    
    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((APICallError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def call_perplexity(
        self,
        query: str,
        model: Optional[str] = None
    ) -> LLMResponse:
        """
        Call Perplexity Search API
        
        Args:
            query: Search query
            model: Model name or alias
            
        Returns:
            LLMResponse object
            
        Raises:
            ProviderNotAvailableError: If Perplexity is not configured
            APICallError: If API call fails
        """
        await self._ensure_initialized()
        self._validate_provider("perplexity")
        
        resolved_model = self._resolve_model("perplexity", model)
        
        try:
            response = await self._http_client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": resolved_model,
                    "messages": [{"role": "user", "content": query}],
                    "max_tokens": DEFAULT_MAX_TOKENS
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract content with fallbacks
            content = ""
            if "choices" in data and data["choices"]:
                choice = data["choices"][0]
                if "message" in choice:
                    content = choice["message"].get("content", "")
                elif "output_text" in choice:
                    content = choice["output_text"]
            
            usage = data.get("usage", {})
            
            return LLMResponse(
                provider="perplexity",
                model=resolved_model,
                content=content,
                success=True,
                usage=usage
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Perplexity HTTP error: {e}")
            raise APICallError(f"Perplexity API failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Perplexity error: {e}", exc_info=True)
            raise APICallError(f"Perplexity API failed: {str(e)}") from e
    
    async def run_prompt(
        self,
        provider: ProviderType,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS
    ) -> Dict[str, Any]:
        """
        Unified interface for running prompts across providers
        
        Args:
            provider: Provider name
            prompt: User prompt
            model: Model name or alias
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens
            
        Returns:
            Dictionary with response data (for backward compatibility)
            
        Raises:
            ValueError: If provider is unknown
            ProviderNotAvailableError: If provider not configured
            APICallError: If API call fails
        """
        provider_lower = provider.lower()
        
        if provider_lower == "claude":
            response = await self.call_claude(prompt, model, max_tokens, system_prompt)
        elif provider_lower in ["gpt", "openai"]:
            response = await self.call_gpt(prompt, model, max_tokens, system_prompt)
        elif provider_lower == "perplexity":
            response = await self.call_perplexity(prompt, model)
        else:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Supported: {', '.join(self.get_available_providers())}"
            )
        
        return response.to_dict()
    
    def get_available_providers(self) -> List[str]:
        """Get list of configured providers"""
        providers = []
        if self.anthropic_api_key:
            providers.append("claude")
        if self.openai_api_key:
            providers.append("gpt")
        if self.perplexity_api_key:
            providers.append("perplexity")
        return providers
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status and configuration"""
        return {
            "available_providers": self.get_available_providers(),
            "claude_available": bool(self.anthropic_api_key),
            "gpt_available": bool(self.openai_api_key),
            "perplexity_available": bool(self.perplexity_api_key),
            "model_mappings": {
                "claude": CLAUDE_MODELS,
                "openai": OPENAI_MODELS,
                "perplexity": PERPLEXITY_MODELS
            },
            "config": {
                "default_max_tokens": DEFAULT_MAX_TOKENS,
                "default_timeout": DEFAULT_TIMEOUT,
                "max_retry_attempts": MAX_RETRY_ATTEMPTS
            }
        }


# Thread-safe singleton
_llm_service: Optional[LLMService] = None
_lock = threading.Lock()


def get_llm_service() -> LLMService:
    """
    Get singleton LLM service instance (thread-safe)
    
    Returns:
        LLMService instance
    """
    global _llm_service
    
    if _llm_service is None:
        with _lock:
            # Double-check locking pattern
            if _llm_service is None:
                _llm_service = LLMService()
    
    return _llm_service


async def reset_llm_service() -> None:
    """Reset singleton (useful for testing)"""
    global _llm_service
    
    if _llm_service:
        await _llm_service.close()
    
    with _lock:
        _llm_service = None


# Export public API
__all__ = [
    'LLMService',
    'LLMResponse',
    'LLMProvider',
    'LLMServiceError',
    'ProviderNotAvailableError',
    'InvalidModelError',
    'APICallError',
    'get_llm_service',
    'reset_llm_service'
]