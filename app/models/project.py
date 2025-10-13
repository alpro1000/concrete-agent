"""
Project models for Czech Building Audit System
Combines SQLAlchemy (DB) and Pydantic (API) models
UPDATED: Compatible with routes.py usage patterns
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# SQLAlchemy Base
Base = declarative_base()


# =============================================================================
# ENUMS
# =============================================================================

class ProjectStatus(str, Enum):
    """Project processing status"""
    PENDING = "pending"          # Initial state after upload
    UPLOADED = "uploaded"        # Files uploaded, ready to process
    PROCESSING = "processing"    # Currently processing
    PARSED = "parsed"            # Parsing completed
    STAGING = "staging"          # In staging phase
    CURATED = "curated"          # Data curated
    AUDIT_IN_PROGRESS = "audit_in_progress"  # Audit running
    AUDIT_COMPLETED = "audit_completed"      # Audit completed
    HITL_REVIEW = "hitl_review"  # Human review needed
    COMPLETED = "completed"      # Fully completed
    FAILED = "failed"            # Processing failed


class AuditClassification(str, Enum):
    """Audit classification for positions"""
    GREEN = "green"  # All checks passed
    AMBER = "amber"  # Minor issues, needs attention
    RED = "red"      # Critical issues, requires review


class WorkflowType(str, Enum):
    """Workflow type"""
    A = "A"  # With výkaz výměr (bill of quantities)
    B = "B"  # Without výkaz (generate from drawings)


# =============================================================================
# SQLAlchemy DATABASE MODEL
# =============================================================================

class Project(Base):
    """
    Project database model (SQLAlchemy)
    Stores project metadata and processing status
    """
    __tablename__ = "projects"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Basic info
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.UPLOADED, nullable=False)
    workflow = Column(SQLEnum(WorkflowType), nullable=True)
    
    # File paths (ETL pipeline)
    raw_file_path = Column(String(1000), nullable=True)
    staging_file_path = Column(String(1000), nullable=True)
    curated_file_path = Column(String(1000), nullable=True)
    audit_report_path = Column(String(1000), nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    audit_completed_at = Column(DateTime, nullable=True)
    
    # Audit statistics
    total_positions = Column(Integer, default=0)
    green_count = Column(Integer, default=0)
    amber_count = Column(Integer, default=0)
    red_count = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Project {self.project_id}: {self.name} ({self.status.value})>"


# =============================================================================
# PYDANTIC API MODELS
# =============================================================================

class ProjectCreate(BaseModel):
    """Request model for creating a new project"""
    name: str = Field(..., description="Project name", min_length=1, max_length=500)
    description: Optional[str] = Field(None, description="Optional project description")
    workflow: Optional[WorkflowType] = Field(
        WorkflowType.A, 
        description="Workflow type: A (with výkaz) or B (without)"
    )


class UploadedFile(BaseModel):
    """Information about an uploaded file"""
    filename: str = Field(..., description="Original filename")
    saved_as: str = Field(..., description="Saved filename with path")
    file_type: str = Field(..., description="File type (pdf, xml, xlsx)")
    size: int = Field(..., description="File size in bytes")


class FileMetadata(BaseModel):
    """
    Metadata about uploaded file
    CRITICAL: Field names MUST match usage in routes.py!
    """
    # Core fields (used in routes.py)
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    uploaded_at: str = Field(..., description="Upload timestamp (ISO format)")
    file_type: str = Field(..., description="File extension without dot (pdf, xml, xlsx)")
    
    # Optional fields
    mime_type: Optional[str] = Field(None, description="MIME type")
    checksum: Optional[str] = Field(None, description="File checksum (MD5/SHA256)")
    
    # ETL stage tracking
    stage: str = Field(default="raw", description="Current ETL stage (raw/staging/curated)")
    processed: bool = Field(default=False, description="Whether file has been processed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "estimate.xlsx",
                "size": 1048576,
                "uploaded_at": "2025-10-13T10:30:00",
                "file_type": "xlsx"
            }
        }
    )


class ProjectResponse(BaseModel):
    """
    Response model for project information
    FLEXIBLE: Supports both upload response and status response formats
    """
    # Core fields (always present)
    project_id: str
    
    # Name field (support both variants)
    project_name: Optional[str] = Field(None, description="Project name")
    name: Optional[str] = Field(None, description="Project name (alternative)")
    
    # Status and workflow
    workflow: Union[WorkflowType, str]
    status: Optional[ProjectStatus] = None
    
    # Timestamps (flexible format)
    uploaded_at: Union[datetime, str]
    created_at: Optional[Union[datetime, str]] = None
    processed_at: Optional[Union[datetime, str]] = None
    audit_completed_at: Optional[Union[datetime, str]] = None
    updated_at: Optional[Union[datetime, str]] = None
    
    # Upload response fields
    success: Optional[bool] = Field(None, description="Success flag for upload")
    files_uploaded: Optional[Dict[str, Any]] = Field(None, description="Files uploaded info")
    enrichment_enabled: Optional[bool] = Field(None, description="Enrichment status")
    
    # Status response fields
    files: Optional[List[Dict[str, Any]]] = Field(None, description="List of files")
    
    # Optional metadata
    description: Optional[str] = None
    
    # Statistics
    total_positions: int = 0
    positions_total: int = 0
    green_count: int = 0
    amber_count: int = 0
    red_count: int = 0
    
    # Progress
    progress: int = Field(0, ge=0, le=100, description="Processing progress percentage")
    message: str = Field("", description="Status message")
    
    model_config = ConfigDict(
        from_attributes=True,
        extra="allow"  # Allow extra fields
    )


class ProjectStatusResponse(BaseModel):
    """
    Detailed project status response
    FLEXIBLE: Matches routes.py return format
    """
    # Core fields
    project_id: str
    project_name: Optional[str] = None
    status: Union[ProjectStatus, str]
    workflow: Union[WorkflowType, str]
    
    # Progress info
    progress: int = Field(0, ge=0, le=100)
    message: Optional[str] = Field(None, description="Status message")
    
    # Processing info
    positions_processed: int = 0
    positions_total: int = 0
    
    # Audit results (optional)
    green_count: int = 0
    amber_count: int = 0
    red_count: int = 0
    
    # Timestamps (flexible string or datetime)
    created_at: Optional[Union[datetime, str]] = None
    updated_at: Optional[Union[datetime, str]] = None
    uploaded_at: Optional[Union[datetime, str]] = None
    processed_at: Optional[Union[datetime, str]] = None
    audit_completed_at: Optional[Union[datetime, str]] = None
    completed_at: Optional[Union[datetime, str]] = None
    
    # Error info (if failed)
    error_message: Optional[str] = None
    
    # Enrichment info
    enrichment_enabled: Optional[bool] = None
    
    model_config = ConfigDict(extra="allow")


class Position(BaseModel):
    """Building position/item model"""
    position_number: str = Field(..., description="Position number (PČ)")
    code: Optional[str] = Field(None, description="KROS/ÚRS code")
    name: str = Field(..., description="Position name/description")
    unit: str = Field(..., description="Unit of measurement (MJ)")
    quantity: float = Field(..., gt=0, description="Quantity (Množství)")
    unit_price: Optional[float] = Field(None, description="Unit price (J.cena)")
    total_price: Optional[float] = Field(None, description="Total price (Cena celkem)")
    
    # Additional fields
    category: Optional[str] = None
    section: Optional[str] = None


class PositionAudit(BaseModel):
    """Audit result for a single position"""
    position: Position
    classification: AuditClassification  # GREEN/AMBER/RED
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in classification")
    
    # Audit findings
    findings: List[str] = Field(default_factory=list, description="List of audit findings")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    errors: List[str] = Field(default_factory=list, description="Critical errors")
    
    # HITL flag
    requires_hitl: bool = Field(False, description="Requires human-in-the-loop review")
    hitl_reason: Optional[str] = Field(None, description="Reason for HITL")
    
    # Matching info
    matched_code: Optional[str] = None
    matched_name: Optional[str] = None
    price_difference_pct: Optional[float] = None


class AuditReport(BaseModel):
    """Complete audit report for a project"""
    project_id: str
    project_name: str
    audit_timestamp: datetime
    
    # Summary statistics
    total_positions: int
    green_count: int
    amber_count: int
    red_count: int
    hitl_count: int
    
    # Detailed results
    positions: List[PositionAudit]
    
    # Overall assessment
    overall_risk: AuditClassification
    recommendations: List[str] = []


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = Field(True, description="Success flag")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def db_project_to_response(db_project: Project) -> ProjectResponse:
    """
    Convert SQLAlchemy Project to Pydantic ProjectResponse
    
    Args:
        db_project: SQLAlchemy Project instance
        
    Returns:
        Pydantic ProjectResponse
    """
    # Calculate progress based on status
    progress_map = {
        ProjectStatus.PENDING: 5,
        ProjectStatus.UPLOADED: 10,
        ProjectStatus.PROCESSING: 30,
        ProjectStatus.PARSED: 50,
        ProjectStatus.STAGING: 60,
        ProjectStatus.CURATED: 70,
        ProjectStatus.AUDIT_IN_PROGRESS: 85,
        ProjectStatus.AUDIT_COMPLETED: 95,
        ProjectStatus.HITL_REVIEW: 98,
        ProjectStatus.COMPLETED: 100,
        ProjectStatus.FAILED: 0,
    }
    
    progress = progress_map.get(db_project.status, 0)
    
    # Generate status message
    if db_project.status == ProjectStatus.FAILED:
        message = f"Failed: {db_project.error_message or 'Unknown error'}"
    elif db_project.status == ProjectStatus.COMPLETED:
        message = f"Audit completed: {db_project.green_count}G / {db_project.amber_count}A / {db_project.red_count}R"
    else:
        message = f"Processing: {db_project.status.value}"
    
    return ProjectResponse(
        project_id=db_project.project_id,
        name=db_project.name,
        description=db_project.description,
        status=db_project.status,
        workflow=db_project.workflow or WorkflowType.A,
        uploaded_at=db_project.uploaded_at,
        processed_at=db_project.processed_at,
        audit_completed_at=db_project.audit_completed_at,
        files=[],  # TODO: Extract from file paths
        total_positions=db_project.total_positions,
        green_count=db_project.green_count,
        amber_count=db_project.amber_count,
        red_count=db_project.red_count,
        progress=progress,
        message=message,
    )


def calculate_audit_summary(positions: List[PositionAudit]) -> Dict[str, int]:
    """
    Calculate audit summary statistics
    
    Args:
        positions: List of audited positions
        
    Returns:
        Dict with counts for each classification
    """
    summary = {
        "total": len(positions),
        "green": sum(1 for p in positions if p.classification == AuditClassification.GREEN),
        "amber": sum(1 for p in positions if p.classification == AuditClassification.AMBER),
        "red": sum(1 for p in positions if p.classification == AuditClassification.RED),
        "hitl": sum(1 for p in positions if p.requires_hitl),
    }
    return summary
