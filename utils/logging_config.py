import logging
import re
from typing import Any


class SensitiveDataFilter(logging.Filter):
    """Filter to prevent sensitive data from being logged"""
    
    # Patterns to detect and mask sensitive data
    PATTERNS = [
        # Anthropic API keys (sk-ant- followed by 40+ chars)
        (re.compile(r'sk-ant-[a-zA-Z0-9_-]{40,}'), 'sk-ant-***MASKED***'),
        # OpenAI API keys (sk- followed by 40+ chars, not sk-ant-)
        (re.compile(r'(?<!ant-)sk-[a-zA-Z0-9]{40,}'), 'sk-***MASKED***'),
        # Environment variable assignments
        (re.compile(r'(ANTHROPIC_API_KEY["\']?\s*[:=]\s*["\']?)([^"\'\s]{10,})'), r'\1***MASKED***'),
        (re.compile(r'(OPENAI_API_KEY["\']?\s*[:=]\s*["\']?)([^"\'\s]{10,})'), r'\1***MASKED***'),
        (re.compile(r'(PERPLEXITY_API_KEY["\']?\s*[:=]\s*["\']?)([^"\'\s]{10,})'), r'\1***MASKED***'),
        # Generic api_key patterns
        (re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'\s]{10,})'), r'\1***MASKED***'),
        # Authorization headers
        (re.compile(r'(Authorization:\s*Bearer\s+)([^\s]+)'), r'\1***MASKED***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record to mask sensitive data"""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            original_msg = record.msg
            for pattern, replacement in self.PATTERNS:
                original_msg = pattern.sub(replacement, original_msg)
            record.msg = original_msg
        
        # Also filter args if present
        if hasattr(record, 'args') and record.args:
            filtered_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    filtered_arg = arg
                    for pattern, replacement in self.PATTERNS:
                        filtered_arg = pattern.sub(replacement, filtered_arg)
                    filtered_args.append(filtered_arg)
                else:
                    filtered_args.append(arg)
            record.args = tuple(filtered_args)
        
        return True


def setup_logging(level: str = "INFO"):
    """
    Setup logging configuration with security filters
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create filter instance
    sensitive_filter = SensitiveDataFilter()
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Add filter to all handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)
    
    # Create file handler with filter if logs directory exists
    try:
        import os
        os.makedirs("logs", exist_ok=True)
        
        file_handler = logging.FileHandler("logs/application.log")
        file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        logging.warning(f"Could not setup file logging: {e}")
    
    logging.info("Secure logging configured successfully")
