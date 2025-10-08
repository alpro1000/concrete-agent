"""
Project-related Pydantic models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AuditStatus(str, Enum):
    """Status of audit processing"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowType(str, Enum):
    """Type of workflow"""
    A = "A"  # With výkaz výměr
    B = "B"  # Without výkaz výměr


class ProjectCreate(BaseModel):
    """Request model for creating a new project"""
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")


class UploadedFile(BaseModel):
    """Information about uploaded file"""
    filename: str
    saved_as: str
    type: str
    size: int


class ProjectResponse(BaseModel):
    """Response model for project"""
    project_id: str
    name: str
    upload_timestamp: datetime
    status: AuditStatus
    workflow: WorkflowType
    files: List[Dict[str, Any]]
    message: str
