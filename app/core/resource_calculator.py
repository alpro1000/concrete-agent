"""Resource calculator component."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.core.registry import registry

logger = logging.getLogger(__name__)


class ResourceCalculator:
    """Aggregate enriched positions into a resource report."""

    def calculate(self, enriched_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_quantity = 0.0
        missing_quantity = 0

        for position in enriched_positions:
            quantity = position.get("quantity")
            try:
                if quantity is None:
                    missing_quantity += 1
                    continue
                total_quantity += float(quantity)
            except (TypeError, ValueError):
                missing_quantity += 1

        report = {
            "total_positions": len(enriched_positions),
            "total_quantity": total_quantity,
            "positions_missing_quantity": missing_quantity,
        }

        logger.info("Resource calculator summary: %s", report)
        return report


registry.register_calculator("resource", ResourceCalculator)

__all__ = ["ResourceCalculator"]
