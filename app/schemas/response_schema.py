"""
Generic response schemas.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None


class AgentExecuteRequest(BaseModel):
    """Request schema for executing an agent."""
    agent_name: str = Field(..., description="Name of the agent to execute")
    input_data: Dict[str, Any] = Field(..., description="Input data for the agent")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional context")


class AgentExecuteResponse(BaseModel):
    """Response schema for agent execution."""
    success: bool
    agent_name: str
    data: Dict[str, Any]
    reasoning_chain: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class WorkflowExecuteRequest(BaseModel):
    """Request schema for executing a workflow."""
    workflow: List[Dict[str, Any]] = Field(..., description="List of workflow steps")
    initial_data: Dict[str, Any] = Field(..., description="Initial input data")


class WorkflowExecuteResponse(BaseModel):
    """Response schema for workflow execution."""
    success: bool
    results: List[AgentExecuteResponse]
    total_steps: int
    completed_steps: int
