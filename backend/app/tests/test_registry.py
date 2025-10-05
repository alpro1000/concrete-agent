"""
Test for agent registry functionality.
"""

import pytest
from backend.app.services.registry import AgentRegistry
from backend.app.agents.base_agent import BaseAgent, AgentResult
from typing import Dict, Any


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    name = "mock_agent"
    description = "Test mock agent"
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        return AgentResult(
            success=True,
            data={"result": "mock"}
        )


def test_agent_registry_register():
    """Test agent registration."""
    registry = AgentRegistry()
    registry.register("test_agent", MockAgent, {"test": True})
    
    assert "test_agent" in registry.list_agents()
    assert registry.get("test_agent") == MockAgent
    assert registry.get_metadata("test_agent")["test"] is True


def test_agent_registry_get_nonexistent():
    """Test getting non-existent agent raises exception."""
    from backend.app.core.exceptions import RegistryException
    
    registry = AgentRegistry()
    
    with pytest.raises(RegistryException):
        registry.get("nonexistent_agent")


def test_agent_registry_clear():
    """Test clearing registry."""
    registry = AgentRegistry()
    registry.register("test_agent", MockAgent)
    
    assert len(registry.list_agents()) > 0
    
    registry.clear()
    
    assert len(registry.list_agents()) == 0


def test_agent_registry_list_agents():
    """Test listing agents."""
    registry = AgentRegistry()
    registry.register("agent1", MockAgent)
    registry.register("agent2", MockAgent)
    
    agents = registry.list_agents()
    
    assert "agent1" in agents
    assert "agent2" in agents
    assert len(agents) == 2
