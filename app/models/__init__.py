"""
Models package initialization
Exports all models for easy import throughout the application
"""
from app.models.project import (
    # SQLAlchemy models
    Project,
    Base,
    
    # Enums
    ProjectStatus,
    AuditClassification,
    WorkflowType,
    
    # Pydantic API models
    ProjectCreate,
    ProjectResponse,
    ProjectStatusResponse,
    UploadedFile,
    FileMetadata,
    Position,
    PositionAudit,
    AuditReport,
    ErrorResponse,
    SuccessResponse,
    
    # Helper functions
    db_project_to_response,
    calculate_audit_summary,
)

__all__ = [
    # === SQLAlchemy ===
    "Project",
    "Base",
    
    # === Enums ===
    "ProjectStatus",
    "AuditClassification",
    "WorkflowType",
    
    # === Pydantic Models ===
    "ProjectCreate",
    "ProjectResponse",
    "ProjectStatusResponse",
    "UploadedFile",
    "FileMetadata",
    "Position",
    "PositionAudit",
    "AuditReport",
    "ErrorResponse",
    "SuccessResponse",
    
    # === Helper Functions ===
    "db_project_to_response",
    "calculate_audit_summary",
]
