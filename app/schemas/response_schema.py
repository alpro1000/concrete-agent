"""
Generic response schemas.
"""

from pydantic import BaseModel, Field, ConfigDict
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
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "agent_name": "boq_parser",
                    "input_data": {
                        "document": "Sample BOQ document text content",
                        "options": {
                            "parse_detailed": True
                        }
                    },
                    "context": {
                        "user_id": "user123",
                        "project_name": "Construction Project A"
                    }
                },
                {
                    "agent_name": "tzd_reader",
                    "input_data": {
                        "document": "Technical specification document content"
                    }
                }
            ]
        }
    )
    
    agent_name: str = Field(..., description="Name of the agent to execute")
    input_data: Dict[str, Any] = Field(..., description="Input data for the agent")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional context")


class AgentExecuteResponse(BaseModel):
    """Response schema for agent execution."""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "agent_name": "boq_parser",
                    "data": {
                        "items": [
                            {
                                "item_number": "1.1",
                                "description": "Excavation",
                                "unit": "m3",
                                "quantity": 100.0,
                                "unit_price": 50.0,
                                "total_price": 5000.0
                            }
                        ],
                        "summary": {
                            "item_count": 1,
                            "total_cost": 5000.0
                        }
                    },
                    "reasoning_chain": [
                        {
                            "step": "hypothesis",
                            "content": "Parse BOQ document and extract line items",
                            "confidence": 0.5,
                            "timestamp": "2025-01-19T12:00:00"
                        },
                        {
                            "step": "reasoning",
                            "content": "Analyzing document structure",
                            "confidence": 0.7,
                            "timestamp": "2025-01-19T12:00:01"
                        }
                    ],
                    "errors": [],
                    "metadata": {
                        "agent": "boq_parser",
                        "version": "1.0.0"
                    },
                    "timestamp": "2025-01-19T12:00:05"
                }
            ]
        }
    )
    
    success: bool
    agent_name: str
    data: Dict[str, Any]
    reasoning_chain: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class WorkflowExecuteRequest(BaseModel):
    """Request schema for executing a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "workflow": [
                        {
                            "agent": "tzd_reader",
                            "input_mapping": {
                                "document": "$.initial_data.specification"
                            }
                        },
                        {
                            "agent": "boq_parser",
                            "input_mapping": {
                                "document": "$.initial_data.boq_document"
                            }
                        }
                    ],
                    "initial_data": {
                        "specification": "Technical specification content",
                        "boq_document": "BOQ document content"
                    }
                }
            ]
        }
    )
    
    workflow: List[Dict[str, Any]] = Field(..., description="List of workflow steps")
    initial_data: Dict[str, Any] = Field(..., description="Initial input data")


class WorkflowExecuteResponse(BaseModel):
    """Response schema for workflow execution."""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "results": [
                        {
                            "success": True,
                            "agent_name": "tzd_reader",
                            "data": {
                                "sections": ["Introduction", "Technical Requirements"]
                            },
                            "reasoning_chain": [],
                            "errors": [],
                            "metadata": {},
                            "timestamp": "2025-01-19T12:00:00"
                        },
                        {
                            "success": True,
                            "agent_name": "boq_parser",
                            "data": {
                                "items": [],
                                "summary": {"item_count": 0}
                            },
                            "reasoning_chain": [],
                            "errors": [],
                            "metadata": {},
                            "timestamp": "2025-01-19T12:00:05"
                        }
                    ],
                    "total_steps": 2,
                    "completed_steps": 2
                }
            ]
        }
    )
    
    success: bool
    results: List[AgentExecuteResponse]
    total_steps: int
    completed_steps: int
