"""Deterministic enrichment of parsed cost positions with drawing specs."""

from __future__ import annotations

import logging
import math
import re
from typing import Dict, Iterable, List, Tuple

logger = logging.getLogger(__name__)


class PositionEnricher:
    """Attach technical specification metadata to cost positions.

    The enricher does *not* rely on external AI services.  It uses deterministic
    heuristics to find the most relevant drawing specification for a position.
    Matching priority follows the specification from the prompt: ``code`` →
    ``description`` → ``unit``.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enrich(
        self,
        positions: Iterable[Dict[str, object]],
        drawing_specs: Iterable[Dict[str, object]],
    ) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
        """Return enriched positions and enrichment statistics."""

        specs = list(drawing_specs) if self.enabled else []
        enriched_positions: List[Dict[str, object]] = []
        stats = {"enabled": bool(self.enabled), "matched": 0, "partial": 0, "unmatched": 0}

        for position in positions:
            enriched = self._enrich_single(dict(position), specs)
            status = enriched.get("enrichment_status", "unmatched")
            stats[status] = stats.get(status, 0) + 1
            enriched_positions.append(enriched)

        logger.info(
            "Enrichment summary → matched=%s, partial=%s, unmatched=%s",
            stats.get("matched", 0),
            stats.get("partial", 0),
            stats.get("unmatched", 0),
        )

        return enriched_positions, stats

    # ------------------------------------------------------------------
    # Matching helpers
    # ------------------------------------------------------------------

    def _enrich_single(
        self, position: Dict[str, object], specs: List[Dict[str, object]]
    ) -> Dict[str, object]:
        """Enrich a single position.

        If enrichment is disabled or there are no specifications the position is
        returned untouched except for ``enrichment_status`` which becomes
        ``"unmatched"``.
        """

        if not self.enabled or not specs:
            position.setdefault("enrichment_status", "unmatched")
            return position

        best_score = 0.0
        best_spec: Dict[str, object] | None = None

        for spec in specs:
            score = self._score_spec(position, spec)
            if score > best_score:
                best_score = score
                best_spec = spec

        if not best_spec or best_score < 0.5:
            position.setdefault("enrichment_status", "unmatched")
            return position

        status = "matched" if best_score >= 0.85 else "partial"

        if technical := best_spec.get("technical_specs"):
            position["technical_specs"] = technical

        position["enrichment_status"] = status
        position["provenance"] = {
            "file": best_spec.get("file"),
            "page": best_spec.get("page"),
            "anchor": best_spec.get("anchor"),
            "confidence": best_spec.get("confidence"),
        }

        return position

    # ------------------------------------------------------------------
    # Scoring logic
    # ------------------------------------------------------------------

    def _score_spec(self, position: Dict[str, object], spec: Dict[str, object]) -> float:
        """Compute a 0–1 score describing how well a specification fits."""

        description = str(position.get("description") or "").lower()
        code = str(position.get("code") or "").lower()
        unit = str(position.get("unit") or "").lower()
        spec_text = str(spec.get("text") or "").lower()
        anchor = str(spec.get("anchor") or "").lower()
        technical = spec.get("technical_specs") or {}

        score = 0.0

        if code and code in spec_text:
            score += 0.45

        if anchor and anchor in description:
            score += 0.35
        elif anchor and anchor in spec_text:
            score += 0.2

        # keyword overlap in descriptions
        if description and spec_text:
            overlap = self._keyword_overlap(description, spec_text)
            score += min(overlap * 0.25, 0.25)

        spec_unit = str(technical.get("unit") or "").lower()
        if unit and spec_unit and unit == spec_unit:
            score += 0.1
        elif unit and unit in spec_text:
            score += 0.05

        if technical.get("concrete_class"):
            class_token = str(technical["concrete_class"]).lower()
            if class_token in description:
                score += 0.25

        exposures = [str(e).lower() for e in technical.get("exposure", [])]
        if exposures and any(exp in description for exp in exposures):
            score += 0.1

        reinforcement = str(technical.get("reinforcement") or "").lower()
        if reinforcement and reinforcement in description:
            score += 0.2

        return min(score, 1.0)

    @staticmethod
    def _keyword_overlap(description: str, spec_text: str) -> float:
        """Return a ratio describing keyword overlap between texts."""

        tokenize = lambda text: {token for token in re.findall(r"[a-z0-9/]+", text) if len(token) > 3}
        desc_tokens = tokenize(description)
        spec_tokens = tokenize(spec_text)

        if not desc_tokens or not spec_tokens:
            return 0.0

        intersection = desc_tokens.intersection(spec_tokens)
        return len(intersection) / math.sqrt(len(desc_tokens) * len(spec_tokens))


__all__ = ["PositionEnricher"]

