import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.kb_loader import get_knowledge_base
from app.services.position_enricher import PositionEnricher
from app.services.specifications_validator import SpecificationsValidator


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


def test_desc_and_marker_fallback_promotes_amber() -> None:
    kb = get_knowledge_base()
    catalog = kb.kb_b1.setdefault("tskp", {})

    test_code = "TSKP-TEST-FALLBACK-001"
    normalized = re.sub(r"[^A-Z0-9]", "", test_code.upper())
    entry_payload = {
        "code": test_code,
        "normalized": normalized,
        "name": "Mostní římsa C30/37 XC2 XF3 XA2 s výztuží B500B S235 Ø16@200 krytí 60 mm",
        "unit": "m3",
        "tech_spec": "Železobetonová římsa s krytím 60 mm",
        "system": "TSKP",
    }

    previous_code_entry = catalog.get(test_code)
    previous_norm_entry = catalog.get(normalized)

    try:
        catalog[test_code] = entry_payload
        if normalized and normalized not in catalog:
            catalog[normalized] = entry_payload
        kb._kros_index = None

        enricher = PositionEnricher(enabled=True)

        description = (
            "Betonáž mostní římsy C30/37 s expozicemi XC2, XF3, XA2 a výztuží B500B/S235, Ø16@200, krytí 60 mm"
        )
        drawing_payload = {
            "specifications": [
                {
                    "file": "spec.pdf",
                    "page": 1,
                    "anchor": "Mostní římsa",
                    "technical_specs": {
                        "concrete_class": ["C30/37"],
                        "exposure": ["XC2"],
                        "reinforcement": ["B500B"],
                        "steel_grade": ["S235"],
                        "reinforcement_mesh": ["Ø16@200"],
                        "concrete_cover": ["krytí 60 mm"],
                    },
                }
            ],
            "markers": {
                "concrete_class": ["C30/37"],
                "exposure_env": ["XC2", "XF3", "XA2"],
                "steel_grade": ["B500B", "S235"],
                "rebar_layout": ["Ø16@200"],
                "cover_depth": ["krytí 60 mm"],
            },
        }

        positions = [{"description": description, "code": "", "unit": "m3"}]
        enriched_positions, stats = enricher.enrich(positions, drawing_payload)
        enriched = enriched_positions[0]

        assert enriched["match_status"] == "partial"
        assert enriched["candidate_codes"]
        assert any(candidate["code"] == test_code for candidate in enriched["candidate_codes"])
        assert stats["rules"]["markers"] >= 1
        assert any(token.startswith("desc_sim") for token in enriched.get("evidence", []))

        validator = SpecificationsValidator()
        validated_positions, validation_stats = validator.validate(enriched_positions)
        validated = validated_positions[0]

        assert validated["validation_status"] == "warning"
        assert validation_stats["warning"] == 1
        candidates = validated.get("validation_candidates", [])
        assert any(candidate["code"] == test_code for candidate in candidates)
        assert "Код позиции не подтверждён" in validated.get("validation_advice", "")

    finally:
        if previous_code_entry is None:
            catalog.pop(test_code, None)
        else:
            catalog[test_code] = previous_code_entry
        if normalized != test_code:
            if previous_norm_entry is None:
                catalog.pop(normalized, None)
            else:
                catalog[normalized] = previous_norm_entry
        kb._kros_index = None
