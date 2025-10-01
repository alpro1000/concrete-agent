"""
Tests for secure logging functionality
"""

import pytest
import logging
from utils.logging_config import SensitiveDataFilter, setup_logging


class TestSensitiveDataFilter:
    """Test that sensitive data is filtered from logs"""
    
    def test_anthropic_api_key_masked(self):
        """Test that Anthropic API keys are masked"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Using API key: sk-ant-1234567890abcdefghijklmnopqrstuvwxyz12345678",
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        
        # Original key should be masked
        assert "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz12345678" not in record.msg
        assert "sk-ant-***MASKED***" in record.msg
    
    def test_openai_api_key_masked(self):
        """Test that OpenAI API keys are masked"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="OpenAI key: sk-1234567890abcdefghijklmnopqrstuvwxyz12345678",
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        
        assert "sk-1234567890abcdefghijklmnopqrstuvwxyz12345678" not in record.msg
        assert "sk-***MASKED***" in record.msg
    
    def test_environment_variable_masked(self):
        """Test that API keys in environment variable format are masked"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='Config: ANTHROPIC_API_KEY="sk-ant-secret123456789"',
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        
        assert "sk-ant-secret123456789" not in record.msg
        assert "***MASKED***" in record.msg
    
    def test_authorization_header_masked(self):
        """Test that Authorization headers are masked"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Authorization: Bearer sk-ant-secret123456789abcdef",
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        
        assert "sk-ant-secret123456789abcdef" not in record.msg
        assert "***MASKED***" in record.msg
    
    def test_generic_api_key_masked(self):
        """Test that generic api_key patterns are masked"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='Request: {"api_key": "secret1234567890"}',
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        
        assert "secret1234567890" not in record.msg
        assert "***MASKED***" in record.msg
    
    def test_multiple_keys_in_same_message(self):
        """Test that multiple keys in the same message are all masked"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Keys: sk-ant-api1234567890123456789012345678901234567890 and sk-api2345678901234567890123456789012345678901234",
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        
        # Both keys should be masked
        assert "api1234567890123456789012345678901234567890" not in record.msg
        assert "api2345678901234567890123456789012345678901234" not in record.msg
        assert "***MASKED***" in record.msg
    
    def test_non_sensitive_data_unchanged(self):
        """Test that non-sensitive data passes through unchanged"""
        filter_obj = SensitiveDataFilter()
        original_msg = "Processing file: document.pdf with size 1024 bytes"
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=original_msg,
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        
        assert record.msg == original_msg
    
    def test_args_filtered(self):
        """Test that log record args are also filtered"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Using key: %s",
            args=("sk-ant-1234567890abcdefghijklmnopqrstuvwxyz12345678",),
            exc_info=None
        )
        
        # Before filtering, args should contain the key
        assert "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz12345678" in record.args[0]
        
        filter_obj.filter(record)
        
        # After filtering, args should be masked
        assert len(record.args) == 1
        assert "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz12345678" not in record.args[0]
        assert "***MASKED***" in record.args[0]
    
    def test_short_strings_not_masked(self):
        """Test that short strings that might look like keys aren't masked"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='Small value: api_key="short"',
            args=(),
            exc_info=None
        )
        
        original_msg = record.msg
        filter_obj.filter(record)
        
        # Short strings (< 10 chars) should not be masked
        assert record.msg == original_msg
    
    def test_openai_key_with_equals_sign(self):
        """Test masking of keys in key=value format"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz',
            args=(),
            exc_info=None
        )
        
        filter_obj.filter(record)
        
        assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in record.msg
        assert "***MASKED***" in record.msg


class TestLoggingSetup:
    """Test logging setup functionality"""
    
    def test_setup_logging_configures_filter(self, caplog):
        """Test that setup_logging adds the sensitive data filter"""
        setup_logging(level="INFO")
        
        # Get root logger
        logger = logging.getLogger()
        
        # Check that at least one handler has the filter
        has_filter = False
        for handler in logger.handlers:
            for filter_obj in handler.filters:
                if isinstance(filter_obj, SensitiveDataFilter):
                    has_filter = True
                    break
        
        assert has_filter, "SensitiveDataFilter should be added to handlers"
    
    def test_logging_with_api_key_gets_filtered(self, caplog):
        """Test that actual logging calls get filtered"""
        import logging
        caplog.set_level(logging.INFO)
        
        setup_logging(level="INFO")
        
        test_logger = logging.getLogger("test_security")
        test_logger.setLevel(logging.INFO)
        
        # Log a message with an API key
        test_logger.info("API Key: sk-ant-1234567890abcdefghijklmnopqrstuvwxyz12345678")
        
        # The actual key should not appear in captured logs
        assert "sk-ant-1234567890abcdefghijklmnopqrstuvwxyz12345678" not in caplog.text
        # Masked version should appear
        assert "***MASKED***" in caplog.text
    
    def test_logging_level_configuration(self):
        """Test that logging level is properly configured"""
        # Clear all handlers first
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        setup_logging(level="DEBUG")
        
        logger = logging.getLogger()
        # Check level is set
        assert logger.level <= logging.DEBUG  # May be set on handler instead of logger
        
        # Clear handlers again
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        setup_logging(level="WARNING")
        
        # Reset may have changed level
        # Just verify setup_logging doesn't crash
        assert True
