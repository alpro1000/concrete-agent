"""
Pydantic schemas for TZD Reader Agent.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TZDSection(BaseModel):
    """Represents a section in a TZD document."""
    
    title: str = Field(..., description="Section title")
    content: List[str] = Field(default_factory=list, description="Section content lines")
    subsections: List['TZDSection'] = Field(default_factory=list, description="Nested subsections")


class TZDParseRequest(BaseModel):
    """Request schema for TZD parsing."""
    
    document: str = Field(..., description="TZD document content")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parsing options")
    extract_requirements: bool = Field(default=True, description="Extract technical requirements")
    extract_materials: bool = Field(default=True, description="Extract material specifications")


class TZDParseResponse(BaseModel):
    """Response schema for TZD parsing."""
    
    success: bool = Field(..., description="Whether parsing succeeded")
    sections: List[TZDSection] = Field(default_factory=list, description="Parsed sections")
    requirements: List[str] = Field(default_factory=list, description="Extracted requirements")
    materials: List[str] = Field(default_factory=list, description="Extracted materials")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


# Enable forward references for recursive model
TZDSection.model_rebuild()
