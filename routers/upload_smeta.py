# routers/upload_smeta.py
"""
Estimates/BOQ Upload Router
Handles XLSX, XML, CSV, XC4 and other estimate formats
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

# Supported file types for estimates
ALLOWED_SMETA_EXTENSIONS = [".xlsx", ".xls", ".xml", ".csv", ".xc4", ".json", ".ods"]

@router.post("/smeta")
async def upload_estimates(
    files: List[UploadFile] = File(..., description="Сметы и ведомости работ (XLSX, XML, CSV, XC4)"),
    project_name: str = Form("Untitled Project", description="Название проекта"),
    estimate_type: str = Form("general", description="Тип сметы: general, detailed, comparative"),
    auto_analyze: bool = Form(True, description="Автоматически анализировать сметы"),
    language: str = Form("cz", description="Язык анализа: cz, en, ru")
):
    """
    Загрузка смет и ведомостей работ
    
    Поддерживаемые форматы:
    - XLSX/XLS: Excel сметы
    - XML: структурированные сметные данные
    - CSV: табличные данные
    - XC4: формат XChange
    - JSON: JSON структуры смет
    - ODS: OpenDocument Spreadsheet
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Validate file types
        uploaded_files = []
        for file in files:
            if not file.filename:
                continue
                
            file_ext = os.path.splitext(file.filename.lower())[1]
            if file_ext not in ALLOWED_SMETA_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ Недопустимый тип файла: {file.filename}. "
                          f"Разрешены: {', '.join(ALLOWED_SMETA_EXTENSIONS)}"
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
                "type": _detect_estimate_type(file.filename, content),
                "format": file_ext[1:]  # Remove the dot
            })
            
            logger.info(f"📊 Загружена смета: {file.filename}")
        
        if not uploaded_files:
            raise HTTPException(status_code=400, detail="❌ Не загружено ни одного файла")
        
        # Prepare analysis result
        result = {
            "upload_type": "estimates_boq",
            "project_name": project_name,
            "estimate_type": estimate_type,
            "total_files": len(uploaded_files),
            "files": uploaded_files,
            "supported_agents": ["VolumeAgent", "MaterialAgent", "ConcreteAgent", "TOVPlanner"],
            "status": "uploaded_successfully"
        }
        
        # Auto-analyze if requested
        if auto_analyze:
            try:
                analysis_result = await _analyze_estimates(
                    uploaded_files, estimate_type, language
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
        logger.error(f"❌ Ошибка загрузки смет: {e}")
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


def _detect_estimate_type(filename: str, content: bytes) -> str:
    """Определяет тип сметного документа"""
    filename_lower = filename.lower()
    
    # Локальная смета
    if any(keyword in filename_lower for keyword in ["local", "локальная", "локал"]):
        return "local_estimate"
    
    # Объектная смета
    if any(keyword in filename_lower for keyword in ["object", "объект", "общая"]):
        return "object_estimate"
    
    # Сводная смета
    if any(keyword in filename_lower for keyword in ["summary", "сводная", "total"]):
        return "summary_estimate"
    
    # Ведомость объемов работ
    if any(keyword in filename_lower for keyword in ["volume", "объем", "работ", "work"]):
        return "work_volume_statement"
    
    # Ресурсная ведомость
    if any(keyword in filename_lower for keyword in ["resource", "ресурс", "material"]):
        return "resource_statement"
    
    # Сравнительная смета
    if any(keyword in filename_lower for keyword in ["compare", "сравн", "comparison"]):
        return "comparative_estimate"
    
    # По расширению файла
    ext = os.path.splitext(filename_lower)[1]
    if ext in [".xlsx", ".xls"]:
        return "excel_estimate"
    elif ext == ".xml":
        return "xml_estimate"
    elif ext == ".csv":
        return "csv_estimate"
    elif ext == ".xc4":
        return "xchange_estimate"
    elif ext == ".json":
        return "json_estimate"
    
    return "general_estimate"


async def _analyze_estimates(files: List[dict], estimate_type: str, language: str) -> dict:
    """Анализирует сметы с помощью агентов"""
    try:
        # Import agents
        from agents.integration_orchestrator import get_integration_orchestrator
        
        orchestrator = get_integration_orchestrator()
        
        # Use first file as main estimate (can be enhanced to process multiple)
        main_estimate_path = files[0]["path"] if files else None
        
        # Run integrated analysis focusing on volume and materials
        from agents.integration_orchestrator import IntegratedAnalysisRequest
        
        request = IntegratedAnalysisRequest(
            doc_paths=[],  # No docs for estimate-only analysis
            smeta_path=main_estimate_path,
            material_query=None,
            use_claude=True,
            claude_mode="enhancement",
            language=language
        )
        
        analysis_result = await orchestrator.run_integrated_analysis(request)
        
        # Parse estimate data
        estimate_data = await _parse_estimate_files(files)
        
        # Extract relevant parts for estimate analysis
        return {
            "summary": analysis_result.get("summary", {}),
            "volume_analysis": analysis_result.get("volume_analysis", {}),
            "materials_analysis": analysis_result.get("materials_analysis", {}),
            "concrete_analysis": analysis_result.get("concrete_analysis", {}),
            "estimate_data": estimate_data,
            "tov_planning": await _generate_tov_plan(estimate_data),
            "processing_status": analysis_result.get("status", {}),
            "analysis_timestamp": analysis_result.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа смет: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "message": "Не удалось выполнить анализ смет"
        }


async def _parse_estimate_files(files: List[dict]) -> dict:
    """Парсит сметные файлы и извлекает структурированные данные"""
    try:
        # Import parsers
        from parsers.smeta_parser import SmetaParser
        from parsers.xml_smeta_parser import XMLSmetaParser
        
        parsed_data = {
            "total_cost": 0.0,
            "total_volume": 0.0,
            "work_items": [],
            "materials": [],
            "resources": []
        }
        
        for file_info in files:
            file_path = file_info["path"]
            file_format = file_info["format"]
            
            try:
                if file_format in ["xlsx", "xls", "csv"]:
                    parser = SmetaParser()
                    file_data = parser.parse(file_path)
                elif file_format == "xml":
                    parser = XMLSmetaParser()
                    file_data = parser.parse(file_path)
                else:
                    logger.warning(f"⚠️ Неподдерживаемый формат: {file_format}")
                    continue
                
                # Merge parsed data
                if file_data:
                    parsed_data["total_cost"] += file_data.get("total_cost", 0)
                    parsed_data["total_volume"] += file_data.get("total_volume", 0)
                    parsed_data["work_items"].extend(file_data.get("work_items", []))
                    parsed_data["materials"].extend(file_data.get("materials", []))
                    parsed_data["resources"].extend(file_data.get("resources", []))
                    
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга файла {file_info['filename']}: {e}")
                continue
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"❌ Общая ошибка парсинга смет: {e}")
        return {"error": str(e)}


