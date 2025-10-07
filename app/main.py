"""
Czech Building Audit System - FastAPI Application
Phase 1: Workflow A (с výkaz výměr)
UPDATED: Integrated with new services
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List, Optional
import shutil
from datetime import datetime

from app.core.config import settings
from app.core.claude_client import ClaudeClient
from app.core.prompt_manager import prompt_manager

# NEW: Import services
from app.services.workflow_a import workflow_a

# Инициализация приложения
app = FastAPI(
    title="Czech Building Audit System",
    description="Phase 1: AUDIT výkazu výměr + Resource Calculation",
    version="1.0.0"
)

# CORS - allow frontend on different domain
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://stav-agent.onrender.com",  # Production frontend
    "https://concrete-agent.onrender.com",  # Backend itself
]

# In development allow all
if settings.BASE_DIR.name == "czech-building-audit":
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (веб-интерфейс)
if settings.WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(settings.WEB_DIR)), name="web")

# Инициализация Claude
claude = ClaudeClient()


@app.get("/")
async def root():
    """Health check и информация о системе"""
    return {
        "status": "online",
        "version": "1.0.0",
        "phase": "Phase 1 - Workflow A + Resource Calculation",
        "features": {
            "workflow_a": settings.ENABLE_WORKFLOW_A,
            "workflow_b": settings.ENABLE_WORKFLOW_B,
            "kros_matching": settings.ENABLE_KROS_MATCHING,
            "rts_matching": settings.ENABLE_RTS_MATCHING,
            "resource_calculation": settings.ENABLE_RESOURCE_CALCULATION,
            "multi_role": settings.multi_role.enabled
        }
    }


@app.post("/api/v1/upload")
async def upload_project(
    files: List[UploadFile] = File(...),
    project_name: Optional[str] = "Nový projekt"
):
    """
    Upload projektových souborů
    
    Args:
        files: Soubory projektu (PDF, Excel)
        project_name: Název projektu
    
    Returns:
        project_id a základní info
    """
    try:
        # Generujeme project_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in project_name if c.isalnum() or c in "_ -")[:30]
        project_id = f"{safe_name}_{timestamp}"
        
        # Создаем папку проекта
        project_dir = settings.DATA_DIR / "raw" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем файлы
        uploaded_files = []
        for file in files:
            file_path = project_dir / file.filename
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            uploaded_files.append({
                "filename": file.filename,
                "size": file_path.stat().st_size,
                "type": file.content_type
            })
        
        return {
            "status": "success",
            "project_id": project_id,
            "project_name": project_name,
            "files_uploaded": len(uploaded_files),
            "files": uploaded_files,
            "next_step": f"POST /api/v1/audit/workflow-a/{project_id}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/audit/workflow-a/{project_id}")
async def run_workflow_a_endpoint(
    project_id: str,
    calculate_resources: bool = False
):
    """
    Spustit celý Workflow A (nový integrovaný)
    
    Args:
        project_id: ID projektu
        calculate_resources: Počítat zdroje (TOV)?
    
    Returns:
        Kompletní audit report
    """
    try:
        # NEW: Use integrated workflow service
        report = await workflow_a.run(
            project_id=project_id,
            calculate_resources=calculate_resources
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "statistics": report["statistics"],
            "download_url": f"/api/v1/download/{project_id}",
            "results_url": f"/api/v1/results/{project_id}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# LEGACY ENDPOINTS (for backward compatibility)
@app.post("/api/v1/parse/{project_id}")
async def parse_project(project_id: str):
    """
    LEGACY: Парсинг документов проекта (Workflow A)
    
    NOTE: Doporučujeme používat /api/v1/audit/workflow-a/{project_id}
    """
    try:
        project_dir = settings.DATA_DIR / "raw" / project_id
        
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Ищем výkaz výměr (Excel или PDF)
        excel_files = list(project_dir.glob("*.xlsx")) + list(project_dir.glob("*.xls"))
        pdf_files = list(project_dir.glob("*.pdf"))
        
        # Загружаем промпт для парсинга
        prompt = prompt_manager.get_parsing_prompt("vykaz")
        
        parsed_data = None
        
        # Пробуем парсить Excel
        if excel_files:
            print(f"📄 Parsing Excel: {excel_files[0].name}")
            parsed_data = claude.parse_excel(excel_files[0], prompt)
        
        # Если нет Excel, пробуем PDF
        elif pdf_files:
            print(f"📄 Parsing PDF: {pdf_files[0].name}")
            parsed_data = claude.parse_pdf(pdf_files[0], prompt)
        
        else:
            raise HTTPException(
                status_code=400, 
                detail="No výkaz výměr found (Excel or PDF)"
            )
        
        # Сохраняем распарсенные данные
        processed_dir = settings.DATA_DIR / "processed" / project_id
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(processed_dir / "positions.json", "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "project_id": project_id,
            "positions_count": parsed_data.get("total_positions", 0),
            "positions": parsed_data.get("positions", []),
            "next_step": f"POST /api/v1/audit/{project_id}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/audit/{project_id}")
async def audit_project_legacy(project_id: str):
    """
    LEGACY: Запуск AUDIT для проекта
    
    NOTE: Doporučujeme používat /api/v1/audit/workflow-a/{project_id}
    """
    # Redirect to new workflow
    return await run_workflow_a_endpoint(project_id, calculate_resources=False)


@app.get("/api/v1/results/{project_id}")
async def get_results(project_id: str):
    """Získat výsledky AUDIT"""
    try:
        results_file = settings.DATA_DIR / "results" / project_id / "audit_report.json"
        
        if not results_file.exists():
            raise HTTPException(status_code=404, detail="Results not found")
        
        import json
        with open(results_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/projects")
async def list_projects():
    """Seznam všech projektů"""
    projects = []
    
    raw_dir = settings.DATA_DIR / "raw"
    if raw_dir.exists():
        for project_dir in raw_dir.iterdir():
            if project_dir.is_dir():
                projects.append({
                    "project_id": project_dir.name,
                    "created_at": datetime.fromtimestamp(
                        project_dir.stat().st_ctime
                    ).isoformat()
                })
    
    return {
        "total": len(projects),
        "projects": projects
    }


@app.get("/api/v1/kb/status")
async def kb_status():
    """Status Knowledge Base"""
    kb_status = {
        "B3_productivity_rates": (settings.KB_DIR / "B3_Pricing" / "productivity_rates.json").exists(),
        "B5_kros": (settings.KB_DIR / "B5_URS_KROS4").exists(),
        "B6_rts": (settings.KB_DIR / "B6_RTS").exists(),
        "B9_pumps": (settings.KB_DIR / "B9_Equipment_Specs" / "pumps.json").exists(),
        "B9_cranes": (settings.KB_DIR / "B9_Equipment_Specs" / "cranes.json").exists(),
        "B9_excavators": (settings.KB_DIR / "B9_Equipment_Specs" / "excavators.json").exists()
    }
    
    return {
        "knowledge_base": kb_status,
        "total_sources": sum(1 for v in kb_status.values() if v),
        "missing_sources": [k for k, v in kb_status.items() if not v]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
