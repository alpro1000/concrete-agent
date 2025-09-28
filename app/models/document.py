# app/models/document.py
"""
Document model for storing file metadata and versions
"""
import enum
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class FileType(enum.Enum):
    """Supported file types"""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    XML = "xml"
    TXT = "txt"
    DWG = "dwg"
    OTHER = "other"


class DocumentStatus(enum.Enum):
    """Document processing status"""
    NEW = "new"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(BaseModel):
    """Document model - stores file metadata and versions"""
    __tablename__ = "documents"
    
    folder_id = Column(String(36), ForeignKey("folders.id"), nullable=False, index=True)  # Use String for UUID
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash
    file_type = Column(Enum(FileType), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    size = Column(Integer, nullable=False)  # Size in bytes
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.NEW, nullable=False)
    
    # Relationships
    folder = relationship("Folder", back_populates="documents")
    extractions = relationship("Extraction", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', version={self.version})>"