async def _generate_tov_plan(estimate_data: dict) -> dict:
    """Генерирует план ресурсов (Труд-Оборудование-Материалы) и захватки"""
    try:
        # This would integrate with TOVPlanner agent when implemented
        # For now, return placeholder data
        
        work_items = estimate_data.get("work_items", [])
        materials = estimate_data.get("materials", [])
        
        return {
            "work_packages": len(work_items),
            "total_labor_hours": sum(item.get("labor_hours", 0) for item in work_items),
            "equipment_requirements": _extract_equipment_needs(work_items),
            "material_requirements": _extract_material_needs(materials),
            "suggested_zones": _suggest_work_zones(work_items),
            "estimated_duration_days": _estimate_project_duration(work_items),
            "critical_path": _identify_critical_activities(work_items),
            "status": "preliminary_plan_generated"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации TOV плана: {e}")
        return {"error": str(e), "status": "tov_planning_failed"}


def _extract_equipment_needs(work_items: List[dict]) -> List[dict]:
    """Извлекает требования к оборудованию"""
    equipment = []
    for item in work_items:
        if "equipment" in item:
            equipment.extend(item["equipment"])
    return equipment


def _extract_material_needs(materials: List[dict]) -> List[dict]:
    """Извлекает требования к материалам"""
    return materials


def _suggest_work_zones(work_items: List[dict]) -> List[dict]:
    """Предлагает разбивку на захватки"""
    # Simplified zone suggestion based on work types
    zones = []
    current_zone = {"zone_id": 1, "activities": [], "estimated_duration": 0}
    
    for item in work_items:
        current_zone["activities"].append(item.get("name", "Unknown activity"))
        current_zone["estimated_duration"] += item.get("duration", 1)
        
        # Simple logic: create new zone every 10 activities
        if len(current_zone["activities"]) >= 10:
            zones.append(current_zone)
            current_zone = {
                "zone_id": len(zones) + 1, 
                "activities": [], 
                "estimated_duration": 0
            }
    
    if current_zone["activities"]:
        zones.append(current_zone)
    
    return zones


def _estimate_project_duration(work_items: List[dict]) -> int:
    """Оценивает общую продолжительность проекта"""
    total_duration = sum(item.get("duration", 1) for item in work_items)
    # Assume some parallelization
    return max(1, int(total_duration * 0.7))


def _identify_critical_activities(work_items: List[dict]) -> List[str]:
    """Определяет критические работы"""
    # Simplified: identify items with longest duration or high cost
    critical = []
    for item in work_items:
        duration = item.get("duration", 0)
        cost = item.get("cost", 0)
        if duration > 5 or cost > 100000:  # Thresholds
            critical.append(item.get("name", "Unknown"))
    return critical