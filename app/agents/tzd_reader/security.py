"""
Enhanced Security validators for TZD Reader
"""

import os
import logging
import mimetypes
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Security constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain'
}


class SecurityError(Exception):
    """Exception for security issues"""
    pass


class FileSecurityValidator:
    """Enhanced file security validator"""
    
    @staticmethod
    def validate_file_path(file_path: str, base_dir: Optional[str] = None) -> bool:
        """
        Validates file path security with enhanced checks
        
        Args:
            file_path: Path to file
            base_dir: Base directory (optional)
            
        Returns:
            True if path is safe
            
        Raises:
            SecurityError: When unsafe path is detected
        """
        try:
            # Resolve to absolute path, following symlinks
            abs_path = Path(file_path).resolve()
            
            # Check if file exists
            if not abs_path.exists():
                raise SecurityError(f"File does not exist: {file_path}")
            
            # Check if it's actually a file (not directory or special file)
            if not abs_path.is_file():
                raise SecurityError(f"Not a regular file: {file_path}")
            
            # Prevent symlink attacks - check if any part of path is a symlink
            if abs_path.is_symlink() or any(p.is_symlink() for p in abs_path.parents):
                raise SecurityError(f"Symbolic links not allowed: {file_path}")
            
            if base_dir:
                base_abs = Path(base_dir).resolve()
                
                # Ensure file is within base_dir using resolved paths
                try:
                    abs_path.relative_to(base_abs)
                except ValueError:
                    raise SecurityError(
                        f"File outside allowed directory: {file_path}\n"
                        f"Allowed: {base_dir}"
                    )
            
            return True
            
        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"Path validation error {file_path}: {e}")
            raise SecurityError(f"Invalid file path {file_path}: {str(e)}")
    
    @staticmethod
    def validate_file_size(file_path: str, max_size: int = MAX_FILE_SIZE) -> bool:
        """
        Validates file size
        
        Args:
            file_path: Path to file
            max_size: Maximum allowed size in bytes
            
        Returns:
            True if size is acceptable
            
        Raises:
            SecurityError: When size limit exceeded or file inaccessible
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise SecurityError(f"File does not exist: {file_path}")
            
            file_size = path.stat().st_size
            
            if file_size == 0:
                raise SecurityError(f"Empty file: {file_path}")
            
            if file_size > max_size:
                raise SecurityError(
                    f"File too large: {file_size:,} bytes "
                    f"(max: {max_size:,} bytes, {max_size / 1024 / 1024:.1f}MB)"
                )
            
            return True
            
        except SecurityError:
            raise
        except OSError as e:
            raise SecurityError(f"Cannot access file {file_path}: {e}")
    
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
        
        if not ext:
            raise SecurityError(f"File has no extension: {file_path}")
        
        if ext not in ALLOWED_EXTENSIONS:
            raise SecurityError(
                f"Disallowed file extension: {ext}\n"
                f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        
        return True
    
    @staticmethod
    def validate_mime_type(file_path: str) -> bool:
        """
        Validates file MIME type (defense in depth)
        
        Args:
            file_path: Path to file
            
        Returns:
            True if MIME type is allowed
            
        Raises:
            SecurityError: When MIME type is not allowed
        """
        try:
            # First check with mimetypes library
            mime_type, _ = mimetypes.guess_type(file_path)
            
            if mime_type and mime_type in ALLOWED_MIME_TYPES:
                return True
            
            # For more robust detection, read file signature (magic bytes)
            with open(file_path, 'rb') as f:
                header = f.read(8)
            
            # PDF signature: %PDF
            if header.startswith(b'%PDF'):
                return True
            
            # DOCX signature: PK (ZIP format)
            if header.startswith(b'PK\x03\x04'):
                # Additional check for DOCX structure
                path = Path(file_path)
                if path.suffix.lower() == '.docx':
                    return True
            
            # Plain text - allow if extension is .txt
            if Path(file_path).suffix.lower() == '.txt':
                # Check if file is valid UTF-8 text
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read(1024)  # Read first KB
                    return True
                except UnicodeDecodeError:
                    raise SecurityError(f"File is not valid UTF-8 text: {file_path}")
            
            raise SecurityError(
                f"File MIME type not allowed or could not be determined: {file_path}\n"
                f"Detected: {mime_type}"
            )
            
        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"MIME type validation error {file_path}: {e}")
            raise SecurityError(f"Cannot validate MIME type for {file_path}: {e}")
    
    @classmethod
    def validate_all(
        cls, 
        file_path: str, 
        base_dir: Optional[str] = None,
        check_mime: bool = True
    ) -> bool:
        """
        Run all validations in sequence
        
        Args:
            file_path: Path to file
            base_dir: Base directory for path validation
            check_mime: Whether to perform MIME type validation
            
        Returns:
            True if all validations pass
            
        Raises:
            SecurityError: When any validation fails
        """
        cls.validate_file_extension(file_path)
        cls.validate_file_path(file_path, base_dir)
        cls.validate_file_size(file_path)
        
        if check_mime:
            cls.validate_mime_type(file_path)
        
        logger.info(f"File validated successfully: {Path(file_path).name}")
        return True


# Convenience function
def validate_file(
    file_path: str, 
    base_dir: Optional[str] = None,
    check_mime: bool = True
) -> bool:
    """
    Validate file with all security checks
    
    Args:
        file_path: Path to file
        base_dir: Base directory restriction
        check_mime: Perform MIME type validation
        
    Returns:
        True if file passes all checks
        
    Raises:
        SecurityError: If validation fails
    """
    validator = FileSecurityValidator()
    return validator.validate_all(file_path, base_dir, check_mime)