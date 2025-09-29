# app/models/tov_plan.py
"""
TOV (Technical Organization of Works) Plan model
"""
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from .base import BaseModel


class TOVPlan(BaseModel):
    """TOV Plan model for construction work organization"""
    __tablename__ = "tov_plans"
    
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # TOV-specific data
    work_phases = Column(JSON, default=list, nullable=False)  # List of work phases
    resource_allocation = Column(JSON, default=dict, nullable=False)  # Resource planning
    timeline = Column(JSON, default=dict, nullable=False)  # Timeline and scheduling
    dependencies = Column(JSON, default=list, nullable=False)  # Work dependencies
    
    # Metrics
    total_duration_days = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Metadata
    tov_metadata = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="tov_plans")
    
    def __repr__(self):
        return f"<TOVPlan(id={self.id}, name='{self.name}', project_id='{self.project_id}')>"