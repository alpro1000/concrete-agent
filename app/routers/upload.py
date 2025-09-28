# app/routers/upload.py
"""
Multi-file upload endpoints with ZIP support
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models import Project, Folder, Document, DocumentStatus
from app.models.document import FileType
from app.services import StorageService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
storage_service = StorageService()


class UploadResponse(BaseModel):
    """Upload response schema"""
    project_id: str
    uploaded: List[dict]


@router.post("/projects/{project_id}/upload", response_model=UploadResponse)
async def upload_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload multiple files with ZIP support"""
    try:
        # Verify project exists
        project_query = select(Project).where(Project.id == project_id)
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get or create default folder
        folder = await _get_or_create_default_folder(db, project_id)
        
        # Upload files using storage service
        uploaded_files_data = await storage_service.upload_files(project_id, files)
        
        # Create document records in database
        uploaded_documents = []
        
        for file_data in uploaded_files_data:
            try:
                # Determine file type
                file_type = _get_file_type_enum(
                    storage_service.get_file_type(file_data["filename"])
                )
                
                # Create document record
                document = Document(
                    folder_id=folder.id,
                    filename=file_data["filename"],
                    file_hash=file_data["hash"],
                    file_type=file_type,
                    version=1,
                    size=file_data["size"],
                    status=DocumentStatus.NEW
                )
                
                db.add(document)
                await db.flush()  # Get the ID
                
                # Update response data
                uploaded_documents.append({
                    "document_id": str(document.id),
                    "filename": file_data["filename"],
                    "version": document.version,
                    "status": document.status.value,
                    "file_type": document.file_type.value,
                    "size": file_data["size"],
                    "hash": file_data["hash"],
                    "parent_zip": file_data.get("parent_zip"),
                    "extraction_status": file_data.get("status", "uploaded")
                })
                
                logger.info(f"📄 Document created: {document.filename} (ID: {document.id})")
                
            except Exception as e:
                logger.error(f"❌ Error creating document record for {file_data['filename']}: {e}")
                # Still include in response but mark as failed
                uploaded_documents.append({
                    "document_id": None,
                    "filename": file_data["filename"],
                    "status": "failed",
                    "error": str(e)
                })
        
        await db.commit()
        
        logger.info(f"✅ Uploaded {len(uploaded_documents)} files to project {project_id}")
        
        return UploadResponse(
            project_id=project_id,
            uploaded=uploaded_documents
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading files: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to upload files")


async def _get_or_create_default_folder(db: AsyncSession, project_id: str) -> Folder:
    """Get or create default folder for project"""
    
    # Try to find existing default folder
    folder_query = select(Folder).where(
        Folder.project_id == project_id,
        Folder.name == "default"
    )
    result = await db.execute(folder_query)
    folder = result.scalar_one_or_none()
    
    if folder:
        return folder
    
    # Create default folder
    folder = Folder(
        project_id=project_id,
        name="default",
        path="/default"
    )
    
    db.add(folder)
    await db.flush()
    
    logger.info(f"📁 Created default folder for project {project_id}")
    return folder


def _get_file_type_enum(file_type_str: str) -> FileType:
    """Convert string file type to enum"""
    type_mapping = {
        # Project Documents
        "pdf": FileType.PDF,
        "docx": FileType.DOCX,
        "txt": FileType.TXT,
        
        # Estimates/BOQ
        "xlsx": FileType.XLSX,
        "xml": FileType.XML,
        "csv": FileType.CSV,
        "xc4": FileType.XC4,
        
        # Drawings
        "dwg": FileType.DWG,
        "dxf": FileType.DXF,
        "ifc": FileType.BIM_IFC,
        
        "other": FileType.OTHER
    }
    
    return type_mapping.get(file_type_str, FileType.OTHER)