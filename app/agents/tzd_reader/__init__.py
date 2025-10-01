"""
TZD Reader Agent Package
Production-ready wrapper with validation and error handling
"""

from typing import List, Dict, Any, Optional, Literal
import logging
import warnings
from pathlib import Path

from .agent import tzd_reader
from .security import SecurityError

logger = logging.getLogger(__name__)

# Type alias for supported engines
EngineType = Literal["gpt", "claude", "auto"]

# Supported engines constant
SUPPORTED_ENGINES = {"gpt", "claude", "auto"}


class TZDReaderError(Exception):
    """Base exception for TZDReader errors"""
    pass


class InvalidEngineError(TZDReaderError):
    """Raised when unsupported AI engine is specified"""
    pass


class InvalidInputError(TZDReaderError):
    """Raised when input validation fails"""
    pass


class TZDReader:
    """
    TZDReader class wrapper for backward compatibility
    
    Provides a class-based interface around the tzd_reader function
    with input validation, error handling, and logging.
    
    Example:
        >>> reader = TZDReader(engine="claude")
        >>> result = reader.analyze(["document.pdf"])
    """
    
    def __init__(self, engine: EngineType = "gpt"):
        """
        Initialize TZDReader
        
        Args:
            engine: AI engine to use ("gpt", "claude", or "auto")
            
        Raises:
            InvalidEngineError: If engine is not supported
        """
        self._validate_engine(engine)
        self.engine = engine
        logger.info(f"TZDReader initialized with engine: {engine}")
    
    @staticmethod
    def _validate_engine(engine: str) -> None:
        """
        Validate AI engine parameter
        
        Args:
            engine: Engine name to validate
            
        Raises:
            InvalidEngineError: If engine is not supported
        """
        if not isinstance(engine, str):
            raise InvalidEngineError(
                f"Engine must be a string, got {type(engine).__name__}"
            )
        
        if engine.lower() not in SUPPORTED_ENGINES:
            raise InvalidEngineError(
                f"Unsupported engine: '{engine}'. "
                f"Supported engines: {', '.join(sorted(SUPPORTED_ENGINES))}"
            )
    
    @staticmethod
    def _validate_files(files: List[str]) -> None:
        """
        Validate files parameter
        
        Args:
            files: List of file paths to validate
            
        Raises:
            InvalidInputError: If files parameter is invalid
        """
        if not files:
            raise InvalidInputError("Files list cannot be empty")
        
        if not isinstance(files, list):
            raise InvalidInputError(
                f"Files must be a list, got {type(files).__name__}"
            )
        
        if not all(isinstance(f, str) for f in files):
            raise InvalidInputError("All file paths must be strings")
        
        # Check for obviously invalid paths
        for file_path in files:
            if not file_path.strip():
                raise InvalidInputError("File path cannot be empty string")
    
    def analyze(
        self, 
        files: List[str], 
        base_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze technical assignment documents
        
        Args:
            files: List of file paths to analyze
            base_dir: Base directory for file access restriction
            
        Returns:
            Analysis results dictionary containing:
                - project_object: Project description
                - requirements: List of requirements
                - norms: List of standards/norms
                - constraints: List of constraints
                - environment: Environmental conditions
                - functions: Project functions
                - processing_metadata: Processing statistics
            
        Raises:
            InvalidInputError: If input validation fails
            SecurityError: If security validation fails
            TZDReaderError: If analysis fails
            
        Example:
            >>> reader = TZDReader(engine="claude")
            >>> result = reader.analyze(
            ...     files=["specs.pdf", "requirements.docx"],
            ...     base_dir="/safe/uploads"
            ... )
        """
        # Validate inputs
        self._validate_files(files)
        
        logger.info(
            f"Starting TZD analysis: {len(files)} file(s) with engine '{self.engine}'"
        )
        
        try:
            result = tzd_reader(
                files=files, 
                engine=self.engine, 
                base_dir=base_dir
            )
            
            # Log success
            metadata = result.get('processing_metadata', {})
            logger.info(
                f"TZD analysis completed successfully: "
                f"{metadata.get('processed_files', 0)} files processed, "
                f"{metadata.get('processing_time_seconds', 0):.2f}s"
            )
            
            return result
            
        except SecurityError as e:
            logger.error(f"Security validation failed: {e}")
            raise
        
        except ValueError as e:
            logger.error(f"Invalid input for TZD analysis: {e}")
            raise InvalidInputError(str(e)) from e
        
        except Exception as e:
            logger.error(f"TZD analysis failed: {e}", exc_info=True)
            raise TZDReaderError(f"Analysis failed: {str(e)}") from e
    
    def analyze_files(
        self, 
        files: List[str], 
        base_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze technical assignment documents (deprecated alias)
        
        .. deprecated:: 1.0.0
            Use :meth:`analyze` instead. This method will be removed in version 2.0.0
        
        Args:
            files: List of file paths to analyze
            base_dir: Base directory for file access restriction
            
        Returns:
            Analysis results dictionary
        """
        warnings.warn(
            "analyze_files() is deprecated, use analyze() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.analyze(files=files, base_dir=base_dir)
    
    def set_engine(self, engine: EngineType) -> None:
        """
        Change the AI engine
        
        Args:
            engine: New engine to use
            
        Raises:
            InvalidEngineError: If engine is not supported
        """
        self._validate_engine(engine)
        old_engine = self.engine
        self.engine = engine
        logger.info(f"Engine changed from '{old_engine}' to '{engine}'")
    
    def __repr__(self) -> str:
        """String representation of TZDReader instance"""
        return f"TZDReader(engine='{self.engine}')"


# Re-export tzd_reader function for direct use
from .agent import tzd_reader as _tzd_reader

def tzd_reader_wrapper(
    files: List[str], 
    engine: EngineType = "gpt",
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function wrapper around TZDReader
    
    This is a thin wrapper that provides the same interface as the
    class-based approach but as a simple function call.
    
    Args:
        files: List of file paths to analyze
        engine: AI engine to use
        base_dir: Base directory for file access restriction
        
    Returns:
        Analysis results dictionary
    """
    reader = TZDReader(engine=engine)
    return reader.analyze(files=files, base_dir=base_dir)


# Export public API
__all__ = [
    'TZDReader',
    'tzd_reader_wrapper',
    'TZDReaderError',
    'InvalidEngineError', 
    'InvalidInputError',
    'SUPPORTED_ENGINES'
]