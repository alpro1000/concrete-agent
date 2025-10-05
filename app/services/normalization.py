"""
Czech diacritic normalization service.
Handles encoding/decoding of Czech characters.
"""

import unicodedata
from typing import Dict


# Czech character mappings
CZECH_CHAR_MAP = {
    'á': 'a', 'Á': 'A',
    'č': 'c', 'Č': 'C',
    'ď': 'd', 'Ď': 'D',
    'é': 'e', 'É': 'E',
    'ě': 'e', 'Ě': 'E',
    'í': 'i', 'Í': 'I',
    'ň': 'n', 'Ň': 'N',
    'ó': 'o', 'Ó': 'O',
    'ř': 'r', 'Ř': 'R',
    'š': 's', 'Š': 'S',
    'ť': 't', 'Ť': 'T',
    'ú': 'u', 'Ú': 'U',
    'ů': 'u', 'Ů': 'U',
    'ý': 'y', 'Ý': 'Y',
    'ž': 'z', 'Ž': 'Z'
}

# Reverse mapping for encoding
ASCII_TO_CZECH_MAP = {
    'a': 'á', 'A': 'Á',
    'c': 'č', 'C': 'Č',
    'd': 'ď', 'D': 'Ď',
    'e': 'é', 'E': 'É',
    'i': 'í', 'I': 'Í',
    'n': 'ň', 'N': 'Ň',
    'o': 'ó', 'O': 'Ó',
    'r': 'ř', 'R': 'Ř',
    's': 'š', 'S': 'Š',
    't': 'ť', 'T': 'Ť',
    'u': 'ú', 'U': 'Ú',
    'y': 'ý', 'Y': 'Ý',
    'z': 'ž', 'Z': 'Ž'
}


def remove_diacritics(text: str) -> str:
    """
    Remove all diacritics from Czech text.
    
    Args:
        text: Text with Czech diacritics
        
    Returns:
        Text without diacritics
    """
    result = []
    for char in text:
        if char in CZECH_CHAR_MAP:
            result.append(CZECH_CHAR_MAP[char])
        else:
            result.append(char)
    return ''.join(result)


def normalize_unicode(text: str) -> str:
    """
    Normalize Unicode text using NFD (Canonical Decomposition).
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    return unicodedata.normalize('NFD', text)


def normalize_to_ascii(text: str) -> str:
    """
    Normalize text to ASCII, removing all diacritics.
    
    Args:
        text: Text to normalize
        
    Returns:
        ASCII-only text
    """
    # First normalize to NFD
    nfd_text = unicodedata.normalize('NFD', text)
    # Then remove combining characters
    ascii_text = ''.join(char for char in nfd_text if unicodedata.category(char) != 'Mn')
    return ascii_text


def preserve_czech_encoding(text: str) -> str:
    """
    Ensure Czech characters are properly encoded.
    
    Args:
        text: Text to encode
        
    Returns:
        Properly encoded text
    """
    return unicodedata.normalize('NFC', text)


def is_czech_text(text: str) -> bool:
    """
    Check if text contains Czech diacritics.
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains Czech characters
    """
    return any(char in CZECH_CHAR_MAP for char in text)


def safe_decode(text: str, encoding: str = 'utf-8') -> str:
    """
    Safely decode text with fallback.
    
    Args:
        text: Text to decode
        encoding: Encoding to use
        
    Returns:
        Decoded text
    """
    if isinstance(text, str):
        return text
    
    try:
        return text.decode(encoding)
    except (UnicodeDecodeError, AttributeError):
        # Try latin-2 (common for Czech)
        try:
            return text.decode('latin-2')
        except (UnicodeDecodeError, AttributeError):
            # Last resort: ignore errors
            return text.decode(encoding, errors='ignore')


class CzechNormalizer:
    """
    Service for normalizing Czech text.
    Provides various normalization strategies.
    """
    
    def __init__(self):
        self.char_map = CZECH_CHAR_MAP
    
    def normalize(self, text: str, strategy: str = "preserve") -> str:
        """
        Normalize text using specified strategy.
        
        Args:
            text: Text to normalize
            strategy: Normalization strategy
                - "preserve": Keep Czech diacritics (default)
                - "remove": Remove all diacritics
                - "ascii": Convert to pure ASCII
                
        Returns:
            Normalized text
        """
        if strategy == "preserve":
            return preserve_czech_encoding(text)
        elif strategy == "remove":
            return remove_diacritics(text)
        elif strategy == "ascii":
            return normalize_to_ascii(text)
        else:
            return text
    
    def detect_encoding_issues(self, text: str) -> bool:
        """
        Detect if text has encoding issues.
        
        Args:
            text: Text to check
            
        Returns:
            True if encoding issues detected
        """
        # Look for common encoding issue patterns
        issues = ['Ã', '¡', '¬', '®', '©']
        return any(issue in text for issue in issues)


# Global normalizer instance
czech_normalizer = CzechNormalizer()
