"""
Centralized LLM Service for Construction Analysis API
Provides unified interface for Claude, ChatGPT, and Perplexity Search API
"""

import os
import logging
import asyncio
import requests
from typing import Dict, Any, Optional, List
from enum import Enum

import anthropic
import openai
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Model mappings as specified in requirements
claude_models = {
    "opus": "claude-opus-4-1-20250805",
    "sonnet": "claude-sonnet-4-20250514"
}

openai_models = {
    "gpt5": "gpt-5-2025-08-07",
    "gpt5-mini": "gpt-5-mini-2025-08-07",
    "gpt5-codex": "gpt-5-codex-2025-09-15",
    "gpt4.1": "gpt-4.1-2025-04-14",
    "o3": "o3-2025-04-16",
    "o3-pro": "o3-pro-2025-04-16"
}


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    CLAUDE = "claude"
    GPT = "gpt"
    OPENAI = "openai"  # alias for GPT
    PERPLEXITY = "perplexity"


class LLMService:
    """
    Centralized service for LLM API calls
    Supports Claude, OpenAI GPT, and Perplexity Search
    """

    def __init__(self):
        # Load API keys from environment
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        
        # Initialize clients
        self.claude_client = None
        self.openai_client = None
        
        if self.anthropic_api_key:
            self.claude_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            logger.info("✅ Claude client initialized")
        else:
            logger.warning("⚠️ ANTHROPIC_API_KEY not found")
            
        if self.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
            logger.info("✅ OpenAI client initialized")
        else:
            logger.warning("⚠️ OPENAI_API_KEY not found")
            
        if self.perplexity_api_key:
            logger.info("✅ Perplexity API key found")
        else:
            logger.warning("⚠️ PERPLEXITY_API_KEY not found")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def call_claude(
        self, 
        prompt: str, 
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call Anthropic Claude API
        
        Args:
            prompt: User prompt text
            model: Claude model to use
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt
            
        Returns:
            Dict with response data
        """
        if not self.claude_client:
            raise ValueError("Claude client not initialized. Check ANTHROPIC_API_KEY.")
            
        try:
            messages = [{"role": "user", "content": prompt}]
            
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
                
            response = await asyncio.to_thread(
                self.claude_client.messages.create,
                **kwargs
            )
            
            content = response.content[0].text if response.content else ""
            
            return {
                "provider": "claude",
                "model": model,
                "content": content,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return {
                "provider": "claude",
                "model": model,
                "content": "",
                "error": str(e),
                "success": False
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def call_gpt(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call OpenAI GPT API
        
        Args:
            prompt: User prompt text
            model: GPT model to use
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt
            
        Returns:
            Dict with response data
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
            
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=model,
                messages=messages,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content if response.choices else ""
            
            return {
                "provider": "gpt",
                "model": model,
                "content": content,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                },
                "success": True
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                "provider": "gpt", 
                "model": model,
                "content": "",
                "error": str(e),
                "success": False
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def call_perplexity(
        self,
        query: str,
        model: str = "llama-3.1-sonar-large-128k-online"
    ) -> Dict[str, Any]:
        """
        Call Perplexity Search API
        
        Args:
            query: Search query
            model: Perplexity model to use
            
        Returns:
            Dict with response data
        """
        if not self.perplexity_api_key:
            raise ValueError("Perplexity API key not found. Check PERPLEXITY_API_KEY.")
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.perplexity_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": query}],
                        "max_tokens": 4000
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    return {
                        "provider": "perplexity",
                        "model": model,
                        "content": content,
                        "usage": data.get("usage", {}),
                        "success": True
                    }
                else:
                    error_msg = f"Perplexity API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "provider": "perplexity",
                        "model": model,
                        "content": "",
                        "error": error_msg,
                        "success": False
                    }
                    
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return {
                "provider": "perplexity",
                "model": model,
                "content": "",
                "error": str(e),
                "success": False
            }

    # Sync methods as specified in requirements
    def call_claude_sync(self, prompt: str, model: str = "opus"):
        """Synchronous Claude API call with model mapping"""
        if model not in claude_models:
            raise ValueError(f"Unknown Claude model: {model}. Available: {list(claude_models.keys())}")
            
        if not self.claude_client:
            raise ValueError("Claude client not initialized. Check ANTHROPIC_API_KEY.")
            
        try:
            response = self.claude_client.messages.create(
                model=claude_models[model],
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response
        except Exception as e:
            logger.error(f"Claude sync API error: {e}")
            raise

    def call_openai_sync(self, prompt: str, model: str = "gpt5"):
        """Synchronous OpenAI API call with model mapping"""
        if model not in openai_models:
            raise ValueError(f"Unknown OpenAI model: {model}. Available: {list(openai_models.keys())}")
            
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
            
        try:
            response = self.openai_client.chat.completions.create(
                model=openai_models[model],
                messages=[{"role": "user", "content": prompt}]
            )
            return response
        except Exception as e:
            logger.error(f"OpenAI sync API error: {e}")
            raise

    def call_perplexity_sync(self, query: str):
        """Synchronous Perplexity API call"""
        if not self.perplexity_api_key:
            raise ValueError("Perplexity API key not found. Check PERPLEXITY_API_KEY.")
            
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "sonar-large-chat",  # base reasoning model
            "messages": [{"role": "user", "content": query}]
        }
        
        try:
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            return response.json()
        except Exception as e:
            logger.error(f"Perplexity sync API error: {e}")
            raise

    def run(self, prompt: str, provider: str = "claude", model: str = "opus"):
        """
        Main sync interface as specified in requirements
        
        Args:
            prompt: User prompt text
            provider: LLM provider ("claude", "openai", "perplexity")
            model: Model name (mapped internally)
            
        Returns:
            Response from the specified provider
        """
        provider = provider.lower()
        
        if provider == "claude":
            return self.call_claude_sync(prompt, model)
        elif provider in ["openai", "gpt"]:
            return self.call_openai_sync(prompt, model)
        elif provider == "perplexity":
            return self.call_perplexity_sync(prompt)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def run_prompt(
        self,
        provider: str,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Unified async interface to run prompts on any provider (backward compatibility)
        
        Args:
            provider: LLM provider ("claude", "gpt", "perplexity")
            prompt: User prompt text
            model: Optional model override
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            
        Returns:
            Dict with response data
        """
        provider = provider.lower()
        
        if provider == LLMProvider.CLAUDE:
            model = model or "claude-3-sonnet-20240229"
            return await self.call_claude(prompt, model, max_tokens, system_prompt)
            
        elif provider in [LLMProvider.GPT, LLMProvider.OPENAI]:
            model = model or "gpt-4o-mini"
            return await self.call_gpt(prompt, model, max_tokens, system_prompt)
            
        elif provider == LLMProvider.PERPLEXITY:
            model = model or "llama-3.1-sonar-large-128k-online"
            return await self.call_perplexity(prompt, model)
            
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use: {[p.value for p in LLMProvider]}")

    def get_available_providers(self) -> List[str]:
        """Get list of available providers based on API keys"""
        providers = []
        
        if self.anthropic_api_key:
            providers.append(LLMProvider.CLAUDE)
        if self.openai_api_key:
            providers.append(LLMProvider.GPT)
        if self.perplexity_api_key:
            providers.append(LLMProvider.PERPLEXITY)
            
        return providers

    def get_available_models(self) -> Dict[str, List[str]]:
        """Get available models for each provider"""
        models = {}
        
        if self.anthropic_api_key:
            models["claude"] = list(claude_models.keys())
        if self.openai_api_key:
            models["openai"] = list(openai_models.keys())
        if self.perplexity_api_key:
            models["perplexity"] = ["sonar-large-chat"]
            
        return models

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "available_providers": self.get_available_providers(),
            "available_models": self.get_available_models(),
            "claude_available": bool(self.anthropic_api_key),
            "gpt_available": bool(self.openai_api_key),
            "perplexity_available": bool(self.perplexity_api_key),
            "model_mappings": {
                "claude": claude_models,
                "openai": openai_models
            }
        }


# Global instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service