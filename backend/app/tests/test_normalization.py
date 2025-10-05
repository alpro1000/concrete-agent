"""
Test for Czech normalization service.
"""

import pytest
from backend.app.services.normalization import (
    remove_diacritics,
    normalize_to_ascii,
    is_czech_text,
    preserve_czech_encoding,
    CzechNormalizer
)


def test_remove_diacritics():
    """Test removing Czech diacritics."""
    text = "Příliš žluťoučký kůň úpěl ďábelské ódy"
    result = remove_diacritics(text)
    
    assert "ř" not in result
    assert "ž" not in result
    assert "ů" not in result
    assert "Příliš" not in result


def test_normalize_to_ascii():
    """Test normalization to ASCII."""
    text = "Beton C25/30 - třída prostředí XC2"
    result = normalize_to_ascii(text)
    
    # Should convert to ASCII
    assert all(ord(char) < 128 for char in result)


def test_is_czech_text():
    """Test detection of Czech text."""
    czech_text = "Betonářská ocel"
    english_text = "Concrete steel"
    
    assert is_czech_text(czech_text) is True
    assert is_czech_text(english_text) is False


def test_preserve_czech_encoding():
    """Test preserving Czech encoding."""
    text = "Beton ČSN"
    result = preserve_czech_encoding(text)
    
    # Should preserve characters
    assert "Č" in result
    assert "S" in result
    assert "N" in result


def test_czech_normalizer_strategies():
    """Test different normalization strategies."""
    normalizer = CzechNormalizer()
    text = "Příliš žluťoučký kůň"
    
    # Preserve strategy
    preserved = normalizer.normalize(text, strategy="preserve")
    assert "ř" in preserved
    
    # Remove strategy
    removed = normalizer.normalize(text, strategy="remove")
    assert "ř" not in removed
    
    # ASCII strategy
    ascii_result = normalizer.normalize(text, strategy="ascii")
    assert all(ord(char) < 128 for char in ascii_result)


def test_detect_encoding_issues():
    """Test detection of encoding issues."""
    normalizer = CzechNormalizer()
    
    good_text = "Normal text"
    bad_text = "Text with Ã© issues"
    
    assert normalizer.detect_encoding_issues(good_text) is False
    assert normalizer.detect_encoding_issues(bad_text) is True
