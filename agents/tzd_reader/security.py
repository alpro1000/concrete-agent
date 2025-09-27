"""
Security validators for TZD Reader
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Security constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}


class SecurityError(Exception):
    """Exception for security issues"""
    pass


class FileSecurityValidator:
    """File security validator"""
    
    @staticmethod
    def validate_file_path(file_path: str, base_dir: Optional[str] = None) -> bool:
        """
        Validates file path security
        
        Args:
            file_path: Path to file
            base_dir: Base directory (optional)
            
        Returns:
            True if path is safe
            
        Raises:
            SecurityError: When unsafe path is detected
        """
        try:
            abs_path = os.path.abspath(file_path)
            
            if base_dir:
                base_abs = os.path.abspath(base_dir)
                
                # Check for path traversal: '..' in path parts
                if ".." in Path(file_path).parts:
                    raise SecurityError(f"Path traversal detected: {file_path}")
                
                # Path must be within base_dir
                if not (abs_path == base_abs or abs_path.startswith(base_abs + os.sep)):
                    raise SecurityError(f"File outside base_dir: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Path validation error {file_path}: {e}")
            raise SecurityError(f"Invalid file path {file_path}: {e}")
    
    @staticmethod
    def validate_file_size(file_path: str) -> bool:
        """
        Validates file size
        
        Args:
            file_path: Path to file
            
        Returns:
            True if size is acceptable
            
        Raises:
            SecurityError: When size limit exceeded
        """
        try:
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                raise SecurityError(
                    f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})"
                )
            return True
        except OSError as e:
            raise SecurityError(f"Cannot check file size {file_path}: {e}")
    
    @staticmethod
    def validate_file_extension(file_path: str) -> bool:
        """
        Validates file extension
        
        Args:
            file_path: Path to file
            
        Returns:
            True if extension is allowed
            
        Raises:
            SecurityError: When extension is not allowed
        """
        ext = Path(file_path).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise SecurityError(
                f"Disallowed file extension: {ext}. "
                f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        return True