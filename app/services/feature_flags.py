"""Feature flag utilities for workflow enablement."""
from __future__ import annotations

"""Centralized feature flag helpers for workflows."""

import os
from typing import Dict, List, Optional

_TRUTHY = {"1", "true", "yes", "on", "y", "t"}
_FALSY = {"0", "false", "no", "off", "n", "f"}

# Canonical keys mapped to their supported aliases. Order matters: the first
# entry is the canonical environment variable name and has the highest
# precedence when multiple aliases are set simultaneously.
_ALIASES: Dict[str, List[str]] = {
    "ENABLE_WORKFLOW_A": [
        "ENABLE_WORKFLOW_A",
        "WORKFLOW_A_ENABLED",
        "FEATURE_WORKFLOW_A",
        "ENABLE_WORKFLOWA",
    ],
    "ENABLE_WORKFLOW_B": [
        "ENABLE_WORKFLOW_B",
        "WORKFLOW_B_ENABLED",
        "FEATURE_WORKFLOW_B",
        "ENABLE_WORKFLOWB",
    ],
}


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    """Parse a string value into a boolean using relaxed truthy/falsy rules."""

    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in _TRUTHY:
        return True
    if normalized in _FALSY:
        return False
    return default


def read_flag(canonical_key: str, default: bool = False) -> bool:
    """Read a feature flag using canonical key with alias fallbacks."""

    for env_name in _ALIASES.get(canonical_key, [canonical_key]):
        env_value = os.getenv(env_name)
        if env_value is not None:
            return _parse_bool(env_value, default=default)
    return default


def flags_summary() -> Dict[str, bool]:
    """Return a mapping with the current workflow feature flag states."""

    return {
        "ENABLE_WORKFLOW_A": read_flag("ENABLE_WORKFLOW_A", default=False),
        "ENABLE_WORKFLOW_B": read_flag("ENABLE_WORKFLOW_B", default=False),
    }


__all__ = ["read_flag", "flags_summary"]
