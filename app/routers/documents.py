# app/routers/documents.py
"""
Document management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models import Document, Folder
from app.services import StorageService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
storage_service = StorageService()


class DocumentResponse(BaseModel):
    """Document response schema"""
    id: str
    folder_id: str
    filename: str
    file_hash: str
    file_type: str
    version: int
    size: int
    uploaded_at: str
    status: str
    
    class Config:
        from_attributes = True


@router.get("/projects/{project_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List documents in a project"""
    try:
        query = (
            select(Document)
            .join(Folder)
            .where(Folder.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .order_by(Document.uploaded_at.desc())
        )
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return [
            DocumentResponse(
                id=str(doc.id),
                folder_id=str(doc.folder_id),
                filename=doc.filename,
                file_hash=doc.file_hash,
                file_type=doc.file_type.value,
                version=doc.version,
                size=doc.size,
                uploaded_at=doc.uploaded_at.isoformat(),
                status=doc.status.value
            )
            for doc in documents
        ]
        
    except Exception as e:
        logger.error(f"❌ Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/projects/{project_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    project_id: str,
    doc_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get document metadata"""
    try:
        query = (
            select(Document)
            .join(Folder)
            .where(
                Document.id == doc_id,
                Folder.project_id == project_id
            )
        )
        
        result = await db.execute(query)
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentResponse(
            id=str(document.id),
            folder_id=str(document.folder_id),
            filename=document.filename,
            file_hash=document.file_hash,
            file_type=document.file_type.value,
            version=document.version,
            size=document.size,
            uploaded_at=document.uploaded_at.isoformat(),
            status=document.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document")


@router.get("/projects/{project_id}/documents/{doc_id}/download")
async def download_document(
    project_id: str,
    doc_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download document file"""
    try:
        # Get document metadata
        query = (
            select(Document)
            .join(Folder)
            .where(
                Document.id == doc_id,
                Folder.project_id == project_id
            )
        )
        
        result = await db.execute(query)
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get file content from storage
        file_content = await storage_service.get_file_content(
            project_id, doc_id, document.filename
        )
        
        # Determine content type
        content_type_mapping = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "txt": "text/plain",
            "xml": "application/xml"
        }
        
        content_type = content_type_mapping.get(document.file_type.value, "application/octet-stream")
        
        return Response(
            content=file_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={document.filename}"
            }
        )
        
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in storage")
    except Exception as e:
        logger.error(f"❌ Error downloading document: {e}")
        raise HTTPException(status_code=500, detail="Failed to download document")