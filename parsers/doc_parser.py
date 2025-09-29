"""
DEPRECATED: This parser is deprecated. Use services/doc_parser.py instead.
Legacy parser for backward compatibility only.
"""

import logging
import warnings

warnings.warn("parsers.doc_parser is deprecated. Use services.doc_parser instead.", DeprecationWarning, stacklevel=2)
logger = logging.getLogger(__name__)

# Re-export from new location for backward compatibility
try:
    from services.doc_parser import *
    logger.info("✅ Redirecting to services.doc_parser")
except ImportError:
    logger.error("❌ Failed to import from services.doc_parser")
    import pdfplumber
    
    class DocParser:
        def __init__(self):
            self.czech_encodings = ['utf-8', 'cp1250', 'iso-8859-2']
            
        def parse(self, file_path: str) -> str:
            try:
                if file_path.endswith('.pdf'):
                    with pdfplumber.open(file_path) as pdf:
                        return '\n'.join([page.extract_text() or '' for page in pdf.pages])
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
            except Exception:
                return ""
