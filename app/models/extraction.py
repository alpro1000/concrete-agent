# app/models/extraction.py
"""
Extraction model for storing AI agent analysis results
"""
from sqlalchemy import Column, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel


class Extraction(BaseModel):
    """Extraction model - stores AI agent analysis results"""
    __tablename__ = "extractions"
    
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)  # Use String for UUID
    agent = Column(String(100), nullable=False, index=True)  # ConcreteAgent, VolumeAgent, etc.
    data = Column(JSON, nullable=False)  # Analysis results in JSON format
    confidence = Column(Float, nullable=True)  # Confidence score 0.0-1.0
    
    # Relationships
    document = relationship("Document", back_populates="extractions")
    corrections = relationship("Correction", back_populates="extraction", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Extraction(id={self.id}, agent='{self.agent}', confidence={self.confidence})>"