from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Tuple

from app.core.config import settings
from app.core.kb_loader import get_knowledge_base

logger = logging.getLogger(__name__)


@dataclass
class TokenBundle:
    raw: str
    normalized: str
    tokens: set[str]
    codes: set[str]
    concretes: set[str]
    exposures: set[str]
    diameters: set[str]
    csn: set[str]
    unit: str


@dataclass
class SpecContext:
    data: Dict[str, Any]
    bundle: TokenBundle
    unit: str
    snippet: str


class PositionEnricher:
    """Attach technical metadata to bill-of-quantities positions."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.score_exact = settings.ENRICH_SCORE_EXACT
        self.score_partial = settings.ENRICH_SCORE_PARTIAL
        self.max_evidence = settings.ENRICH_MAX_EVIDENCE

        self.kros_index: Dict[str, Dict[str, Any]] = {}
        self._kros_entries: List[Tuple[Dict[str, Any], TokenBundle]] = []
        self.csn_index: Dict[str, List[Dict[str, str]]] = {}

        if self.enabled:
            kb = get_knowledge_base()
            self.kros_index = kb.get_kros_index()
            self.csn_index = kb.get_csn_index()
            for entry in self.kros_index.values():
                description = entry.get("description") or ""
                unit = entry.get("unit")
                self._kros_entries.append((entry, self._extract_bundle(description, unit)))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enrich(
        self,
        positions: Iterable[Dict[str, Any]],
        drawing_specs: Iterable[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not self.enabled:
            enriched_positions = []
            for position in positions:
                payload = dict(position)
                payload.setdefault("enrichment_status", "unmatched")
                payload["enrichment_score"] = 0.0
                payload["enrichment"] = {"match": "none", "score": 0.0, "evidence": []}
                enriched_positions.append(payload)
            stats = {"enabled": False, "matched": 0, "partial": 0, "unmatched": len(enriched_positions)}
            return enriched_positions, stats

        spec_contexts = [self._prepare_spec(spec) for spec in drawing_specs]

        enriched_positions: List[Dict[str, Any]] = []
        stats = {"enabled": True, "matched": 0, "partial": 0, "unmatched": 0}

        for position in positions:
            enriched = self._enrich_single(dict(position), spec_contexts)
            status = str(enriched.get("enrichment_status") or "").lower()
            if status == "matched":
                stats["matched"] += 1
            elif status == "partial":
                stats["partial"] += 1
            else:
                stats["unmatched"] += 1
            enriched_positions.append(enriched)

        logger.info(
            "enrichment: matched=%s partial=%s unmatched=%s",
            stats.get("matched", 0),
            stats.get("partial", 0),
            stats.get("unmatched", 0),
        )

        return enriched_positions, stats

    # ------------------------------------------------------------------
    # Core enrichment logic
    # ------------------------------------------------------------------

    def _enrich_single(self, position: Dict[str, Any], specs: List[SpecContext]) -> Dict[str, Any]:
        description = str(position.get("description") or "")
        unit = position.get("unit")
        bundle = self._extract_bundle(description, unit)

        score = 0.0
        evidence: List[Dict[str, Any]] = []

        # 1. Exact code match using KROS/ÚRS dictionary
        code = str(position.get("code") or "").strip().upper()
        if code and code in self.kros_index:
            entry = self.kros_index[code]
            evidence.append(
                {
                    "source": "kb:B1",
                    "reason": "kros_code_exact",
                    "snippet": entry.get("description"),
                }
            )
            if entry.get("section") and not position.get("section"):
                position["section"] = entry.get("section")
            if entry.get("unit") and not position.get("unit"):
                position["unit"] = entry.get("unit")
            score += 0.55
        else:
            entry, similarity = self._match_kros_description(bundle)
            if entry and similarity >= 0.45:
                evidence.append(
                    {
                        "source": "kb:B1",
                        "reason": "kros_description_similarity",
                        "snippet": entry.get("description"),
                    }
                )
                if not code:
                    position["code"] = entry.get("code")
                if entry.get("section") and not position.get("section"):
                    position["section"] = entry.get("section")
                score += min(0.45, similarity)

        # 2. ČSN references from standards (B2)
        for token in bundle.csn:
            references = self.csn_index.get(token)
            if not references:
                continue
            evidence.append({
                "source": references[0].get("source"),
                "reason": "csn_reference",
                "snippet": references[0].get("snippet"),
            })
            score += 0.15
            break

        # 3. Drawing specifications
        spec_context, spec_score = self._select_best_spec(bundle, specs)
        if spec_context and spec_score > 0:
            spec_data = spec_context.data
            if spec_data.get("technical_specs"):
                position.setdefault("technical_specs", spec_data["technical_specs"])
            position["drawing_source"] = {
                "drawing": spec_data.get("file"),
                "page": spec_data.get("page"),
                "anchor": spec_data.get("anchor"),
            }
            evidence.append(
                {
                    "source": f"drawing:{spec_data.get('file')}",
                    "reason": "drawing_spec_match",
                    "snippet": spec_context.snippet,
                }
            )
            score += min(0.5, spec_score)

        score = min(score, 1.0)

        if score >= self.score_exact:
            match = "exact"
            status = "matched"
        elif score >= self.score_partial:
            match = "partial"
            status = "partial"
        else:
            match = "none"
            status = "unmatched"

        enrichment_block = {
            "match": match,
            "score": round(score, 4),
            "evidence": evidence[: self.max_evidence],
        }

        position["enrichment_status"] = status
        position["enrichment_score"] = enrichment_block["score"]
        position["enrichment"] = enrichment_block

        return position

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _prepare_spec(self, spec: Dict[str, Any]) -> SpecContext:
        technical = spec.get("technical_specs") or {}
        parts = [
            str(spec.get("text") or ""),
            str(spec.get("anchor") or ""),
        ]
        if isinstance(technical, dict):
            for value in technical.values():
                if isinstance(value, (list, tuple)):
                    parts.append(" ".join(str(item) for item in value))
                else:
                    parts.append(str(value))
        combined = " ".join(part for part in parts if part)
        bundle = self._extract_bundle(combined, technical.get("unit") if isinstance(technical, dict) else None)
        snippet = spec.get("text") or spec.get("anchor") or combined[:160]
        return SpecContext(data=spec, bundle=bundle, unit=bundle.unit, snippet=snippet)

    def _extract_bundle(self, text: str, unit: Any = None) -> TokenBundle:
        raw = text or ""
        normalized = unicodedata.normalize("NFKD", raw)
        ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        ascii_lower = ascii_text.lower()

        tokens = set(re.findall(r"[a-z0-9]{3,}", ascii_lower))
        codes = {
            re.sub(r"[^0-9A-Z]", "", match.upper())
            for match in re.findall(r"\b\d{3}[\s/-]?\d{2}[\s/-]?\d{3}\b", raw, flags=re.I)
        }
        concretes = {match.upper() for match in re.findall(r"C\d{1,2}/\d{1,2}", raw, flags=re.I)}
        exposures = {match.upper() for match in re.findall(r"X[CDFA]\d(?:/\d)?", raw, flags=re.I)}
        diameters = {re.sub(r"\s+", "", match.upper()) for match in re.findall(r"Ø\s*\d+", raw)}
        csn_tokens = {
            self._normalise_csn_token(match)
            for match in re.findall(r"ČSN\s*[0-9]{2}[\s\-]?[0-9]{2,3}(?:[\s\-]?[0-9]{1,3})?", raw, flags=re.I)
        }
        csn_tokens.discard("")

        unit_token = self._normalise_unit(unit)

        return TokenBundle(
            raw=raw,
            normalized=ascii_lower,
            tokens=tokens,
            codes=codes,
            concretes=concretes,
            exposures=exposures,
            diameters=diameters,
            csn=csn_tokens,
            unit=unit_token,
        )

    def _select_best_spec(
        self, bundle: TokenBundle, specs: List[SpecContext]
    ) -> Tuple[SpecContext | None, float]:
        best_context: SpecContext | None = None
        best_score = 0.0

        for context in specs:
            score = self._score_spec(bundle, context)
            if score > best_score:
                best_score = score
                best_context = context

        if best_score < 0.25:
            return None, 0.0

        return best_context, best_score

    def _score_spec(self, bundle: TokenBundle, context: SpecContext) -> float:
        spec_bundle = context.bundle

        overlap = len(bundle.tokens & spec_bundle.tokens)
        overlap_ratio = overlap / max(1, len(bundle.tokens))
        score = min(overlap_ratio * 0.4, 0.4)

        if bundle.codes & spec_bundle.codes:
            score += 0.25
        if bundle.concretes & spec_bundle.concretes:
            score += 0.25
        if bundle.exposures & spec_bundle.exposures:
            score += 0.15
        if bundle.diameters & spec_bundle.diameters:
            score += 0.1

        if context.unit and context.unit == bundle.unit and context.unit:
            score += 0.1
        elif context.unit and context.unit in bundle.tokens:
            score += 0.05

        similarity = SequenceMatcher(None, bundle.normalized, spec_bundle.normalized).ratio()
        score += min(similarity * 0.15, 0.15)

        return min(score, 1.0)

    def _match_kros_description(
        self, bundle: TokenBundle
    ) -> Tuple[Dict[str, Any] | None, float]:
        best_entry: Dict[str, Any] | None = None
        best_score = 0.0

        for entry, entry_bundle in self._kros_entries:
            if not entry_bundle.tokens:
                continue
            overlap = len(bundle.tokens & entry_bundle.tokens)
            if not overlap:
                continue
            ratio = overlap / max(1, len(bundle.tokens))
            unit_bonus = 0.1 if entry_bundle.unit and entry_bundle.unit == bundle.unit else 0.0
            score = min(ratio + unit_bonus, 1.0)
            if score > best_score:
                best_score = score
                best_entry = entry

        return best_entry, best_score

    @staticmethod
    def _normalise_unit(unit: Any) -> str:
        return str(unit or "").strip().lower()

    @staticmethod
    def _normalise_csn_token(value: str) -> str:
        if not value:
            return ""
        ascii_value = unicodedata.normalize("NFKD", value)
        ascii_value = "".join(ch for ch in ascii_value if not unicodedata.combining(ch))
        digits = re.sub(r"[^0-9]", "", ascii_value)
        if not digits:
            return ""
        return f"CSN{digits}"


__all__ = ["PositionEnricher"]
