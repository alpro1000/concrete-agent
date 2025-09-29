"""
TZD Reader Agent Package
"""

from .agent import tzd_reader
from typing import List, Dict, Any, Optional


class TZDReader:
    """
    TZDReader class wrapper for backward compatibility
    Wraps the tzd_reader function in a class interface
    """
    
    def __init__(self, engine: str = "gpt"):
        """
        Initialize TZDReader
        
        Args:
            engine: AI engine to use ("gpt", "claude", or "auto")
        """
        self.engine = engine
    
    def analyze(self, files: List[str], base_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze technical assignment documents
        
        Args:
            files: List of file paths to analyze
            base_dir: Base directory for file access restriction
            
        Returns:
            Analysis results dictionary
        """
        return tzd_reader(files=files, engine=self.engine, base_dir=base_dir)
    
    def analyze_files(self, files: List[str], base_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Alias for analyze method for compatibility
        """
        return self.analyze(files=files, base_dir=base_dir)


# Export both the class and function for flexibility
__all__ = ['TZDReader', 'tzd_reader']