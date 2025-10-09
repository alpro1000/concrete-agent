"""
Project-related models (Pydantic + SQLAlchemy)
СОВМЕСТИМОСТЬ: Сохраняет все существующие имена
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# SQLAlchemy imports (только для класса Project)
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# =============================================================================
# СУЩЕСТВУЮЩИЕ PYDANTIC МОДЕЛИ (БЕЗ ИЗМЕНЕНИЙ)
# =============================================================================

class ProjectStatus(str, Enum):
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


class FileMetadata(BaseModel):
    """Safe file metadata without exposing server paths"""
    file_id: str = Field(..., description="Logical file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="Type of file (vykaz_vymer, vykresy, etc.)")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class ProjectResponse(BaseModel):
    """Response model for project"""
    project_id: str
    name: str
    upload_timestamp: datetime
    status: ProjectStatus
    workflow: WorkflowType
    files: List[Dict[str, Any]]  # Safe file metadata (no paths)
    message: str


# =============================================================================
# НОВОЕ: SQLAlchemy DATABASE MODEL (для БД в Phase 2+)
# =============================================================================

class Project(Base):
    """
    SQLAlchemy модель проекта для базы данных
    ДОБАВЛЕНО: для импорта в routes.py
    """
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Статус (используем существующий ProjectStatus enum)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.UPLOADED)
    workflow = Column(SQLEnum(WorkflowType), nullable=True)
    
    # Пути к файлам
    raw_file_path = Column(String(1000), nullable=True)
    staging_file_path = Column(String(1000), nullable=True)
    curated_file_path = Column(String(1000), nullable=True)
    audit_report_path = Column(String(1000), nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    audit_completed_at = Column(DateTime, nullable=True)
    
    # Статистика аудита
    total_positions = Column(Integer, default=0)
    green_count = Column(Integer, default=0)
    amber_count = Column(Integer, default=0)
    red_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Project {self.project_id}: {self.name}>"
    
    def to_response(self) -> ProjectResponse:
        """Конвертация в Pydantic модель для API"""
        return ProjectResponse(
            project_id=self.project_id,
            name=self.name,
            upload_timestamp=self.uploaded_at,
            status=self.status,
            workflow=self.workflow or WorkflowType.A,
            files=[],  # TODO: populate from file paths
            message=f"Project {self.status.value}"
        )


# =============================================================================
# PROJECT STATUS RESPONSE
# =============================================================================

class ProjectStatusResponse(BaseModel):
    """Detailed project status for API"""
    project_id: str
    status: ProjectStatus
    progress: int = Field(0, ge=0, le=100)
    message: str
    positions_processed: int = 0
    positions_total: int = 0
    green_count: int = 0
    amber_count: int = 0
    red_count: int = 0
