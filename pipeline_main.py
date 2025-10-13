"""Compatibility wrapper for running the pipeline from the project root."""
from __future__ import annotations

import asyncio

from app.main import main


if __name__ == "__main__":
    asyncio.run(main())
