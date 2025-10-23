"""Tests for workflow feature flag helpers."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from app.services.feature_flags import read_flag


@pytest.mark.parametrize(
    "value",
    ["1", "true", "yes", "on", "y", "t", "TRUE", "Yes", " On "]
)
def test_truthy_values(monkeypatch, value: str) -> None:
    monkeypatch.setenv("ENABLE_WORKFLOW_A", value)
    assert read_flag("ENABLE_WORKFLOW_A") is True


@pytest.mark.parametrize(
    "value",
    ["0", "false", "no", "off", "n", "f", "FALSE", " No "]
)
def test_falsy_values(monkeypatch, value: str) -> None:
    monkeypatch.setenv("ENABLE_WORKFLOW_B", value)
    assert read_flag("ENABLE_WORKFLOW_B") is False


def test_alias_precedence(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_WORKFLOW_B", raising=False)
    monkeypatch.setenv("WORKFLOW_B_ENABLED", "true")
    monkeypatch.setenv("FEATURE_WORKFLOW_B", "false")
    assert read_flag("ENABLE_WORKFLOW_B") is True


def test_default_when_missing(monkeypatch) -> None:
    for key in ("ENABLE_WORKFLOW_A", "WORKFLOW_A_ENABLED"):
        monkeypatch.delenv(key, raising=False)
    assert read_flag("ENABLE_WORKFLOW_A", default=False) is False
