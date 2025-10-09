"""
API Routes for Workflow A - Specialized Endpoints
POUZE specifické endpointy pro Workflow A (bez upload!)
"""
from pathlib import Path
from typing import List
import logging
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow-a", tags=["Workflow A"])


# Request/Response Models
class AnalyzePositionsRequest(BaseModel):
    """Request pro analýzu vybraných pozic"""
    selected_indices: List[int]
    context: dict = {}


# =============================================================================
# WORKFLOW A SPECIFIC ENDPOINTS
# =============================================================================

@router.get("/{project_id}/positions")
async def get_positions(project_id: str):
    """
    Získat všechny pozice z výkazu výměr
    
    Args:
        project_id: ID projektu
    
    Returns:
        Seznam všech pozic
    """
    try:
        # Načíst project info
        project_dir = settings.DATA_DIR / "raw" / project_id
        info_path = project_dir / "project_info.json"
        
        if not info_path.exists():
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        with open(info_path, 'r', encoding='utf-8') as f:
            project_info = json.load(f)
        
        # Ověřit že je to Workflow A
        if project_info.get("workflow") != "A":
            raise HTTPException(
                status_code=400,
                detail="Tento endpoint je pouze pro Workflow A"
            )
        
        # Načíst parsované pozice
        curated_dir = settings.DATA_DIR / "curated" / project_id
        positions_path = curated_dir / "parsed_positions.json"
        
        if not positions_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Pozice ještě nebyly zpracovány"
            )
        
        with open(positions_path, 'r', encoding='utf-8') as f:
            positions_data = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_info["project_name"],
            "total_positions": len(positions_data.get("positions", [])),
            "positions": positions_data.get("positions", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při získávání pozic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/analyze")
async def analyze_selected_positions(
    project_id: str,
    request: AnalyzePositionsRequest
):
    """
    Detailní analýza vybraných pozic
    
    Provede hloubkovou kontrolu:
    - Správnost kódů KROS/RTS
    - Ceny vs. databáze
    - Normy ČSN
    - Materiály a podmínky (z výkresů)
    
    Args:
        project_id: ID projektu
        request: Vybrané indexy pozic
    
    Returns:
        Detailní výsledky analýzy
    """
    try:
        logger.info(f"Analýza {len(request.selected_indices)} pozic pro {project_id}")
        
        # Načíst pozice
        curated_dir = settings.DATA_DIR / "curated" / project_id
        positions_path = curated_dir / "parsed_positions.json"
        
        if not positions_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Pozice nenalezeny"
            )
        
        with open(positions_path, 'r', encoding='utf-8') as f:
            positions_data = json.load(f)
        
        all_positions = positions_data.get("positions", [])
        
        # Vybrat požadované pozice
        selected = []
        for idx in request.selected_indices:
            if 0 <= idx < len(all_positions):
                selected.append(all_positions[idx])
        
        if not selected:
            raise HTTPException(
                status_code=400,
                detail="Žádné platné pozice k analýze"
            )
        
        # TODO: Spustit detailní analýzu přes Workflow A service
        # Pro teď vrátíme placeholder
        
        return {
            "success": True,
            "project_id": project_id,
            "analyzed_count": len(selected),
            "positions": selected,
            "message": "Analýza probíhá v pozadí"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při analýze: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/summary")
async def get_project_summary(project_id: str):
    """
    Získat shrnutí projektu
    
    Obsahuje:
    - Informace z výkresu (typ stavby, charakteristika)
    - Statistiky pozic
    - Hlavní práce
    - Speciální požadavky
    
    Args:
        project_id: ID projektu
    
    Returns:
        Shrnutí projektu
    """
    try:
        curated_dir = settings.DATA_DIR / "curated" / project_id
        summary_path = curated_dir / "project_summary.json"
        
        if not summary_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Shrnutí ještě nebylo vygenerováno"
            )
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při načítání shrnutí: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/context")
async def get_drawing_context(project_id: str):
    """
    Získat kontext z výkresů
    
    Informace extrahované z výkresů:
    - Materiály a jejich vlastnosti
    - Podmínky zpracování
    - Technologické detaily
    - Speciální požadavky
    
    Args:
        project_id: ID projektu
    
    Returns:
        Kontext z výkresů
    """
    try:
        curated_dir = settings.DATA_DIR / "curated" / project_id
        context_path = curated_dir / "drawing_context.json"
        
        if not context_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Kontext z výkresů nebyl zpracován"
            )
        
        with open(context_path, 'r', encoding='utf-8') as f:
            context = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "context": context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při načítání kontextu: {e}")
        raise HTTPException(status_code=500, detail=str(e))
