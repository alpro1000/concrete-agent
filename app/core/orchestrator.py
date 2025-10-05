"""
Orchestrator for coordinating agent execution and workflow.
"""

from typing import Dict, Any, Optional, List
from app.core.logging_config import app_logger
from app.core.exceptions import AgentException, RegistryException
from app.services.registry import agent_registry
from app.agents.base_agent import BaseAgent, AgentResult


class Orchestrator:
    """
    Orchestrates agent execution and manages workflows.
    Handles agent selection, execution, and result aggregation.
    """
    
    def __init__(self):
        self.execution_history: List[Dict] = []
        app_logger.info("Orchestrator initialized")
    
    async def execute_agent(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        Execute a single agent by name.
        
        Args:
            agent_name: Name of the agent to execute
            input_data: Input data for the agent
            context: Optional context information
            
        Returns:
            AgentResult from agent execution
        """
        try:
            # Get agent class from registry
            agent_class = agent_registry.get(agent_name)
            
            # Instantiate agent
            agent: BaseAgent = agent_class()
            
            app_logger.info(f"Executing agent: {agent_name}")
            
            # Execute agent
            result = await agent.execute(input_data)
            
            # Store execution history
            self._record_execution(agent_name, input_data, result, context)
            
            return result
            
        except RegistryException as e:
            app_logger.error(f"Agent not found: {agent_name}")
            return AgentResult(
                success=False,
                data={},
                errors=[str(e)]
            )
        except Exception as e:
            app_logger.error(f"Agent execution failed: {e}")
            return AgentResult(
                success=False,
                data={},
                errors=[str(e)]
            )
    
    async def execute_workflow(
        self,
        workflow: List[Dict[str, Any]],
        initial_data: Dict[str, Any]
    ) -> List[AgentResult]:
        """
        Execute a workflow of multiple agents.
        
        Args:
            workflow: List of workflow steps, each with 'agent' and optional 'config'
            initial_data: Initial input data
            
        Returns:
            List of AgentResult objects from each step
        """
        results = []
        current_data = initial_data.copy()
        
        app_logger.info(f"Starting workflow with {len(workflow)} steps")
        
        for i, step in enumerate(workflow):
            agent_name = step.get("agent")
            step_config = step.get("config", {})
            
            if not agent_name:
                app_logger.error(f"Workflow step {i} missing agent name")
                continue
            
            # Merge step config with current data
            step_input = {**current_data, **step_config}
            
            # Execute agent
            result = await self.execute_agent(agent_name, step_input)
            results.append(result)
            
            # Pass successful results to next step
            if result.success:
                current_data.update(result.data)
                app_logger.info(f"Workflow step {i} ({agent_name}) completed successfully")
            else:
                app_logger.warning(f"Workflow step {i} ({agent_name}) failed: {result.errors}")
                # Optionally stop workflow on failure
                # break
        
        app_logger.info(f"Workflow completed with {len(results)} results")
        return results
    
    async def execute_parallel(
        self,
        agents: List[str],
        input_data: Dict[str, Any]
    ) -> Dict[str, AgentResult]:
        """
        Execute multiple agents in parallel with same input.
        
        Args:
            agents: List of agent names
            input_data: Input data for all agents
            
        Returns:
            Dict mapping agent names to their results
        """
        import asyncio
        
        app_logger.info(f"Executing {len(agents)} agents in parallel")
        
        # Create tasks for parallel execution
        tasks = {
            agent_name: self.execute_agent(agent_name, input_data)
            for agent_name in agents
        }
        
        # Execute all tasks
        results = {}
        for agent_name, task in tasks.items():
            try:
                results[agent_name] = await task
            except Exception as e:
                app_logger.error(f"Parallel execution failed for {agent_name}: {e}")
                results[agent_name] = AgentResult(
                    success=False,
                    data={},
                    errors=[str(e)]
                )
        
        return results
    
    def get_available_agents(self) -> List[str]:
        """Get list of all available agents."""
        return agent_registry.list_agents()
    
    def get_agent_metadata(self, agent_name: str) -> Dict:
        """Get metadata for a specific agent."""
        return agent_registry.get_metadata(agent_name)
    
    def get_execution_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get execution history.
        
        Args:
            limit: Optional limit on number of records to return
            
        Returns:
            List of execution history records
        """
        if limit:
            return self.execution_history[-limit:]
        return self.execution_history
    
    def clear_history(self):
        """Clear execution history."""
        self.execution_history.clear()
        app_logger.info("Execution history cleared")
    
    def _record_execution(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        result: AgentResult,
        context: Optional[Dict[str, Any]]
    ):
        """Record an agent execution in history."""
        record = {
            "agent": agent_name,
            "timestamp": result.timestamp,
            "success": result.success,
            "input_size": len(str(input_data)),
            "output_size": len(str(result.data)),
            "errors": result.errors,
            "context": context
        }
        
        self.execution_history.append(record)
        
        # Keep only last 1000 executions
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]


# Global orchestrator instance
orchestrator = Orchestrator()
