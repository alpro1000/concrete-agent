import logging
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
    steel_grades: set[str]
    rebar_layouts: set[str]
    cover_depths: set[str]
    surface_categories: set[str]
    norm_refs: set[str]
    geometry_tokens: set[str]
    bridge_tokens: set[str]
    csn: set[str]
    unit: str


@dataclass
class SpecContext:
    data: Dict[str, Any]
    bundle: TokenBundle
    unit: str
    snippet: str


@dataclass
class KBEntry:
    code: str
    name: str
    description: str
    unit: str
    system: str
    tech_spec: str
    bundle: TokenBundle


@dataclass
class CandidateScore:
    entry: KBEntry
    score: float
    base_score: float
    marker_tokens: List[str]


class PositionEnricher:
    """Attach technical metadata to bill-of-quantities positions."""

    MARKER_KEYS = (
        "concrete_class",
        "exposure_env",
        "steel_grade",
        "rebar_layout",
        "cover_depth",
        "surface_category",
        "norm_refs",
        "geometry_tokens",
        "bridge_tokens",
    )

    CONCRETE_PATTERN = re.compile(r"C\d{1,2}/\d{1,2}", re.IGNORECASE)
    EXPOSURE_PATTERN = re.compile(r"X[ACDFS]\d(?:[AB])?", re.IGNORECASE)
    STEEL_PATTERN = re.compile(r"B\d{3}[A-Z]?", re.IGNORECASE)
    STEEL_GENERAL_PATTERN = re.compile(r"S\d{3}", re.IGNORECASE)
    REBAR_PATTERN = re.compile(r"(?:Ø|⌀)\s*\d{1,2}\s*@\s*\d{2,3}", re.IGNORECASE)
    COVER_PATTERN = re.compile(r"kryt[íi]\s*\d{1,3}(?:/\d{1,3})?\s*mm", re.IGNORECASE)
    SURFACE_PATTERN = re.compile(r"\b(?:A[a-d]?|B[a-d]?|C[12][a-d]?|D[a-b]?|E)\b", re.IGNORECASE)
    NORM_PATTERN = re.compile(
        r"\b(?:ČSN\s*(?:EN\s*)?\d{2,3}(?:[+A-Z0-9\/-]+)?|ČSN\s*EN\s*206(?:\s*\+\s*A2)?|TKP\s*\d{1,2}|TP\s*\d{2,3}|VL4\s*\d{3}\.\d{2})\b",
        re.IGNORECASE,
    )
    GEOMETRY_PATTERN = re.compile(
        r"((?:Ø|⌀)\s*\d{2,4})|(\b\d{1,2}[.,]\d\s*m\b)|(\b\d{2,3}/\d{2,3}\s*mm\b)|(\b\d{1,4}\s*mm\b)",
        re.IGNORECASE,
    )
    BRIDGE_KEYWORDS = {
        "pilot",
        "pilota",
        "piloty",
        "pilotu",
        "vrubovy",
        "vrubový",
        "kloub",
        "niveleta",
        "nivelety",
        "opěra",
        "opery",
        "opěr",
        "římsa",
        "rims",
        "rimsa",
    }

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.score_exact = settings.ENRICH_SCORE_EXACT
        self.score_partial = settings.ENRICH_SCORE_PARTIAL
        self.max_evidence = settings.ENRICH_MAX_EVIDENCE

        self.kros_index: Dict[str, Dict[str, Any]] = {}
        self._kb_entries: List[KBEntry] = []
        self._code_index: Dict[str, KBEntry] = {}
        self._bridge_index: Dict[str, List[str]] = {}
        self.csn_index: Dict[str, List[Dict[str, str]]] = {}

        if self.enabled:
            kb = get_knowledge_base()
            self.kros_index = kb.get_kros_index()
            self.csn_index = kb.get_csn_index()
            for code, entry in self.kros_index.items():
                if not code:
                    continue
                name = entry.get("name") or entry.get("description") or ""
                description = entry.get("description") or name
                unit = entry.get("unit") or ""
                tech_spec = entry.get("tech_spec") or ""
                system = entry.get("system") or ""
                searchable = " ".join(part for part in (name, description, tech_spec) if part)
                bundle = self._extract_bundle(searchable, unit)
                kb_entry = KBEntry(
                    code=code,
                    name=name,
                    description=description,
                    unit=unit,
                    system=system,
                    tech_spec=tech_spec,
                    bundle=bundle,
                )
                self._register_kb_entry(kb_entry, entry)

            logger.debug("position_enricher: regex_sanity=ok (classes normalized)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enrich(
        self,
        positions: Iterable[Dict[str, Any]],
        drawing_payload: Any,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not self.enabled:
            enriched_positions: List[Dict[str, Any]] = []
            for position in positions:
                payload = dict(position)
                payload.setdefault("enrichment_status", "unmatched")
                payload.setdefault("match_status", "unmatched")
                payload.setdefault("candidate_codes", [])
                payload.setdefault("evidence", [])
                payload["enrichment_score"] = 0.0
                payload["enrichment"] = {"match": "none", "score": 0.0, "evidence": []}
                enriched_positions.append(payload)
            stats = {
                "enabled": False,
                "matched": 0,
                "partial": 0,
                "unmatched": len(enriched_positions),
            }
            return enriched_positions, stats

        specs_input, markers_payload = self._extract_drawing_inputs(drawing_payload)
        spec_contexts = [self._prepare_spec(spec) for spec in specs_input]
        marker_context = self._build_marker_context(markers_payload)

        enriched_positions: List[Dict[str, Any]] = []
        stats = {"enabled": True, "matched": 0, "partial": 0, "unmatched": 0}
        rule_stats = {"exact": 0, "bridge": 0, "desc": 0, "markers": 0}

        for position in positions:
            enriched, used_rules = self._enrich_single(dict(position), spec_contexts, marker_context)
            status = str(enriched.get("enrichment_status") or "").lower()
            if status == "matched":
                stats["matched"] += 1
            elif status == "partial":
                stats["partial"] += 1
            else:
                stats["unmatched"] += 1
            for rule in used_rules:
                if rule in rule_stats:
                    rule_stats[rule] += 1
            enriched_positions.append(enriched)

        logger.info(
            "enrichment: matched=%s partial=%s unmatched=%s",
            stats.get("matched", 0),
            stats.get("partial", 0),
            stats.get("unmatched", 0),
        )
        logger.info(
            "enrichment rules: exact=%s bridge=%s desc=%s markers=%s",
            rule_stats.get("exact", 0),
            rule_stats.get("bridge", 0),
            rule_stats.get("desc", 0),
            rule_stats.get("markers", 0),
        )

        stats["rules"] = rule_stats
        return enriched_positions, stats

    @staticmethod
    def _extract_drawing_inputs(
        payload: Any,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if isinstance(payload, dict):
            specs = payload.get("specifications")
            markers = payload.get("markers") or {}
            if not isinstance(specs, list):
                specs_list: List[Dict[str, Any]] = []
            else:
                specs_list = list(specs)
            return specs_list, markers
        if payload is None:
            return [], {}
        return list(payload), {}

    def _build_marker_context(
        self, markers_payload: Dict[str, Any]
    ) -> Dict[str, set[str]]:
        context = {marker: set() for marker in self.MARKER_KEYS}
        if not isinstance(markers_payload, dict):
            return context
        for marker_type, entries in markers_payload.items():
            if marker_type not in context:
                continue
            values = entries if isinstance(entries, list) else []
            for entry in values:
                if isinstance(entry, dict):
                    value = entry.get("value")
                else:
                    value = entry
                normalised = self._normalise_marker_value(marker_type, value)
                if normalised:
                    context[marker_type].add(normalised)
        return context

    def _enrich_single(
        self,
        position: Dict[str, Any],
        specs: List[SpecContext],
        marker_context: Dict[str, set[str]],
    ) -> Tuple[Dict[str, Any], set[str]]:
        description = str(position.get("description") or "")
        unit = position.get("unit")
        bundle = self._extract_bundle(description, unit)

        evidence: List[str] = []
        candidate_codes: List[Dict[str, Any]] = []
        used_rules: set[str] = set()
        match_status = "unmatched"
        enrichment_score = 0.0

        raw_code = str(position.get("code") or "").strip()
        matched_entry = self._lookup_code(raw_code)
        if not matched_entry and raw_code:
            matched_entry = self._lookup_code(self._normalise_code(raw_code))

        if matched_entry:
            match_status = "matched"
            used_rules.add("exact")
            evidence.append("exact_code")
            enrichment_score = 1.0
            candidate_codes = [
                {"code": matched_entry.code, "system": matched_entry.system or "", "score": 1.0}
            ]
            position["code"] = matched_entry.code
            if matched_entry.unit and not position.get("unit"):
                position["unit"] = matched_entry.unit
            if matched_entry.system:
                position["matched_system"] = matched_entry.system
        else:
            bridged_entry = self._resolve_bridge(raw_code)
            if bridged_entry:
                match_status = "matched"
                used_rules.add("bridge")
                evidence.append(f"bridge:{raw_code or '?'}→{bridged_entry.code}")
                enrichment_score = 0.95
                candidate_codes = [
                    {"code": bridged_entry.code, "system": bridged_entry.system or "", "score": 0.95}
                ]
                position["code"] = bridged_entry.code
                if bridged_entry.unit and not position.get("unit"):
                    position["unit"] = bridged_entry.unit
                if bridged_entry.system:
                    position["matched_system"] = bridged_entry.system
            else:
                candidates = self._score_candidates(bundle, marker_context, limit=5)
                if candidates:
                    candidate_codes = [
                        {
                            "code": candidate.entry.code,
                            "system": candidate.entry.system or "",
                            "score": round(candidate.score, 4),
                        }
                        for candidate in candidates
                    ]
                    top_candidate = candidates[0]
                    enrichment_score = top_candidate.score
                    desc_evidence = f"desc_sim_{top_candidate.base_score:.2f}"
                    marker_evidence = ", ".join(top_candidate.marker_tokens)
                    next_score = candidates[1].score if len(candidates) > 1 else 0.0

                    if top_candidate.base_score >= 0.90:
                        match_status = "partial"
                        used_rules.add("desc")
                        evidence.append(desc_evidence)
                        if marker_evidence:
                            evidence.append(f"markers:{marker_evidence}")
                    elif marker_evidence and top_candidate.score - next_score >= 0.15 and top_candidate.score >= 0.65:
                        match_status = "partial"
                        used_rules.add("markers")
                        evidence.append(desc_evidence)
                        evidence.append(f"markers:{marker_evidence}")
                    elif top_candidate.base_score >= 0.75 and top_candidate.score >= 0.80:
                        match_status = "partial"
                        used_rules.add("desc")
                        evidence.append(desc_evidence)

                    if top_candidate.entry.system and match_status in {"matched", "partial"}:
                        position["matched_system"] = top_candidate.entry.system

        csn_hint = self._collect_csn_evidence(bundle)
        if csn_hint:
            evidence.append(csn_hint)

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
            evidence.append(f"drawing:{spec_data.get('file')}#p{spec_data.get('page')}")
            enrichment_score = max(enrichment_score, min(0.7, spec_score))

        enrichment_score = min(enrichment_score, 1.0)

        position["match_status"] = match_status
        position["candidate_codes"] = candidate_codes
        position["evidence"] = evidence[: self.max_evidence]

        if match_status == "matched":
            enrichment_status = "matched"
            match_label = "exact"
        elif match_status == "partial":
            enrichment_status = "partial"
            match_label = "partial"
        else:
            enrichment_status = "unmatched"
            match_label = "none"

        enrichment_block = {
            "match": match_label,
            "score": round(enrichment_score, 4),
            "evidence": position["evidence"],
        }

        if candidate_codes:
            enrichment_block["candidates"] = [
                {
                    "code": candidate["code"],
                    "description": self.kros_index.get(candidate["code"], {}).get("description") or "",
                    "unit": self.kros_index.get(candidate["code"], {}).get("unit") or "",
                    "score": candidate["score"],
                }
                for candidate in candidate_codes[:5]
            ]

        position["enrichment_status"] = enrichment_status
        position["enrichment_score"] = enrichment_block["score"]
        position["enrichment"] = enrichment_block

        return position, used_rules

    def _collect_csn_evidence(self, bundle: TokenBundle) -> Optional[str]:
        for token in bundle.csn:
            if token in self.csn_index:
                return f"csn:{token}"
        return None

    def _score_candidates(
        self,
        bundle: TokenBundle,
        marker_context: Dict[str, set[str]],
        limit: int = 5,
    ) -> List[CandidateScore]:
        scored: List[CandidateScore] = []
        for entry in self._kb_entries:
            final_score, base_score, marker_tokens = self._score_entry(bundle, entry, marker_context)
            if final_score <= 0:
                continue
            scored.append(
                CandidateScore(entry=entry, score=final_score, base_score=base_score, marker_tokens=marker_tokens)
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def _score_entry(
        self,
        bundle: TokenBundle,
        entry: KBEntry,
        marker_context: Dict[str, set[str]],
    ) -> Tuple[float, float, List[str]]:
        entry_bundle = entry.bundle
        if not entry_bundle.tokens:
            return 0.0, 0.0, []
        token_overlap = len(bundle.tokens & entry_bundle.tokens)
        if token_overlap == 0:
            return 0.0, 0.0, []
        union_size = len(bundle.tokens | entry_bundle.tokens)
        jaccard = token_overlap / max(1, union_size)
        sequence_ratio = SequenceMatcher(None, bundle.normalized, entry_bundle.normalized).ratio()
        base_score = max(jaccard, sequence_ratio)
        if entry.unit and bundle.unit and entry.unit.lower() == bundle.unit.lower():
            base_score = min(1.0, base_score + 0.05)
        marker_bonus, marker_tokens = self._calculate_marker_bonus(bundle, entry_bundle, marker_context)
        final_score = min(1.0, base_score + marker_bonus)
        if final_score < 0.45:
            return 0.0, base_score, marker_tokens
        return final_score, base_score, marker_tokens

    def _calculate_marker_bonus(
        self,
        bundle: TokenBundle,
        entry_bundle: TokenBundle,
        marker_context: Dict[str, set[str]],
    ) -> Tuple[float, List[str]]:
        attribute_map = {
            "concrete_class": "concretes",
            "exposure_env": "exposures",
            "steel_grade": "steel_grades",
            "rebar_layout": "rebar_layouts",
            "cover_depth": "cover_depths",
            "surface_category": "surface_categories",
            "norm_refs": "norm_refs",
            "geometry_tokens": "geometry_tokens",
            "bridge_tokens": "bridge_tokens",
        }
        weights = {
            "concrete_class": 0.12,
            "exposure_env": 0.1,
            "steel_grade": 0.08,
            "rebar_layout": 0.06,
            "cover_depth": 0.05,
            "surface_category": 0.03,
            "norm_refs": 0.04,
            "geometry_tokens": 0.03,
            "bridge_tokens": 0.04,
        }
        matched_tokens: List[str] = []
        bonus = 0.0

        for marker_key, attribute in attribute_map.items():
            entry_values = getattr(entry_bundle, attribute)
            if not entry_values:
                continue
            bundle_values = getattr(bundle, attribute)
            context_values = marker_context.get(marker_key, set())
            hits = (entry_values & bundle_values) | (entry_values & context_values)
            if hits:
                matched_tokens.extend(sorted(hits))
                bonus += weights.get(marker_key, 0.0)

        return min(bonus, 0.35), matched_tokens

    def _resolve_bridge(self, code: str) -> Optional[KBEntry]:
        normalized = self._normalise_code(code)
        if not normalized:
            return None
        for candidate_code in self._bridge_index.get(normalized, []):
            entry = self._lookup_code(candidate_code)
            if entry:
                return entry
        return None

    def _lookup_code(self, code: str) -> Optional[KBEntry]:
        if not code:
            return None
        key = code.strip().upper()
        if key in self._code_index:
            return self._code_index[key]
        normalized = self._normalise_code(key)
        if normalized and normalized in self._code_index:
            return self._code_index[normalized]
        compact = key.replace(" ", "").replace("-", "")
        return self._code_index.get(compact)

    def _register_kb_entry(self, entry: KBEntry, raw_entry: Dict[str, Any]) -> None:
        self._kb_entries.append(entry)
        for alias in self._generate_code_aliases(entry.code):
            self._code_index.setdefault(alias, entry)

        alias_fields = raw_entry.get("aliases") or raw_entry.get("alias_codes") or []
        if isinstance(alias_fields, str):
            alias_fields = [alias_fields]
        for alias_code in alias_fields:
            for variant in self._generate_code_aliases(alias_code):
                self._code_index.setdefault(variant, entry)
            norm_alias = self._normalise_code(alias_code)
            if norm_alias:
                bucket = self._bridge_index.setdefault(norm_alias, [])
                if entry.code not in bucket:
                    bucket.append(entry.code)

        primary_norm = self._normalise_code(entry.code)
        if primary_norm:
            bucket = self._bridge_index.setdefault(primary_norm, [])
            if entry.code not in bucket:
                bucket.append(entry.code)

        related_codes = raw_entry.get("bridge_codes") or raw_entry.get("mapped_codes") or raw_entry.get("related_codes")
        if isinstance(related_codes, str):
            related_codes = [related_codes]
        if isinstance(related_codes, (list, tuple)):
            for candidate in related_codes:
                norm_candidate = self._normalise_code(candidate)
                if not norm_candidate:
                    continue
                bucket = self._bridge_index.setdefault(norm_candidate, [])
                if entry.code not in bucket:
                    bucket.append(entry.code)

    def _generate_code_aliases(self, code: str) -> List[str]:
        aliases: set[str] = set()
        if not code:
            return []
        text = str(code).strip().upper()
        if text:
            aliases.add(text)
        normalized = self._normalise_code(text)
        if normalized:
            aliases.add(normalized)
        compact = text.replace(" ", "").replace("-", "")
        if compact:
            aliases.add(compact)
        if text.startswith("ÚRS"):
            aliases.add(text.replace("ÚRS", "").strip())
        if text.startswith("OTSKP"):
            aliases.add(text.replace("OTSKP", "").strip())
        return [alias for alias in aliases if alias]

    @staticmethod
    def _normalise_code(code: str | None) -> str:
        if not code:
            return ""
        return re.sub(r"[^A-Z0-9]", "", str(code).upper())

    @staticmethod
    def _normalise_marker_value(marker_type: str, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if marker_type in {"concrete_class", "exposure_env", "steel_grade", "surface_category", "norm_refs"}:
            return text.upper()
        if marker_type == "rebar_layout":
            cleaned = text.replace(" ", "").replace("⌀", "Ø")
            return cleaned.upper()
        if marker_type == "cover_depth":
            return text
        if marker_type == "geometry_tokens":
            return text.replace("⌀", "Ø")
        if marker_type == "bridge_tokens":
            return text
        return text

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
        bundle = self._extract_bundle(
            combined,
            technical.get("unit") if isinstance(technical, dict) else None,
        )
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
            for match in re.findall(r"\b\d{3}[\s\/-]?\d{2}[\s\/-]?\d{3}\b", raw, flags=re.I)
        }
        concretes = {match.upper() for match in self.CONCRETE_PATTERN.findall(raw)}
        exposures = set(self.EXPOSURE_PATTERN.findall(raw.upper()))
        for combo in re.findall(r"X[ACDFS]\d(?:[AB])?(?:[+/]X[ACDFS]\d(?:[AB])?)+", raw, flags=re.I):
            for part in re.split(r"[+/]", combo.upper()):
                if self.EXPOSURE_PATTERN.fullmatch(part):
                    exposures.add(part)
        steel_grades = {match.upper() for match in self.STEEL_PATTERN.findall(raw)}
        steel_grades.update({match.upper() for match in self.STEEL_GENERAL_PATTERN.findall(raw)})
        rebar_layouts = {self._normalise_rebar(value) for value in self.REBAR_PATTERN.findall(raw)}
        cover_depths = set()
        for match in self.COVER_PATTERN.finditer(raw):
            digits = re.findall(r"\d{1,3}", match.group(0))
            if not digits:
                continue
            if len(digits) == 1:
                cover_depths.add(f"krytí {digits[0]} mm")
            else:
                cover_depths.add(f"krytí {'/'.join(digits)} mm")
        surface_categories = {match.group(0).upper() for match in self.SURFACE_PATTERN.finditer(raw)}
        norm_refs = set()
        for match in self.NORM_PATTERN.finditer(raw):
            cleaned = re.sub(r"\s+", " ", match.group(0).strip())
            norm_refs.add(cleaned.replace(" + ", "+"))
        geometry_tokens = set()
        for match in self.GEOMETRY_PATTERN.finditer(raw):
            token = next((group for group in match.groups() if group), "")
            if not token:
                continue
            normalized_token = token.replace(" ", "").replace("⌀", "Ø")
            geometry_tokens.add(normalized_token)
        bridge_tokens = {
            word for word in re.findall(r"[A-Za-zÁ-Žá-ž]+", raw)
            if word.lower() in self.BRIDGE_KEYWORDS
        }
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
            steel_grades=steel_grades,
            rebar_layouts={value for value in rebar_layouts if value},
            cover_depths=cover_depths,
            surface_categories=surface_categories,
            norm_refs=norm_refs,
            geometry_tokens=geometry_tokens,
            bridge_tokens=bridge_tokens,
            csn=csn_tokens,
            unit=unit_token,
        )

    @staticmethod
    def _normalise_rebar(value: str) -> str:
        cleaned = value.upper().replace(" ", "")
        return cleaned.replace("⌀", "Ø")

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
        score = min(overlap_ratio * 0.35, 0.35)

        if bundle.codes & spec_bundle.codes:
            score += 0.2
        if bundle.concretes & spec_bundle.concretes:
            score += 0.2
        if bundle.exposures & spec_bundle.exposures:
            score += 0.15
        if bundle.steel_grades & spec_bundle.steel_grades:
            score += 0.1
        if bundle.rebar_layouts & spec_bundle.rebar_layouts:
            score += 0.08
        if bundle.cover_depths & spec_bundle.cover_depths:
            score += 0.05
        if bundle.surface_categories & spec_bundle.surface_categories:
            score += 0.04
        if bundle.norm_refs & spec_bundle.norm_refs:
            score += 0.04
        if bundle.geometry_tokens & spec_bundle.geometry_tokens:
            score += 0.03

        if context.unit and context.unit == bundle.unit and context.unit:
            score += 0.05
        elif context.unit and context.unit in bundle.tokens:
            score += 0.02

        similarity = SequenceMatcher(None, bundle.normalized, spec_bundle.normalized).ratio()
        score += min(similarity * 0.1, 0.1)

        return min(score, 1.0)

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
