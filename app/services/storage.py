"""
File storage service for saving uploaded files
Handles secure file naming and directory structure
"""

from fastapi import UploadFile
from typing import List, Optional
import os
import uuid
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

STORAGE_BASE = os.getenv("STORAGE_BASE", "storage")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other security issues
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Remove directory components
    filename = os.path.basename(filename)
    
    # Replace any character that's not alphanumeric, underscore, dash, or dot
    filename = re.sub(r'[^\w\-.]', '_', filename)
    
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    
    return f"{name}{ext}"


def get_storage_path(user_id: int, analysis_id: str) -> Path:
    """
    Get storage path for a specific user and analysis
    
    Args:
        user_id: User ID
        analysis_id: Analysis ID (UUID)
        
    Returns:
        Path object for storage directory
    """
    return Path(STORAGE_BASE) / str(user_id) / "uploads" / analysis_id


async def save_file(
    file: UploadFile,
    user_id: int,
    analysis_id: str,
    field_type: str
) -> dict:
    """
    Save a single uploaded file to storage
    
    Args:
        file: FastAPI UploadFile object
        user_id: User ID
        analysis_id: Analysis ID (UUID)
        field_type: Type of field (technical, quantities, drawings)
        
    Returns:
        dict with file information
    """
    # Create storage directory
    storage_path = get_storage_path(user_id, analysis_id)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)
    
    # Create full file path
    file_path = storage_path / safe_filename
    
    # If file exists, append a number to make it unique
    counter = 1
    original_path = file_path
    while file_path.exists():
        name, ext = os.path.splitext(safe_filename)
        file_path = storage_path / f"{name}_{counter}{ext}"
        counter += 1
    
    # Save file
    content = await file.read()
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Reset file pointer
    await file.seek(0)
    
    logger.info(f"Saved file: {file_path} ({len(content)} bytes)")
    
    return {
        "original_filename": file.filename,
        "saved_filename": file_path.name,
        "path": str(file_path),
        "size": len(content),
        "field_type": field_type
    }


async def save_files(
    files: Optional[List[UploadFile]],
    user_id: int,
    analysis_id: str,
    field_type: str
) -> List[dict]:
    """
    Save multiple uploaded files
    
    Args:
        files: List of UploadFile objects
        user_id: User ID
        analysis_id: Analysis ID (UUID)
        field_type: Type of field (technical, quantities, drawings)
        
    Returns:
        List of file information dictionaries
    """
    if not files:
        return []
    
    saved_files = []
    for file in files:
        try:
            file_info = await save_file(file, user_id, analysis_id, field_type)
            saved_files.append(file_info)
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            raise
    
    return saved_files


def create_analysis_id() -> str:
    """
    Generate a new analysis ID (UUID)
    
    Returns:
        UUID string
    """
    return str(uuid.uuid4())
