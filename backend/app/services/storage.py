"""
Storage service for managing file uploads and storage.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from app.core.config import settings
from app.core.logging_config import app_logger
from app.core.exceptions import StorageException
from app.core.utils import generate_uuid


class StorageService:
    """Service for handling file storage operations."""
    
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_upload_file(
        self,
        file: UploadFile,
        user_id: Optional[int] = None,
        subdirectory: Optional[str] = None
    ) -> dict:
        """
        Save an uploaded file.
        
        Args:
            file: Uploaded file
            user_id: Optional user ID for organizing files
            subdirectory: Optional subdirectory within upload dir
            
        Returns:
            Dict with file information
        """
        try:
            # Create directory path
            save_dir = self.upload_dir
            if subdirectory:
                save_dir = save_dir / subdirectory
            if user_id:
                save_dir = save_dir / str(user_id)
            
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            file_extension = Path(file.filename).suffix
            unique_filename = f"{generate_uuid()}{file_extension}"
            file_path = save_dir / unique_filename
            
            # Check file size
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning
            
            if file_size > settings.max_upload_size:
                raise StorageException(
                    f"File size ({file_size}) exceeds maximum allowed size ({settings.max_upload_size})",
                    {"file_size": file_size, "max_size": settings.max_upload_size}
                )
            
            # Save file
            with open(file_path, 'wb') as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            app_logger.info(f"Saved file: {file_path}")
            
            return {
                "filename": unique_filename,
                "original_filename": file.filename,
                "file_path": str(file_path),
                "file_size": file_size,
                "content_type": file.content_type
            }
            
        except StorageException:
            raise
        except Exception as e:
            app_logger.error(f"Failed to save file: {e}")
            raise StorageException(f"Failed to save file: {e}")
    
    async def read_file(self, file_path: str) -> bytes:
        """
        Read a file from storage.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content as bytes
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise StorageException(f"File not found: {file_path}")
            
            with open(path, 'rb') as f:
                return f.read()
                
        except Exception as e:
            app_logger.error(f"Failed to read file: {e}")
            raise StorageException(f"Failed to read file: {e}")
    
    async def read_text_file(self, file_path: str, encoding: str = 'utf-8') -> str:
        """
        Read a text file from storage.
        
        Args:
            file_path: Path to file
            encoding: File encoding
            
        Returns:
            File content as string
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise StorageException(f"File not found: {file_path}")
            
            with open(path, 'r', encoding=encoding) as f:
                return f.read()
                
        except Exception as e:
            app_logger.error(f"Failed to read text file: {e}")
            raise StorageException(f"Failed to read text file: {e}")
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if deleted successfully
        """
        try:
            path = Path(file_path)
            
            if path.exists():
                path.unlink()
                app_logger.info(f"Deleted file: {file_path}")
                return True
            
            return False
            
        except Exception as e:
            app_logger.error(f"Failed to delete file: {e}")
            raise StorageException(f"Failed to delete file: {e}")
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get file information.
        
        Args:
            file_path: Path to file
            
        Returns:
            File information dict
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise StorageException(f"File not found: {file_path}")
            
            stat = path.stat()
            
            return {
                "filename": path.name,
                "file_path": str(path),
                "file_size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime
            }
            
        except Exception as e:
            app_logger.error(f"Failed to get file info: {e}")
            raise StorageException(f"Failed to get file info: {e}")


# Global storage service instance
storage_service = StorageService()
