"""
Project Models - ИСПРАВЛЕНО
Added project_id to ProjectResponse
"""
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class WorkflowType(str, Enum):
    """Project workflow type"""
    A = "A"  # Audit existing vykaz vymer
    B = "B"  # Generate from drawings


class ProjectStatus(str, Enum):
    """Project processing status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PositionClassification(str, Enum):
    """Position audit classification"""
    GREEN = "GREEN"    # All good
    AMBER = "AMBER"    # Needs attention
    RED = "RED"        # Critical issues


class FileMetadata(BaseModel):
    """Metadata for uploaded file"""
    filename: str
    size: int
    uploaded_at: str
    file_type: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "vykaz.xml",
                "size": 524288,
                "uploaded_at": "2025-10-11T12:00:00",
                "file_type": "xml"
            }
        }


class ProjectResponse(BaseModel):
    """Response for project upload - ИСПРАВЛЕНО"""
    success: bool
    project_id: str  # ✅ ДОБАВЛЕНО - главное исправление!
    project_name: str
    workflow: str
    uploaded_at: str
    files_uploaded: Dict[str, Any]
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "project_id": "proj_21db12226dcf",  # ✅ ТЕПЕРЬ ЕСТЬ!
                "project_name": "RD Valcha",
                "workflow": "A",
                "uploaded_at": "2025-10-11T17:54:03",
                "files_uploaded": {
                    "vykaz_vymer": True,
                    "vykresy": 1,
                    "rozpocet": False,
                    "dokumentace": 0,
                    "zmeny": 0
                },
                "message": "Project uploaded successfully. ID: proj_21db12226dcf"
            }
        }


class ProjectStatusResponse(BaseModel):
    """Response for project status query"""
    project_id: str
    project_name: str
    status: ProjectStatus
    workflow: WorkflowType
    created_at: str
    updated_at: str
    progress: Optional[int] = 0
    positions_total: Optional[int] = 0
    positions_processed: Optional[int] = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj_21db12226dcf",
                "project_name": "RD Valcha",
                "status": "PROCESSING",
                "workflow": "A",
                "created_at": "2025-10-11T17:54:03",
                "updated_at": "2025-10-11T17:54:15",
                "progress": 65,
                "positions_total": 298,
                "positions_processed": 195
            }
        }


class PositionAudit(BaseModel):
    """Audit result for a single position"""
    position_number: str
    code: str
    description: str
    quantity: float
    unit: str
    classification: PositionClassification
    issues: list[str] = []
    recommendations: list[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "position_number": "1.1.1",
                "code": "121-01-001",
                "description": "Beton základů C20/25",
                "quantity": 25.5,
                "unit": "m³",
                "classification": "GREEN",
                "issues": [],
                "recommendations": []
            }
        }


class AuditResult(BaseModel):
    """Complete audit result"""
    project_id: str
    summary: Dict[str, Any]
    positions: list[PositionAudit]
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj_21db12226dcf",
                "summary": {
                    "total_positions": 298,
                    "green": 285,
                    "amber": 10,
                    "red": 3
                },
                "positions": []
            }
        }
