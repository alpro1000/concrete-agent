"""
Utility functions for the Concrete Agent system.
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from jose import jwt
from backend.app.core.config import settings


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def hash_string(text: str) -> str:
    """Generate SHA256 hash of a string."""
    return hashlib.sha256(text.encode()).hexdigest()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time delta
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT access token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded token data
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO 8601 string."""
    return dt.isoformat()


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO 8601 timestamp string."""
    return datetime.fromisoformat(timestamp_str)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
