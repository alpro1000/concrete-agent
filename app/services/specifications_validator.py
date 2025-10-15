"""Validation of enriched positions against the knowledge base."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from app.core.kb_loader import init_kb_loader

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result for a single position."""

    position: Dict[str, object]
    errors: List[str]
    warnings: List[str]

    @property
    def status(self) -> str:
        if self.errors:
            return "failed"
        if self.warnings:
            return "warning"
        return "passed"


class SpecificationsValidator:
    """Check positions against OTSKP codes and simplified ČSN rules."""

    EXPOSURE_MIN_CLASS = {
        "XF2": 30,
        "XF3": 35,
        "XF4": 35,
        "XD2": 30,
        "XD3": 35,
        "XS2": 30,
        "XS3": 35,
        "XA2": 35,
        "XA3": 40,
    }

    def __init__(self) -> None:
        kb = init_kb_loader()
        self.otskp_index = self._build_otskp_index(kb.data.get("B1_kros_urs_codes", {}))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self, positions: Iterable[Dict[str, object]]
    ) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
        """Validate all positions and append validation metadata."""

        validated_positions: List[Dict[str, object]] = []
        stats = {"passed": 0, "warning": 0, "failed": 0}

        for position in positions:
            result = self._validate_single(dict(position))
            position_payload = result.position
            position_payload["validation_status"] = result.status
            position_payload["validation_results"] = {
                "errors": result.errors,
                "warnings": result.warnings,
            }

            stats[result.status] += 1
            validated_positions.append(position_payload)

        logger.info(
            "Validation summary → passed=%s, warning=%s, failed=%s",
            stats["passed"],
            stats["warning"],
            stats["failed"],
        )

        return validated_positions, stats

    # ------------------------------------------------------------------
    # Single position validation
    # ------------------------------------------------------------------

    def _validate_single(self, position: Dict[str, object]) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        code = str(position.get("code") or "").strip()
        unit = str(position.get("unit") or "").strip().lower()
        quantity = position.get("quantity")

        kb_entry = self._lookup_otskp(code)
        if kb_entry is None:
            errors.append("code_not_found_in_otskp")
        else:
            kb_unit = str(kb_entry.get("unit") or "").lower()
            if kb_unit and unit and kb_unit != unit:
                errors.append("unit_mismatch_with_otskp")

        if quantity is None:
            warnings.append("quantity_missing")
        else:
            try:
                if float(quantity) <= 0:
                    errors.append("quantity_non_positive")
            except (ValueError, TypeError):
                errors.append("quantity_invalid")

        self._check_concrete_rules(position, errors, warnings)

        return ValidationResult(position=position, errors=errors, warnings=warnings)

    # ------------------------------------------------------------------
    # Knowledge base helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_otskp_index(category_payload: Dict[str, object]) -> Dict[str, Dict[str, object]]:
        index: Dict[str, Dict[str, object]] = {}

        for data in category_payload.values():
            if isinstance(data, list):
                for item in data:
                    code = SpecificationsValidator._normalise_code(item.get("code") or item.get("znacka"))
                    if code:
                        index[code] = {
                            "name": item.get("name") or item.get("nazev"),
                            "unit": (item.get("unit") or item.get("MJ") or "").strip().lower(),
                            "unit_price": item.get("unit_price") or item.get("jedn_cena"),
                        }
            elif isinstance(data, dict):
                code = SpecificationsValidator._normalise_code(data.get("code") or data.get("znacka"))
                if code:
                    index[code] = {
                        "name": data.get("name") or data.get("nazev"),
                        "unit": (data.get("unit") or data.get("MJ") or "").strip().lower(),
                        "unit_price": data.get("unit_price") or data.get("jedn_cena"),
                    }

        return index

    def _lookup_otskp(self, code: str) -> Dict[str, object] | None:
        normalised = self._normalise_code(code)
        if not normalised:
            return None
        return self.otskp_index.get(normalised)

    @staticmethod
    def _normalise_code(code: object) -> str:
        if not code:
            return ""
        text = str(code).strip().upper()
        return re.sub(r"[^A-Z0-9]", "", text)

    # ------------------------------------------------------------------
    # ČSN EN 206 heuristics
    # ------------------------------------------------------------------

    def _check_concrete_rules(
        self,
        position: Dict[str, object],
        errors: List[str],
        warnings: List[str],
    ) -> None:
        specs = position.get("technical_specs") or {}
        concrete_class = str(specs.get("concrete_class") or "")
        exposures = specs.get("exposure") or []

        if not concrete_class and exposures:
            warnings.append("concrete_class_missing")
            return

        if not concrete_class:
            return

        class_value = self._extract_class_value(concrete_class)
        if class_value is None:
            warnings.append("concrete_class_unrecognised")
            return

        if not exposures:
            warnings.append("exposure_missing")
            return

        exposure_tokens = [str(item).upper() for item in exposures]
        for token in exposure_tokens:
            required = self.EXPOSURE_MIN_CLASS.get(token)
            if required and class_value < required:
                errors.append(f"exposure_{token}_requires_C{required}")

        if all(token.startswith("XC") for token in exposure_tokens):
            warnings.append("exposure_only_xc")

    @staticmethod
    def _extract_class_value(concrete_class: str) -> int | None:
        match = re.search(r"C(\d{2})", concrete_class.upper())
        return int(match.group(1)) if match else None


__all__ = ["SpecificationsValidator"]

