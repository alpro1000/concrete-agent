"""
Unified router for agent orchestration and execution.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from app.core.orchestrator import orchestrator
from app.services.registry import agent_registry
from app.schemas.response_schema import (
    AgentExecuteRequest,
    AgentExecuteResponse,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    SuccessResponse
)
from app.core.logging_config import app_logger

router = APIRouter()


@router.post("/execute", response_model=AgentExecuteResponse)
async def execute_agent(request: AgentExecuteRequest):
    """
    Execute a single agent.
    
    Args:
        request: Agent execution request with agent name and input data
        
    Returns:
        Agent execution result with reasoning chain
    """
    try:
        app_logger.info(f"Executing agent: {request.agent_name}")
        
        # Execute agent
        result = await orchestrator.execute_agent(
            agent_name=request.agent_name,
            input_data=request.input_data,
            context=request.context
        )
        
        # Convert to response format
        return AgentExecuteResponse(
            success=result.success,
            agent_name=request.agent_name,
            data=result.data,
            reasoning_chain=[step.dict() for step in result.reasoning_chain],
            errors=result.errors,
            metadata=result.metadata,
            timestamp=result.timestamp.isoformat()
        )
        
    except Exception as e:
        app_logger.error(f"Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow", response_model=WorkflowExecuteResponse)
async def execute_workflow(request: WorkflowExecuteRequest):
    """
    Execute a workflow of multiple agents.
    
    Args:
        request: Workflow execution request with steps and initial data
        
    Returns:
        Results from all workflow steps
    """
    try:
        app_logger.info(f"Executing workflow with {len(request.workflow)} steps")
        
        # Execute workflow
        results = await orchestrator.execute_workflow(
            workflow=request.workflow,
            initial_data=request.initial_data
        )
        
        # Convert to response format
        agent_responses = []
        for result in results:
            agent_responses.append(AgentExecuteResponse(
                success=result.success,
                agent_name=result.metadata.get("agent", "unknown"),
                data=result.data,
                reasoning_chain=[step.dict() for step in result.reasoning_chain],
                errors=result.errors,
                metadata=result.metadata,
                timestamp=result.timestamp.isoformat()
            ))
        
        return WorkflowExecuteResponse(
            success=all(r.success for r in results),
            results=agent_responses,
            total_steps=len(request.workflow),
            completed_steps=sum(1 for r in results if r.success)
        )
        
    except Exception as e:
        app_logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=List[str])
async def list_agents():
    """
    Get list of all available agents.
    
    Returns:
        List of agent names
    """
    try:
        agents = orchestrator.get_available_agents()
        return agents
    except Exception as e:
        app_logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_name}/metadata")
async def get_agent_metadata(agent_name: str):
    """
    Get metadata for a specific agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Agent metadata
    """
    try:
        metadata = orchestrator.get_agent_metadata(agent_name)
        
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Failed to get agent metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_execution_history(limit: int = 100):
    """
    Get execution history.
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of execution history records
    """
    try:
        history = orchestrator.get_execution_history(limit=limit)
        return history
    except Exception as e:
        app_logger.error(f"Failed to get execution history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/clear", response_model=SuccessResponse)
async def clear_execution_history():
    """
    Clear execution history.
    
    Returns:
        Success message
    """
    try:
        orchestrator.clear_history()
        return SuccessResponse(
            success=True,
            message="Execution history cleared successfully"
        )
    except Exception as e:
        app_logger.error(f"Failed to clear execution history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
