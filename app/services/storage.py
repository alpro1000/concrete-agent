# app/services/storage.py
"""
File storage service with versioning and SHA256 hashing
"""
import os
import hashlib
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from fastapi import UploadFile
import aiofiles
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Service for handling file storage with versioning"""
    
    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def get_project_path(self, project_id: str) -> Path:
        """Get storage path for a project"""
        return self.base_path / "projects" / str(project_id)
    
    def get_document_path(self, project_id: str, document_id: str) -> Path:
        """Get storage path for a document"""
        return self.get_project_path(project_id) / str(document_id)
    
    async def compute_file_hash(self, file_content: bytes) -> str:
        """Compute SHA256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    async def save_file(
        self, 
        project_id: str, 
        document_id: str, 
        filename: str, 
        file_content: bytes
    ) -> Dict[str, Any]:
        """Save file to storage and return metadata"""
        
        document_path = self.get_document_path(project_id, document_id)
        document_path.mkdir(parents=True, exist_ok=True)
        
        file_path = document_path / filename
        file_hash = await self.compute_file_hash(file_content)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        logger.info(f"📁 File saved: {file_path}")
        
        return {
            "path": str(file_path),
            "hash": file_hash,
            "size": len(file_content)
        }
    
    async def upload_files(
        self, 
        project_id: str, 
        files: List[UploadFile]
    ) -> List[Dict[str, Any]]:
        """Upload multiple files, handle ZIP extraction"""
        
        uploaded_files = []
        
        for file in files:
            file_content = await file.read()
            
            # Check if it's a ZIP file
            if file.filename.lower().endswith('.zip'):
                extracted_files = await self._extract_zip_file(
                    project_id, file_content, file.filename
                )
                uploaded_files.extend(extracted_files)
            else:
                # Regular file upload
                document_id = self._generate_document_id()
                file_data = await self.save_file(
                    project_id, document_id, file.filename, file_content
                )
                
                uploaded_files.append({
                    "document_id": document_id,
                    "filename": file.filename,
                    "status": "uploaded",
                    **file_data
                })
        
        return uploaded_files
    
    async def _extract_zip_file(
        self, 
        project_id: str, 
        zip_content: bytes, 
        zip_filename: str
    ) -> List[Dict[str, Any]]:
        """Extract ZIP file and upload contents"""
        
        import tempfile
        extracted_files = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / zip_filename
            
            # Save ZIP to temp location
            with open(zip_path, 'wb') as f:
                f.write(zip_content)
            
            # Extract ZIP
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Process extracted files
                for extracted_file in temp_path.rglob('*'):
                    if extracted_file.is_file() and extracted_file != zip_path:
                        
                        with open(extracted_file, 'rb') as f:
                            file_content = f.read()
                        
                        document_id = self._generate_document_id()
                        relative_path = extracted_file.relative_to(temp_path)
                        
                        file_data = await self.save_file(
                            project_id, document_id, str(relative_path), file_content
                        )
                        
                        extracted_files.append({
                            "document_id": document_id,
                            "filename": str(relative_path),
                            "status": "extracted",
                            "parent_zip": zip_filename,
                            **file_data
                        })
                
            except zipfile.BadZipFile:
                logger.error(f"❌ Invalid ZIP file: {zip_filename}")
                # Still save the ZIP as a regular file
                document_id = self._generate_document_id()
                file_data = await self.save_file(
                    project_id, document_id, zip_filename, zip_content
                )
                
                extracted_files.append({
                    "document_id": document_id,
                    "filename": zip_filename,
                    "status": "invalid_zip",
                    **file_data
                })
        
        return extracted_files
    
    def _generate_document_id(self) -> str:
        """Generate unique document ID"""
        import uuid
        return str(uuid.uuid4())
    
    async def get_file_content(self, project_id: str, document_id: str, filename: str) -> bytes:
        """Retrieve file content"""
        file_path = self.get_document_path(project_id, document_id) / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    
    async def check_file_exists(
        self, 
        project_id: str, 
        filename: str, 
        file_hash: str
    ) -> Optional[Tuple[str, int]]:
        """Check if file with same content already exists, return (document_id, version)"""
        
        project_path = self.get_project_path(project_id)
        if not project_path.exists():
            return None
        
        # Search for files with same hash
        for document_dir in project_path.iterdir():
            if document_dir.is_dir():
                for file_path in document_dir.iterdir():
                    if file_path.is_file() and file_path.name == filename:
                        # Check hash
                        async with aiofiles.open(file_path, 'rb') as f:
                            content = await f.read()
                            existing_hash = await self.compute_file_hash(content)
                            
                            if existing_hash == file_hash:
                                # File already exists with same content
                                return document_dir.name, 1  # Assume version 1 for now
        
        return None
    
    def get_file_type(self, filename: str) -> str:
        """Determine file type from extension"""
        extension = Path(filename).suffix.lower()
        
        type_mapping = {
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.doc': 'docx',
            '.xlsx': 'xlsx',
            '.xls': 'xlsx',
            '.xml': 'xml',
            '.txt': 'txt',
            '.dwg': 'dwg'
        }
        
        return type_mapping.get(extension, 'other')