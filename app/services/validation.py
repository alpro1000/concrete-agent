"""
Validation service for data validation and sanitization.
"""

import re
from typing import Any, Dict, List, Optional
from app.core.logging_config import app_logger
from app.core.exceptions import ValidationException


class ValidationService:
    """Service for validating and sanitizing data."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """
        Validate username format.
        
        Args:
            username: Username to validate
            
        Returns:
            True if valid
        """
        # Username must be 3-50 characters, alphanumeric and underscores only
        pattern = r'^[a-zA-Z0-9_]{3,50}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        Check password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Dict with validation results
        """
        result = {
            "valid": True,
            "score": 0,
            "feedback": []
        }
        
        if len(password) < 8:
            result["valid"] = False
            result["feedback"].append("Password must be at least 8 characters")
        else:
            result["score"] += 1
        
        if len(password) >= 12:
            result["score"] += 1
        
        if re.search(r'[a-z]', password):
            result["score"] += 1
        else:
            result["feedback"].append("Password should contain lowercase letters")
        
        if re.search(r'[A-Z]', password):
            result["score"] += 1
        else:
            result["feedback"].append("Password should contain uppercase letters")
        
        if re.search(r'\d', password):
            result["score"] += 1
        else:
            result["feedback"].append("Password should contain numbers")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            result["score"] += 1
        else:
            result["feedback"].append("Password should contain special characters")
        
        return result
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Remove HTML tags from text.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        clean = re.sub(r'<[^>]+>', '', text)
        return clean
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
        """
        Validate file extension.
        
        Args:
            filename: Filename to validate
            allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.txt'])
            
        Returns:
            True if valid
        """
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        return f".{extension}" in [ext.lower() for ext in allowed_extensions]
    
    @staticmethod
    def validate_json_structure(data: Dict, required_fields: List[str]) -> bool:
        """
        Validate that JSON data contains required fields.
        
        Args:
            data: JSON data to validate
            required_fields: List of required field names
            
        Returns:
            True if valid
            
        Raises:
            ValidationException if validation fails
        """
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise ValidationException(
                f"Missing required fields: {', '.join(missing_fields)}",
                {"required": required_fields, "missing": missing_fields}
            )
        
        return True
    
    @staticmethod
    def validate_agent_name(agent_name: str) -> bool:
        """
        Validate agent name format.
        
        Args:
            agent_name: Agent name to validate
            
        Returns:
            True if valid
        """
        # Agent name: lowercase, alphanumeric and underscores
        pattern = r'^[a-z0-9_]+$'
        return bool(re.match(pattern, agent_name))
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename by removing potentially dangerous characters.
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
        """
        # Remove path separators and other dangerous characters
        sanitized = re.sub(r'[^\w\s.-]', '', filename)
        # Remove leading dots and spaces
        sanitized = sanitized.lstrip('. ')
        return sanitized
    
    @staticmethod
    def validate_numeric_range(
        value: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> bool:
        """
        Validate that a numeric value is within a range.
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            True if valid
            
        Raises:
            ValidationException if validation fails
        """
        if min_value is not None and value < min_value:
            raise ValidationException(
                f"Value {value} is less than minimum {min_value}",
                {"value": value, "min": min_value}
            )
        
        if max_value is not None and value > max_value:
            raise ValidationException(
                f"Value {value} is greater than maximum {max_value}",
                {"value": value, "max": max_value}
            )
        
        return True


# Global validation service instance
validation_service = ValidationService()
