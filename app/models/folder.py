# app/models/folder.py
"""
Folder model for organizing documents within projects
"""
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class Folder(BaseModel):
    """Folder model - organizes documents within projects"""
    __tablename__ = "folders"
    
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)  # Use String for UUID
    name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="folders")
    documents = relationship("Document", back_populates="folder", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Folder(id={self.id}, name='{self.name}', path='{self.path}')>"