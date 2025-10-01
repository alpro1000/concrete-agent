"""
BaseAgent - Base class for all agents in the beads system
All agents must inherit from this class and implement the required interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    
    All agents must inherit from this class and implement:
    - name: str - unique identifier for the agent
    - supported_types: list[str] - list of file types or document types the agent can handle
    - analyze(file_path: str) -> dict - analysis method
    
    Example:
        class MyAgent(BaseAgent):
            name = "my_agent"
            supported_types = ["pdf", "docx", "technical_assignment"]
            
            async def analyze(self, file_path: str) -> dict:
                # Your analysis logic
                return {"result": "analysis"}
    """
    
    # Agent identifier - must be overridden by subclass
    name: str = "base"
    
    # List of supported file types or document types - must be overridden by subclass
    supported_types: List[str] = []
    
    @abstractmethod
    async def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a file and return structured results.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dictionary with analysis results. Structure depends on the agent.
            
        Raises:
            Exception: If analysis fails
        """
        pass
    
    def supports_type(self, file_type: str) -> bool:
        """
        Check if this agent supports a given file type.
        
        Args:
            file_type: Type to check (e.g., "pdf", "technical_assignment")
            
        Returns:
            True if the agent supports this type
        """
        return file_type.lower() in [t.lower() for t in self.supported_types]
    
    def __repr__(self) -> str:
        """String representation of the agent"""
        return f"{self.__class__.__name__}(name='{self.name}', supported_types={self.supported_types})"
