"""
API Routes for Workflow B - Specialized Endpoints
POUZE specifické endpointy pro Workflow B (bez upload!)
"""
from pathlib import Path
import logging
import json

from fastapi import APIRouter, HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow-b", tags=["Workflow B"])


# =============================================================================
# WORKFLOW B SPECIFIC ENDPOINTS
# =============================================================================

@router.get("/{project_id}/tech-card")
async def get_tech_card(project_id: str):
    """
    Získat technologickou kartu
    
    Obsahuje:
    - Vypočtené množství materiálů
    - Technologické postupy
    - Časové odhady
    - Požadované zdroje
    
    Args:
        project_id: ID projektu
    
    Returns:
        Technologická karta
    """
    try:
        # Načíst project info
        project_dir = settings.DATA_DIR / "raw" / project_id
        info_path = project_dir / "project_info.json"
        
        if not info_path.exists():
            raise HTTPException(status_code=404, detail="Projekt nenalezen")
        
        with open(info_path, 'r', encoding='utf-8') as f:
            project_info = json.load(f)
        
        # Ověřit že je to Workflow B
        if project_info.get("workflow") != "B":
            raise HTTPException(
                status_code=400,
                detail="Tento endpoint je pouze pro Workflow B"
            )
        
        # Načíst tech card
        results_dir = settings.DATA_DIR / "results" / project_id
        tech_card_path = results_dir / "tech_card.json"
        
        if not tech_card_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Technologická karta ještě nebyla vygenerována"
            )
        
        with open(tech_card_path, 'r', encoding='utf-8') as f:
            tech_card = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "tech_card": tech_card
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při načítání tech. karty: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/calculations")
async def get_material_calculations(project_id: str):
    """
    Získat výpočty materiálů
    
    Detailní výpočty:
    - Beton (m³) podle typů a tříd
    - Výztuž (kg) podle průměrů
    - Bednění (m²) podle typů
    - Ostatní materiály
    
    Args:
        project_id: ID projektu
    
    Returns:
        Výpočty materiálů
    """
    try:
        results_dir = settings.DATA_DIR / "results" / project_id
        calc_path = results_dir / "material_calculations.json"
        
        if not calc_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Výpočty materiálů nejsou k dispozici"
            )
        
        with open(calc_path, 'r', encoding='utf-8') as f:
            calculations = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "calculations": calculations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při načítání výpočtů: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/drawing-analysis")
async def get_drawing_analysis(project_id: str):
    """
    Získat analýzu výkresů
    
    Obsahuje:
    - Rozpoznané elementy (zdi, stropy, základy)
    - Dimenze a materiály
    - Detekované problémy
    - Poznámky a doporučení
    
    Args:
        project_id: ID projektu
    
    Returns:
        Analýza výkresů
    """
    try:
        curated_dir = settings.DATA_DIR / "curated" / project_id
        analysis_path = curated_dir / "drawing_analysis.json"
        
        if not analysis_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Analýza výkresů není k dispozici"
            )
        
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při načítání analýzy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/generated-vykaz")
async def get_generated_vykaz(project_id: str):
    """
    Získat vygenerovaný výkaz výměr
    
    Výkaz vytvořený z výkresů pomocí AI:
    - Všechny pozice
    - Množství
    - Jednotky
    - Popisky
    
    Args:
        project_id: ID projektu
    
    Returns:
        Vygenerovaný výkaz
    """
    try:
        results_dir = settings.DATA_DIR / "results" / project_id
        vykaz_path = results_dir / "generated_vykaz.json"
        
        if not vykaz_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Výkaz ještě nebyl vygenerován"
            )
        
        with open(vykaz_path, 'r', encoding='utf-8') as f:
            vykaz = json.load(f)
        
        return {
            "success": True,
            "project_id": project_id,
            "vykaz": vykaz,
            "total_positions": len(vykaz.get("positions", []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba při načítání výkazu: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/comparison")
async def compare_with_similar_projects(project_id: str):
    """
    Porovnat s podobnými projekty
    
    Porovnání:
    - Podobné projekty z historie
    - Rozdíly v množstvích
    - Cenové srovnání
    - Doporučení
    
    Args:
        project_id: ID projektu
    
    Returns:
        Srovnání s podobnými projekty
    """
    try:
        # TODO: Implementovat logiku porovnání
        # Pro teď placeholder
        
        return {
            "success": True,
            "project_id": project_id,
            "similar_projects": [],
            "message": "Funkce bude implementována v příští verzi"
        }
        
    except Exception as e:
        logger.error(f"Chyba při porovnání: {e}")
        raise HTTPException(status_code=500, detail=str(e))
