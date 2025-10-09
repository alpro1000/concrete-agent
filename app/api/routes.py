"""
API Routes for Czech Building Audit System
"""
from pathlib import Path
from typing import Dict, Any, List, Optional  # ← ДОБАВЬТЕ ЭТУ СТРОКУ!
from datetime import datetime
import json
import logging
import uuid
import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.services.workflow_a import WorkflowA
from app.models.project import Project, ProjectStatus

logger = logging.getLogger(__name__)

async def generate_quick_preview(project_id: str) -> Dict[str, Any]:
    """
    Generate quick preview of uploaded document using Claude
    FIXED: Properly load prompt from file
    """
    logger.info(f"Generating quick preview for {project_id}")
    
    try:
        # Find uploaded file
        raw_dir = settings.DATA_DIR / "raw" / project_id
        if not raw_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Find the file
        files = list(raw_dir.glob("*"))
        if not files:
            raise HTTPException(status_code=404, detail="No files found")
        
        file_path = files[0]
        
        # Initialize Claude client
        from app.core.claude_client import ClaudeClient
        client = ClaudeClient()
        
        # Detect file format
        file_ext = file_path.suffix.lower()
        
        # Parse the file
        if file_ext == '.xml':
            # Check if it's KROS format
            with open(file_path, 'r', encoding='utf-8') as f:
                content_preview = f.read(1000)
            
            if '<TZ>' in content_preview or '<Row>' in content_preview:
                # KROS Table XML
                parsed_data = client.parse_xml(file_path, prompt_name="parsing/parse_kros_table_xml")
            elif '<unixml' in content_preview.lower():
                # KROS UNIXML
                parsed_data = client.parse_xml(file_path, prompt_name="parsing/parse_kros_unixml")
            else:
                # Generic XML
                parsed_data = client.parse_xml(file_path)
        
        elif file_ext in ['.xlsx', '.xls']:
            parsed_data = client.parse_excel(file_path)
        
        elif file_ext == '.pdf':
            parsed_data = client.parse_pdf(file_path)
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_ext}")
        
        # Load quick preview prompt from file
        prompt = client._load_prompt_from_file("analysis/quick_preview")
        
        # Prepare data for preview
        data_summary = {
            "document_type": parsed_data.get("document_info", {}).get("document_type", "Unknown"),
            "total_positions": parsed_data.get("total_positions", 0),
            "positions_sample": parsed_data.get("positions", [])[:5],  # First 5 positions
            "sections": parsed_data.get("sections", [])
        }
        
        # Add data to prompt
        full_prompt = f"""{prompt}

===== DATA Z DOKUMENTU =====
{json.dumps(data_summary, ensure_ascii=False, indent=2)}
"""
        
        # Call Claude for preview
        preview_result = client.call(full_prompt)
        
        # Save preview to curated
        curated_dir = settings.DATA_DIR / "curated" / project_id
        curated_dir.mkdir(parents=True, exist_ok=True)
        
        preview_path = curated_dir / "quick_preview.json"
        with open(preview_path, 'w', encoding='utf-8') as f:
            json.dump({
                "preview": preview_result,
                "parsed_data": parsed_data,
                "generated_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Quick preview generated successfully for {project_id}")
        
        return preview_result
        
    except Exception as e:
        logger.error(f"Preview generation error: {str(e)}")
        # Return fallback preview
        return {
            "nahrano": {
                "nazev_dokumentu": file_path.name if 'file_path' in locals() else "Unknown",
                "format": file_ext.upper() if 'file_ext' in locals() else "Unknown",
                "datum_nacteni": datetime.now().strftime("%Y-%m-%d")
            },
            "obsah": {
                "pocet_pozic": 0,
                "celkova_suma_kc": 0.0,
                "hlavni_prace": [],
                "stav": "chyba při načítání"
            },
            "co_budeme_kontrolovat": [
                "Kódy KROS/RTS",
                "Ceny",
                "Normy ČSN"
            ],
            "doporuceni": f"Chyba při generování náhledu: {str(e)}. Pokračujte na detailní analýzu.",
            "estimate_time_minutes": 5,
            "error": str(e)
        }
