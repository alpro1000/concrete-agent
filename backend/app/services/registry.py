"""
Dynamic agent registry for discovering and loading agents.
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, Type, Optional, List
from backend.app.core.logging_config import app_logger
from backend.app.core.exceptions import RegistryException


class AgentRegistry:
    """
    Registry for dynamically discovering and loading agents.
    Agents are discovered from the agents directory automatically.
    """
    
    def __init__(self):
        self._agents: Dict[str, Type] = {}
        self._agent_metadata: Dict[str, Dict] = {}
    
    def register(self, name: str, agent_class: Type, metadata: Optional[Dict] = None):
        """
        Register an agent class.
        
        Args:
            name: Agent name (unique identifier)
            agent_class: Agent class to register
            metadata: Optional metadata about the agent
        """
        if name in self._agents:
            app_logger.warning(f"Agent '{name}' already registered, overwriting")
        
        self._agents[name] = agent_class
        self._agent_metadata[name] = metadata or {}
        app_logger.info(f"Registered agent: {name}")
    
    def get(self, name: str) -> Type:
        """
        Get an agent class by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent class
        """
        if name not in self._agents:
            raise RegistryException(
                f"Agent '{name}' not found in registry",
                {"available_agents": list(self._agents.keys())}
            )
        
        return self._agents[name]
    
    def list_agents(self) -> List[str]:
        """Get list of all registered agent names."""
        return list(self._agents.keys())
    
    def get_metadata(self, name: str) -> Dict:
        """Get metadata for an agent."""
        return self._agent_metadata.get(name, {})
    
    def discover_agents(self, agents_path: Optional[Path] = None):
        """
        Automatically discover and register agents from the agents directory.
        
        Args:
            agents_path: Path to agents directory (default: app/agents)
        """
        if agents_path is None:
            agents_path = Path(__file__).parent.parent / "agents"
        
        if not agents_path.exists():
            app_logger.warning(f"Agents path does not exist: {agents_path}")
            return
        
        app_logger.info(f"Discovering agents in {agents_path}")
        
        # Iterate through agent directories
        for agent_dir in agents_path.iterdir():
            if not agent_dir.is_dir() or agent_dir.name.startswith("_"):
                continue
            
            agent_file = agent_dir / "agent.py"
            if not agent_file.exists():
                continue
            
            try:
                # Import the agent module using full package path
                module_path = f"backend.app.agents.{agent_dir.name}.agent"
                module = importlib.import_module(module_path)
                
                # Find agent classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it's an agent class (has execute method)
                    if hasattr(obj, "execute") and hasattr(obj, "name"):
                        agent_name = getattr(obj, "name", agent_dir.name)
                        self.register(agent_name, obj, {
                            "module": module_path,
                            "directory": str(agent_dir)
                        })
                        
            except Exception as e:
                app_logger.error(f"Failed to discover agent in {agent_dir}: {e}")
    
    def clear(self):
        """Clear all registered agents."""
        self._agents.clear()
        self._agent_metadata.clear()
        app_logger.info("Agent registry cleared")


# Global agent registry instance
agent_registry = AgentRegistry()
