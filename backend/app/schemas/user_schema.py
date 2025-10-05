"""
Pydantic schemas for user data.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating user data."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class Token(BaseModel):
    """Schema for authentication token."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token data."""
    username: Optional[str] = None
