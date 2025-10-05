"""
Custom exceptions for the Concrete Agent system.
"""


class ConcreteAgentException(Exception):
    """Base exception for all Concrete Agent errors."""
    
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AgentException(ConcreteAgentException):
    """Exception raised by agents during execution."""
    pass


class LLMException(ConcreteAgentException):
    """Exception related to LLM service failures."""
    pass


class DatabaseException(ConcreteAgentException):
    """Exception related to database operations."""
    pass


class ValidationException(ConcreteAgentException):
    """Exception related to data validation."""
    pass


class ConfigurationException(ConcreteAgentException):
    """Exception related to configuration errors."""
    pass


class RegistryException(ConcreteAgentException):
    """Exception related to agent registry operations."""
    pass


class StorageException(ConcreteAgentException):
    """Exception related to file storage operations."""
    pass


class KnowledgeBaseException(ConcreteAgentException):
    """Exception related to knowledge base operations."""
    pass
