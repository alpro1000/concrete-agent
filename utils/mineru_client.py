"""
MinerU Client utilities - stub implementation
"""

from typing import List, Optional

def extract_with_mineru_if_available(pdf_files: List[str]) -> Optional[str]:
    """
    Extract text from PDF files using MinerU if available.
    
    Args:
        pdf_files: List of PDF file paths
        
    Returns:
        Extracted text or None if MinerU is not available
    """
    # MinerU is optional - return None to use fallback parser
    return None
