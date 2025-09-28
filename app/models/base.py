# app/models/base.py
"""
Base model with common fields and functionality
"""
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models"""
    pass


class BaseModel(Base):
    """Base model with common fields"""
    __abstract__ = True
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)  # Use String for UUID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }