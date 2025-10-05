"""
Services package initialization.

All imports use full package paths (app.*) for proper module resolution.
"""

from app.services.registry import agent_registry
from app.services.normalization import czech_normalizer

__all__ = [
    "agent_registry",
    "czech_normalizer"
]
