"""
File database model.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class File(Base):
    """Database model for uploaded files."""
    
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    
    # File metadata
    content_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    
    # Processing
    is_processed = Column(Integer, default=0)  # 0=no, 1=yes
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="files")
