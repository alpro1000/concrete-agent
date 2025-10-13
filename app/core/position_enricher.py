"""LLM-powered position enricher."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional

from app.core.config import settings
from app.core.claude_client import ClaudeClient
from app.core.kb_loader import kb_loader
from app.core.registry import registry

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

        self.csn206 = kb_loader.get("B2_csn_standards/csn_en_206")

    def build_prompt(
        self,
        positions: Iterable[Dict[str, Any]],
        specs: Iterable[Dict[str, Any]],
    ) -> str:
        """Build prompt for LLM enrichment."""
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

        if self.csn206 is not None:
            prompt += (
                "\n\nČSN EN 206 excerpt:\n"
                f"{json.dumps(self.csn206, ensure_ascii=False, indent=2)}"
            )

        try:
            llm_output = await self.claude.generate_response(prompt)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("LLM enrichment failed: %s", exc, exc_info=True)
            return positions

        enriched_positions = self.parse_llm_output(llm_output)

        if not enriched_positions:
            logger.warning("LLM returned no enrichment. Keeping original positions.")
            return positions

        self._ensure_codes(enriched_positions, positions, specs)

        return enriched_positions

    def parse_llm_output(self, llm_output: Any) -> List[Dict[str, Any]]:
        """Parse LLM response into structured positions."""
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

    @staticmethod
    def _ensure_codes(
        enriched: List[Dict[str, Any]],
        original_positions: Iterable[Dict[str, Any]],
        specs: Iterable[Dict[str, Any]],
    ) -> None:
        """Ensure enriched positions keep their original codes."""

        spec_code_map: Dict[str, Any] = {}
        for spec in specs:
            if not isinstance(spec, dict):
                continue

            identifier = PositionEnricher._extract_identifier(spec)
            code = (
                spec.get("znacka")
                or spec.get("znak")
                or spec.get("Kód")
                or spec.get("KOD")
                or spec.get("Kod")
                or spec.get("kod")
            )

            if identifier and code and identifier not in spec_code_map:
                spec_code_map[identifier] = code

        position_code_map: Dict[str, Any] = {}
        for pos in original_positions:
            if not isinstance(pos, dict):
                continue

            identifier = PositionEnricher._extract_identifier(pos)
            code = (
                pos.get("code")
                or pos.get("Kód")
                or pos.get("KOD")
                or pos.get("Kod")
                or pos.get("kod")
                or pos.get("znacka")
            )

            if identifier and code and identifier not in position_code_map:
                position_code_map[identifier] = code

        for position in enriched:
            if not isinstance(position, dict):
                continue

            if position.get("code"):
                continue

            identifier = PositionEnricher._extract_identifier(position)

            code = None
            if identifier:
                code = spec_code_map.get(identifier) or position_code_map.get(identifier)

            if not code and position.get("position_number"):
                candidate = str(position["position_number"])
                code = spec_code_map.get(candidate) or position_code_map.get(candidate)

            if code:
                position["code"] = code

    @staticmethod
    def _extract_identifier(item: Dict[str, Any]) -> Optional[str]:
        """Extract a comparable identifier used for code lookups."""

        for key in (
            "position_number",
            "number",
            "cislo",
            "číslo",
            "code",
            "Kód",
            "KOD",
            "Kod",
            "znacka",
            "znak",
            "kod",
            "kód",
        ):
            value = item.get(key)
            if value not in (None, ""):
                return str(value)

        return None


registry.register_enricher("llm", PositionEnricher)

__all__ = ["PositionEnricher"]
