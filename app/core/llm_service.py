"""
Centralized LLM Service for Construction Analysis API
Provides unified interface for Claude, OpenAI GPT, and Perplexity Search API
"""

import os
import logging
import asyncio
import requests
from typing import Dict, Any, Optional, List
from enum import Enum

import anthropic
from openai import OpenAI
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Маппинги моделей
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
    CLAUDE = "claude"
    GPT = "gpt"
    OPENAI = "openai"  # alias
    PERPLEXITY = "perplexity"


class LLMService:
    """Centralized service for LLM API calls"""

    def __init__(self):
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

        # Инициализация клиентов
        self.claude_client = anthropic.Anthropic(api_key=self.anthropic_api_key) if self.anthropic_api_key else None
        self.openai_client = OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None

        logger.info(f"LLMService initialized. Providers: {self.get_available_providers()}")

    # ---------------- Claude ----------------
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def call_claude(self, prompt: str, model: str = "claude-sonnet-4-20250514",
                          max_tokens: int = 4000, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.claude_client:
            return {"provider": "claude", "success": False, "error": "Claude API key missing"}

        try:
            messages = [{"role": "user", "content": prompt}]
            kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await asyncio.to_thread(self.claude_client.messages.create, **kwargs)
            content = response.content[0].text if response.content else ""

            return {"provider": "claude", "model": model, "content": content,
                    "usage": dict(response.usage), "success": True}
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return {"provider": "claude", "success": False, "error": str(e)}

    # ---------------- OpenAI ----------------
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def call_gpt(self, prompt: str, model: str = "gpt5", max_tokens: int = 4000,
                       system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.openai_client:
            return {"provider": "gpt", "success": False, "error": "OpenAI API key missing"}

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=openai_models.get(model, model),
                messages=messages,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content if response.choices else ""

            return {"provider": "gpt", "model": model, "content": content,
                    "usage": dict(response.usage), "success": True}
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {"provider": "gpt", "success": False, "error": str(e)}

    # ---------------- Perplexity ----------------
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def call_perplexity(self, query: str, model: str = "llama-3.1-sonar-large-128k-online") -> Dict[str, Any]:
        if not self.perplexity_api_key:
            return {"provider": "perplexity", "success": False, "error": "Perplexity API key missing"}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={"Authorization": f"Bearer {self.perplexity_api_key}",
                             "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": query}], "max_tokens": 4000}
                )
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content") or choice.get("output_text", "")

                return {"provider": "perplexity", "model": model, "content": content,
                        "usage": data.get("usage", {}), "success": True}
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return {"provider": "perplexity", "success": False, "error": str(e)}

    # ---------------- Unified async ----------------
    async def run_prompt(self, provider: str, prompt: str, model: Optional[str] = None,
                         system_prompt: Optional[str] = None, max_tokens: int = 4000) -> Dict[str, Any]:
        provider = provider.lower()
        if provider == "claude":
            model = claude_models.get(model, model or "sonnet")
            return await self.call_claude(prompt, model, max_tokens, system_prompt)
        elif provider in ["gpt", "openai"]:
            model = openai_models.get(model, model or "gpt5")
            return await self.call_gpt(prompt, model, max_tokens, system_prompt)
        elif provider == "perplexity":
            return await self.call_perplexity(prompt, model or "llama-3.1-sonar-large-128k-online")
        else:
            raise ValueError(f"Unknown provider: {provider}")

    # ---------------- Status helpers ----------------
    def get_available_providers(self) -> List[str]:
        providers = []
        if self.anthropic_api_key:
            providers.append("claude")
        if self.openai_api_key:
            providers.append("gpt")
        if self.perplexity_api_key:
            providers.append("perplexity")
        return providers

    def get_status(self) -> Dict[str, Any]:
        return {
            "available_providers": self.get_available_providers(),
            "claude_available": bool(self.anthropic_api_key),
            "gpt_available": bool(self.openai_api_key),
            "perplexity_available": bool(self.perplexity_api_key),
            "model_mappings": {"claude": claude_models, "openai": openai_models}
        }


# Global instance
_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service