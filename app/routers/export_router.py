"""
Export API Router
Provides document generation (PDF/DOCX/XLSX)
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["export"])


class ExportRequest(BaseModel):
    """Export request model"""
    analysis_id: str
    format: str = "pdf"  # pdf, docx, xlsx, or all


@router.get("/")
async def export_root():
    """Export API information"""
    return {
        "service": "Export API",
        "version": "1.0.0",
        "description": "Generate PDF/DOCX/XLSX reports from analysis results",
        "supported_formats": ["pdf", "docx", "xlsx", "all"],
        "endpoints": {
            "export": "POST /api/v1/export/generate",
            "download": "GET /api/v1/export/download/{file_id}"
        }
    }


@router.post("/generate")
async def generate_export(request: ExportRequest):
    """
    Generate export documents from analysis results
    
    - **analysis_id**: Analysis ID to export
    - **format**: Export format - pdf, docx, xlsx, or all
    """
    try:
        from app.agents.export_agent import ExportAgent
        import json
        
        # Load analysis results
        storage_path = Path("/home/runner/work/concrete-agent/concrete-agent/storage")
        result_file = storage_path / "results" / f"{request.analysis_id}.json"
        
        if not result_file.exists():
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        with open(result_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Generate export
        agent = ExportAgent()
        output_dir = tempfile.mkdtemp()
        
        result = await agent.analyze({
            "data": analysis_data,
            "format": request.format,
            "output_dir": output_dir
        })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats")
async def get_formats():
    """Get supported export formats"""
    return {
        "formats": [
            {
                "id": "pdf",
                "name": "PDF Report",
                "description": "Portable Document Format report"
            },
            {
                "id": "docx",
                "name": "Word Document",
                "description": "Microsoft Word document"
            },
            {
                "id": "xlsx",
                "name": "Excel Spreadsheet",
                "description": "Microsoft Excel spreadsheet"
            },
            {
                "id": "all",
                "name": "All Formats",
                "description": "Generate all supported formats"
            }
        ]
    }
