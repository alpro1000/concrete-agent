"""
app.core — public API exports.

Import from here instead of deep paths to keep coupling low.
"""
from app.core.auth import verify_token  # noqa: F401 — re-export for importers

__all__ = ["verify_token"]
