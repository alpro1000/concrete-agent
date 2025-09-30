# app/routers/projects.py
"""
Project management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models import Project
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ProjectCreate(BaseModel):
    """Project creation schema"""
    name: str
    description: Optional[str] = None
    metadata: Optional[dict] = None


class ProjectResponse(BaseModel):
    """Project response schema"""
    id: str
    name: str
    description: Optional[str]
    metadata: dict
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    try:
        project = Project(
            name=project_data.name,
            description=project_data.description,
            project_metadata=project_data.metadata or {}
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"✅ Created project: {project.name} (ID: {project.id})")
        
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            metadata=project.project_metadata,
            created_at=project.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Error creating project: {e}")
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all projects"""
    try:
        query = select(Project).offset(skip).limit(limit).order_by(Project.created_at.desc())
        result = await db.execute(query)
        projects = result.scalars().all()
        
        return [
            ProjectResponse(
                id=str(project.id),
                name=project.name,
                description=project.description,
                metadata=project.project_metadata,
                created_at=project.created_at.isoformat()
            )
            for project in projects
        ]
        
    except Exception as e:
        logger.error(f"❌ Error listing projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to list projects")


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get project details"""
    try:
        query = select(Project).where(Project.id == project_id)
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            metadata=project.project_metadata,
            created_at=project.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting project: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project")
