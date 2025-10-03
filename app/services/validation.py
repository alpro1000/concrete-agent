"""
File validation service for multipart/form-data uploads
Validates MIME types and file sizes according to field type
"""

from fastapi import HTTPException, UploadFile
from typing import List, Optional
import os
import logging

logger = logging.getLogger(__name__)

# Maximum file size in bytes (50 MB)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

# MIME types allowed for each field type
ALLOWED_MIME_TYPES = {
    # technical_files | project_documentation
    "technical": [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain"
    ],
    # quantities_files | budget_estimate
    "quantities": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/pdf",
        "application/xml",
        "text/xml"
    ],
    # drawings_files | drawings
    "drawings": [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/bmp",
        "application/acad",
        "image/vnd.dwg",
        "application/dwg",
        "image/x-dwg",
        "application/dxf"
    ]
}


def get_mime_type_from_filename(filename: str) -> str:
    """
    Get MIME type from file extension
    
    Args:
        filename: Name of the file
        
    Returns:
        MIME type string
    """
    ext = os.path.splitext(filename)[1].lower()
    
    # Map extensions to MIME types
    mime_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".xml": "application/xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".dwg": "application/acad",
        ".dxf": "application/dxf"
    }
    
    return mime_map.get(ext, "application/octet-stream")


async def validate_file(
    file: UploadFile,
    field_type: str,
    max_size: int = MAX_FILE_SIZE
) -> dict:
    """
    Validate a single file for MIME type and size
    
    Args:
        file: FastAPI UploadFile object
        field_type: Type of field (technical, quantities, drawings)
        max_size: Maximum file size in bytes
        
    Returns:
        dict with validation result
        
    Raises:
        HTTPException: If validation fails
    """
    # Get MIME type from content_type or filename
    mime_type = file.content_type or get_mime_type_from_filename(file.filename)
    
    # Validate MIME type
    allowed_types = ALLOWED_MIME_TYPES.get(field_type, [])
    if mime_type not in allowed_types:
        detail = f"Invalid file type '{mime_type}' for {field_type}. Allowed: {', '.join(allowed_types)}"
        logger.warning(f"File {file.filename}: {detail}")
        raise HTTPException(status_code=400, detail=detail)
    
    # Read content to check size
    content = await file.read()
    file_size = len(content)
    
    if file_size > max_size:
        detail = f"File too large: {file_size} bytes (max {max_size} bytes / {max_size / 1024 / 1024:.1f}MB)"
        logger.warning(f"File {file.filename}: {detail}")
        raise HTTPException(status_code=400, detail=detail)
    
    if file_size == 0:
        detail = "Empty file not allowed"
        logger.warning(f"File {file.filename}: {detail}")
        raise HTTPException(status_code=400, detail=detail)
    
    # Reset file pointer for later use
    await file.seek(0)
    
    logger.info(f"Validated {file.filename}: {mime_type}, {file_size} bytes")
    
    return {
        "filename": file.filename,
        "mime_type": mime_type,
        "size": file_size,
        "valid": True
    }


async def validate_files(
    files: Optional[List[UploadFile]],
    field_type: str
) -> List[dict]:
    """
    Validate multiple files
    
    Args:
        files: List of UploadFile objects
        field_type: Type of field (technical, quantities, drawings)
        
    Returns:
        List of validation results
    """
    if not files:
        return []
    
    results = []
    for file in files:
        try:
            result = await validate_file(file, field_type)
            results.append(result)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating file {file.filename}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Error validating file {file.filename}: {str(e)}"
            )
    
    return results
