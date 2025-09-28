# app/models/correction.py
"""
Correction model for storing user feedback and corrections
"""
from sqlalchemy import Column, Text, ForeignKey, JSON, String
from sqlalchemy.orm import relationship
from .base import BaseModel


class Correction(BaseModel):
    """Correction model - stores user corrections for self-learning"""
    __tablename__ = "corrections"
    
    extraction_id = Column(String(36), ForeignKey("extractions.id"), nullable=False, index=True)  # Use String for UUID
    user_feedback = Column(Text, nullable=True)
    corrected_data = Column(JSON, nullable=False)  # Corrected analysis results
    
    # Relationships
    extraction = relationship("Extraction", back_populates="corrections")
    
    def __repr__(self):
        return f"<Correction(id={self.id}, extraction_id={self.extraction_id})>"