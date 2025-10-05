"""
Pydantic schemas for analysis operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class AnalysisBase(BaseModel):
    """Base analysis schema."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    analysis_type: str = Field(..., description="Type of analysis (tzd, boq, drawing, etc.)")


class AnalysisCreate(AnalysisBase):
    """Schema for creating a new analysis."""
    input_data: Dict[str, Any] = Field(default_factory=dict)


class AnalysisUpdate(BaseModel):
    """Schema for updating analysis."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None


class AnalysisResponse(AnalysisBase):
    """Schema for analysis response."""
    id: int
    status: str
    agent_name: Optional[str] = None
    agent_version: Optional[str] = None
    execution_time: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AnalysisWithData(AnalysisResponse):
    """Schema for analysis with full data."""
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    reasoning_chain: Optional[List[Dict[str, Any]]] = None
