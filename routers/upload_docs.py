# routers/upload_docs.py
"""
Project Documents Upload Router
Handles technical specifications, geological materials, PDF/DOCX/TXT documents
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import tempfile
import os
import shutil
import logging
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Supported file types for project documents
ALLOWED_DOCS_EXTENSIONS = [".pdf", ".docx", ".txt", ".doc", ".rtf"]

@router.post("/docs")
async def upload_project_documents(
    files: List[UploadFile] = File(..., description="Проектные документы (TZ, PDF, DOCX, TXT, геология)"),
    project_name: str = Form("Untitled Project", description="Название проекта"),
    auto_analyze: bool = Form(True, description="Автоматически анализировать загруженные документы"),
    language: str = Form("cz", description="Язык анализа: cz, en, ru")
):
    """
    Загрузка проектных документов
    
    Поддерживаемые форматы:
    - PDF: технические задания, геология, спецификации
    - DOCX: текстовые документы проекта
    - TXT: простые текстовые файлы
    - DOC: старые форматы Word
    - RTF: форматированный текст
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Validate file types
        uploaded_files = []
        for file in files:
            if not file.filename:
                continue
                
            file_ext = os.path.splitext(file.filename.lower())[1]
            if file_ext not in ALLOWED_DOCS_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ Недопустимый тип файла: {file.filename}. "
                          f"Разрешены: {', '.join(ALLOWED_DOCS_EXTENSIONS)}"
                )
            
            # Save file to temp directory
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            uploaded_files.append({
                "filename": file.filename,
                "path": file_path,
                "size": len(content),
                "type": _detect_document_type(file.filename, content)
            })
            
            logger.info(f"📄 Загружен проектный документ: {file.filename}")
        
        if not uploaded_files:
            raise HTTPException(status_code=400, detail="❌ Не загружено ни одного файла")
        
        # Prepare analysis result
        result = {
            "upload_type": "project_documents",
            "project_name": project_name,
            "total_files": len(uploaded_files),
            "files": uploaded_files,
            "supported_agents": ["TZDReader", "ConcreteAgent", "MaterialAgent"],
            "status": "uploaded_successfully"
        }
        
        # Auto-analyze if requested
        if auto_analyze:
            try:
                analysis_result = await _analyze_project_documents(
                    uploaded_files, language
                )
                result["analysis"] = analysis_result
                result["status"] = "analyzed_successfully"
            except Exception as e:
                logger.error(f"❌ Ошибка анализа: {e}")
                result["analysis"] = {
                    "error": str(e),
                    "status": "analysis_failed"
                }
                result["status"] = "uploaded_but_analysis_failed"
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки проектных документов: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )
    finally:
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить временные файлы: {e}")


def _detect_document_type(filename: str, content: bytes) -> str:
    """Определяет тип проектного документа"""
    filename_lower = filename.lower()
    
    # Техническое задание
    if any(keyword in filename_lower for keyword in ["tz", "техзадание", "tech", "specification"]):
        return "technical_specification"
    
    # Геология
    if any(keyword in filename_lower for keyword in ["geo", "геология", "грунт", "soil"]):
        return "geological_report"
    
    # Нормативные документы
    if any(keyword in filename_lower for keyword in ["gost", "гост", "снип", "sp", "norm"]):
        return "regulatory_document"
    
    # Проектная документация
    if any(keyword in filename_lower for keyword in ["project", "проект", "план", "plan"]):
        return "project_documentation"
    
    # По расширению файла
    ext = os.path.splitext(filename_lower)[1]
    if ext == ".pdf":
        return "pdf_document"
    elif ext in [".docx", ".doc"]:
        return "word_document"
    elif ext == ".txt":
        return "text_document"
    
    return "general_document"


async def _analyze_project_documents(files: List[dict], language: str) -> dict:
    """Анализирует проектные документы с помощью агентов"""
    try:
        # Import agents
        from agents.integration_orchestrator import get_integration_orchestrator
        from agents.tzd_reader import TZDReader
        
        orchestrator = get_integration_orchestrator()
        
        # Prepare file paths for analysis
        doc_paths = [f["path"] for f in files]
        
        # Run integrated analysis
        from agents.integration_orchestrator import IntegratedAnalysisRequest
        
        request = IntegratedAnalysisRequest(
            doc_paths=doc_paths,
            smeta_path=None,  # No estimate file for docs-only analysis
            material_query=None,
            use_claude=True,
            claude_mode="enhancement",
            language=language
        )
        
        analysis_result = await orchestrator.run_integrated_analysis(request)
        
        # Extract relevant parts for document analysis
        return {
            "summary": analysis_result.get("summary", {}),
            "technical_specification": analysis_result.get("tzd_analysis", {}),
            "concrete_analysis": analysis_result.get("concrete_analysis", {}),
            "materials_found": analysis_result.get("materials_analysis", {}).get("materials", []),
            "processing_status": analysis_result.get("status", {}),
            "analysis_timestamp": analysis_result.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа проектных документов: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "message": "Не удалось выполнить анализ документов"
        }