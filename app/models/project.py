# app/models/project.py
"""
Project model for organizing construction documents
"""
from sqlalchemy import Column, String, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel


class Project(BaseModel):
    """Project model - top level container for construction documents"""
    __tablename__ = "projects"
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    project_metadata = Column(JSON, default=dict, nullable=False)  # Use JSON for SQLite compatibility
    
    # Relationships
    folders = relationship("Folder", back_populates="project", cascade="all, delete-orphan")
    tov_plans = relationship("TOVPlan", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"