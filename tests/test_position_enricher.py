import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.position_enricher import PositionEnricher


@pytest.fixture()
def position_enricher() -> PositionEnricher:
    """Provide an instance with enrichment disabled to avoid KB access."""

    return PositionEnricher(enabled=False)


@pytest.mark.parametrize(
    "text",
    [
        "Код: 123 45 678",
        "Код: 123-45-678",
        "Код: 123/45/678",
    ],
)
def test_extract_bundle_supports_multiple_separators(
    position_enricher: PositionEnricher, text: str
) -> None:
    bundle = position_enricher._extract_bundle(text)

    assert "12345678" in bundle.codes


def test_extract_bundle_handles_missing_codes(position_enricher: PositionEnricher) -> None:
    bundle = position_enricher._extract_bundle("Описание без кодов и с символами - /")

    assert bundle.codes == set()
