"""LLM-powered position enricher."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional

from app.core.config import settings
from app.core.claude_client import ClaudeClient
from app.core.kb_loader import kb_loader

logger = logging.getLogger(__name__)


class _MockClaudeClient:
    """Fallback client used when Anthropic credentials are missing."""

    async def generate_response(self, prompt: str) -> Dict[str, Any]:
        logger.debug("Mock Claude client invoked. Returning empty enrichment.")
        return {"positions": []}


class PositionEnricher:
    """Enrich parsed positions with knowledge base context using an LLM."""

    def __init__(self, claude_client: Optional[Any] = None) -> None:
        if not kb_loader.datasets:
            kb_loader.load_all()

        if claude_client is not None:
            self.claude = claude_client
        elif settings.ANTHROPIC_API_KEY:
            self.claude = ClaudeClient()
        else:
            logger.warning(
                "Anthropic API key not provided. Falling back to mock LLM client."
            )
            self.claude = _MockClaudeClient()

    def build_prompt(
        self,
        positions: Iterable[Dict[str, Any]],
        specs: Iterable[Dict[str, Any]],
    ) -> str:
        payload = {
            "positions": list(positions),
            "specifications": list(specs),
        }
        prompt = [
            "You are an expert construction estimator.",
            "Match bill of quantities positions with drawing specifications",
            "and enrich them with ČSN EN 206 standard requirements.",
            "Return valid JSON with enriched positions.",
            "Context follows:",
            json.dumps(payload, ensure_ascii=False, indent=2),
        ]
        return "\n\n".join(prompt)

    async def enrich_positions(
        self,
        positions: List[Dict[str, Any]],
        specs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        prompt = self.build_prompt(positions, specs)
        llm_output = await self.claude.generate_response(prompt)
        enriched = self.parse_llm_output(llm_output)
        return enriched or positions

    def parse_llm_output(self, llm_output: Any) -> List[Dict[str, Any]]:
        if isinstance(llm_output, list):
            return [item for item in llm_output if isinstance(item, dict)]

        if isinstance(llm_output, dict):
            if "positions" in llm_output and isinstance(llm_output["positions"], list):
                return [
                    item
                    for item in llm_output["positions"]
                    if isinstance(item, dict)
                ]

            if "enriched_positions" in llm_output and isinstance(
                llm_output["enriched_positions"], list
            ):
                return [
                    item
                    for item in llm_output["enriched_positions"]
                    if isinstance(item, dict)
                ]

            return [llm_output]

        if isinstance(llm_output, str):
            try:
                parsed = json.loads(llm_output)
            except json.JSONDecodeError:
                logger.error("Failed to decode LLM output as JSON: %s", llm_output)
                return []
            return self.parse_llm_output(parsed)

        logger.error(
            "Unexpected LLM output type %s. Returning empty list.", type(llm_output)
        )
        return []


__all__ = ["PositionEnricher"]
