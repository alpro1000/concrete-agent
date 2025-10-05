"""
LLM Service with automatic fallback between Anthropic and OpenAI.
"""

from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from openai import OpenAI
from backend.app.core.config import settings
from backend.app.core.logging_config import app_logger
from backend.app.core.exceptions import LLMException


class LLMService:
    """
    LLM service with automatic fallback.
    Primary: Anthropic Claude
    Fallback: OpenAI GPT
    """
    
    def __init__(self):
        self.anthropic_client = None
        self.openai_client = None
        
        # Initialize Anthropic if API key available
        if settings.anthropic_api_key:
            try:
                self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
                app_logger.info("Anthropic client initialized")
            except Exception as e:
                app_logger.warning(f"Failed to initialize Anthropic client: {e}")
        
        # Initialize OpenAI if API key available
        if settings.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=settings.openai_api_key)
                app_logger.info("OpenAI client initialized")
            except Exception as e:
                app_logger.warning(f"Failed to initialize OpenAI client: {e}")
        
        if not self.anthropic_client and not self.openai_client:
            app_logger.error("No LLM clients available!")
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        provider: Optional[str] = None
    ) -> str:
        """
        Generate text using LLM with automatic fallback.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            provider: Force specific provider ('anthropic' or 'openai')
            
        Returns:
            Generated text
        """
        # Determine provider order
        if provider:
            providers = [provider]
        elif settings.llm_primary_provider == "anthropic":
            providers = ["anthropic", "openai"]
        else:
            providers = ["openai", "anthropic"]
        
        last_error = None
        
        for provider_name in providers:
            try:
                if provider_name == "anthropic" and self.anthropic_client:
                    return await self._generate_anthropic(messages, system_prompt, temperature, max_tokens)
                elif provider_name == "openai" and self.openai_client:
                    return await self._generate_openai(messages, system_prompt, temperature, max_tokens)
            except Exception as e:
                last_error = e
                app_logger.warning(f"Failed to generate with {provider_name}: {e}")
                continue
        
        # All providers failed
        raise LLMException(
            "All LLM providers failed",
            {"error": str(last_error), "providers_tried": providers}
        )
    
    async def _generate_anthropic(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Anthropic Claude."""
        try:
            response = self.anthropic_client.messages.create(
                model=settings.llm_model_anthropic,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=messages
            )
            
            app_logger.info(f"Generated response using Anthropic Claude")
            return response.content[0].text
            
        except Exception as e:
            app_logger.error(f"Anthropic generation failed: {e}")
            raise
    
    async def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using OpenAI GPT."""
        try:
            # Add system prompt to messages if provided
            openai_messages = []
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})
            openai_messages.extend(messages)
            
            response = self.openai_client.chat.completions.create(
                model=settings.llm_model_openai,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            app_logger.info(f"Generated response using OpenAI GPT")
            return response.choices[0].message.content
            
        except Exception as e:
            app_logger.error(f"OpenAI generation failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if any LLM provider is available."""
        return self.anthropic_client is not None or self.openai_client is not None


# Global LLM service instance
llm_service = LLMService()
