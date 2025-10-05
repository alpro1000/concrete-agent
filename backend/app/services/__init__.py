"""
Services package initialization.

All imports use full package paths (backend.app.*) for proper module resolution.
"""

from backend.app.services.registry import agent_registry
from backend.app.services.normalization import czech_normalizer

__all__ = [
    "agent_registry",
    "czech_normalizer"
]
