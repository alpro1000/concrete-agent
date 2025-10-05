"""
Analysis database model.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from backend.app.core.database import Base


class AnalysisStatus(enum.Enum):
    """Analysis status enumeration."""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Analysis(Base):
    """Database model for construction analyses."""
    
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Analysis details
    analysis_type = Column(String(50), nullable=False)  # tzd, boq, drawing, etc.
    status = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.pending)
    
    # Results
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    reasoning_chain = Column(JSON, nullable=True)
    
    # Metadata
    agent_name = Column(String(50), nullable=True)
    agent_version = Column(String(20), nullable=True)
    execution_time = Column(Integer, nullable=True)  # milliseconds
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
