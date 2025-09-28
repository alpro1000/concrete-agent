# routers/upload_drawings.py
"""
Technical Drawings Upload Router
Handles DWG, DXF, PDF, BIM/IFC files for geometric analysis
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

# Supported file types for drawings
ALLOWED_DRAWING_EXTENSIONS = [".dwg", ".dxf", ".pdf", ".ifc", ".step", ".iges", ".3dm"]

@router.post("/drawings")
async def upload_drawings(
    files: List[UploadFile] = File(..., description="Чертежи (DWG, DXF, PDF, BIM/IFC)"),
    project_name: str = Form("Untitled Project", description="Название проекта"),
    drawing_type: str = Form("general", description="Тип чертежей: architectural, structural, mechanical"),
    scale: Optional[str] = Form(None, description="Масштаб чертежей (например, 1:100)"),
    auto_analyze: bool = Form(True, description="Автоматически анализировать геометрию"),
    extract_volumes: bool = Form(True, description="Извлекать объемы из чертежей"),
    language: str = Form("cz", description="Язык анализа: cz, en, ru")
):
    """
    Загрузка технических чертежей
    
    Поддерживаемые форматы:
    - DWG: AutoCAD чертежи
    - DXF: обменный формат чертежей
    - PDF: чертежи в PDF формате
    - IFC: BIM модели (Industry Foundation Classes)
    - STEP: 3D модели
    - IGES: обменный формат CAD
    - 3DM: Rhino 3D модели
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Validate file types
        uploaded_files = []
        for file in files:
            if not file.filename:
                continue
                
            file_ext = os.path.splitext(file.filename.lower())[1]
            if file_ext not in ALLOWED_DRAWING_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ Недопустимый тип файла: {file.filename}. "
                          f"Разрешены: {', '.join(ALLOWED_DRAWING_EXTENSIONS)}"
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
                "type": _detect_drawing_type(file.filename, content),
                "format": file_ext[1:],  # Remove the dot
                "scale": scale
            })
            
            logger.info(f"📐 Загружен чертеж: {file.filename}")
        
        if not uploaded_files:
            raise HTTPException(status_code=400, detail="❌ Не загружено ни одного файла")
        
        # Prepare analysis result
        result = {
            "upload_type": "technical_drawings",
            "project_name": project_name,
            "drawing_type": drawing_type,
            "scale": scale,
            "total_files": len(uploaded_files),
            "files": uploaded_files,
            "supported_agents": ["DrawingVolumeAgent", "ConcreteAgent", "VolumeAgent"],
            "status": "uploaded_successfully"
        }
        
        # Auto-analyze if requested
        if auto_analyze:
            try:
                analysis_result = await _analyze_drawings(
                    uploaded_files, drawing_type, extract_volumes, language
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
        logger.error(f"❌ Ошибка загрузки чертежей: {e}")
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


def _detect_drawing_type(filename: str, content: bytes) -> str:
    """Определяет тип чертежа"""
    filename_lower = filename.lower()
    
    # Архитектурные чертежи
    if any(keyword in filename_lower for keyword in ["arch", "архит", "plan", "план", "facade", "фасад"]):
        return "architectural_drawing"
    
    # Конструктивные чертежи
    if any(keyword in filename_lower for keyword in ["struct", "конст", "reinf", "арм", "beam", "балка"]):
        return "structural_drawing"
    
    # Инженерные системы
    if any(keyword in filename_lower for keyword in ["mech", "hvac", "отопл", "венти", "электр", "electric"]):
        return "mechanical_drawing"
    
    # Детали
    if any(keyword in filename_lower for keyword in ["detail", "деталь", "node", "узел", "section", "разрез"]):
        return "detail_drawing"
    
    # Схемы
    if any(keyword in filename_lower for keyword in ["scheme", "схема", "diagram", "диаграм"]):
        return "schematic_drawing"
    
    # Генплан
    if any(keyword in filename_lower for keyword in ["site", "генплан", "master", "общий"]):
        return "site_plan"
    
    # По расширению файла
    ext = os.path.splitext(filename_lower)[1]
    if ext == ".dwg":
        return "autocad_drawing"
    elif ext == ".dxf":
        return "dxf_drawing"
    elif ext == ".pdf":
        return "pdf_drawing"
    elif ext == ".ifc":
        return "bim_model"
    elif ext in [".step", ".stp"]:
        return "step_model"
    elif ext in [".iges", ".igs"]:
        return "iges_model"
    elif ext == ".3dm":
        return "rhino_model"
    
    return "general_drawing"


async def _analyze_drawings(files: List[dict], drawing_type: str, extract_volumes: bool, language: str) -> dict:
    """Анализирует чертежи с помощью агентов"""
    try:
        # Import agents
        from agents.integration_orchestrator import get_integration_orchestrator
        
        orchestrator = get_integration_orchestrator()
        
        # Prepare file paths for analysis
        drawing_paths = [f["path"] for f in files]
        
        # Run drawing-specific analysis
        analysis_result = await _run_drawing_analysis(drawing_paths, extract_volumes)
        
        # If volume extraction is requested, run volume analysis
        if extract_volumes:
            volume_result = await _extract_volumes_from_drawings(files)
            analysis_result["volume_extraction"] = volume_result
        
        # Geometric analysis
        geometry_result = await _analyze_geometry(files)
        analysis_result["geometry_analysis"] = geometry_result
        
        return {
            "summary": {
                "total_drawings": len(files),
                "drawing_types": [f["type"] for f in files],
                "formats": [f["format"] for f in files],
                "analysis_type": drawing_type
            },
            "drawing_analysis": analysis_result,
            "geometric_data": geometry_result,
            "material_detection": await _detect_materials_in_drawings(files),
            "concrete_elements": await _detect_concrete_elements(files),
            "processing_status": {"status": "completed"},
            "analysis_timestamp": "2025-01-09T12:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа чертежей: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "message": "Не удалось выполнить анализ чертежей"
        }


async def _run_drawing_analysis(drawing_paths: List[str], extract_volumes: bool) -> dict:
    """Запускает анализ чертежей с помощью DrawingVolumeAgent"""
    try:
        # Import drawing volume agent
        from agents.drawing_volume_agent import get_drawing_volume_agent
        
        agent = get_drawing_volume_agent()
        if not agent:
            return {
                "status": "unavailable",
                "message": "DrawingVolumeAgent недоступен",
                "total_drawings": len(drawing_paths)
            }
        
        # Analyze each drawing
        results = []
        total_volume = 0.0
        
        for path in drawing_paths:
            try:
                if path.lower().endswith('.pdf'):
                    # PDF drawing analysis
                    result = await agent.analyze_pdf_drawing(path)
                elif path.lower().endswith(('.dwg', '.dxf')):
                    # CAD drawing analysis
                    result = await agent.analyze_cad_drawing(path)
                elif path.lower().endswith('.ifc'):
                    # BIM model analysis
                    result = await agent.analyze_bim_model(path)
                else:
                    result = {"error": f"Неподдерживаемый формат: {path}"}
                
                results.append({
                    "file": os.path.basename(path),
                    "analysis": result
                })
                
                # Sum up volumes if available
                if "volume_m3" in result:
                    total_volume += result["volume_m3"]
                    
            except Exception as e:
                logger.error(f"❌ Ошибка анализа чертежа {path}: {e}")
                results.append({
                    "file": os.path.basename(path),
                    "error": str(e)
                })
        
        return {
            "status": "completed",
            "total_drawings": len(drawing_paths),
            "total_volume_m3": total_volume,
            "drawings": results
        }
        
    except Exception as e:
        logger.error(f"❌ Общая ошибка анализа чертежей: {e}")
        return {"error": str(e), "status": "failed"}


async def _extract_volumes_from_drawings(files: List[dict]) -> dict:
    """Извлекает объемы из чертежей"""
    try:
        volume_data = {
            "total_volume_m3": 0.0,
            "total_area_m2": 0.0,
            "elements": []
        }
        
        for file_info in files:
            file_path = file_info["path"]
            file_format = file_info["format"]
            
            # Extract volumes based on file format
            if file_format == "pdf":
                volumes = await _extract_pdf_volumes(file_path)
            elif file_format in ["dwg", "dxf"]:
                volumes = await _extract_cad_volumes(file_path)
            elif file_format == "ifc":
                volumes = await _extract_bim_volumes(file_path)
            else:
                continue
            
            if volumes:
                volume_data["total_volume_m3"] += volumes.get("volume_m3", 0)
                volume_data["total_area_m2"] += volumes.get("area_m2", 0)
                volume_data["elements"].extend(volumes.get("elements", []))
        
        return volume_data
        
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения объемов: {e}")
        return {"error": str(e)}


async def _extract_pdf_volumes(file_path: str) -> dict:
    """Извлекает объемы из PDF чертежей"""
    try:
        # Use pdfplumber for table extraction
        import pdfplumber
        
        volumes = {"volume_m3": 0.0, "area_m2": 0.0, "elements": []}
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Extract tables that might contain volume data
                tables = page.extract_tables()
                for table in tables:
                    # Look for volume/area data in tables
                    volumes.update(_parse_volume_table(table))
        
        return volumes
        
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения объемов из PDF: {e}")
        return {}


async def _extract_cad_volumes(file_path: str) -> dict:
    """Извлекает объемы из CAD файлов"""
    try:
        # This would require ezdxf or similar library
        # For now, return placeholder
        return {
            "volume_m3": 0.0,
            "area_m2": 0.0,
            "elements": [],
            "note": "CAD volume extraction planned for implementation"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения объемов из CAD: {e}")
        return {}


async def _extract_bim_volumes(file_path: str) -> dict:
    """Извлекает объемы из BIM моделей"""
    try:
        # This would require ifcopenshell or similar library
        # For now, return placeholder
        return {
            "volume_m3": 0.0,
            "area_m2": 0.0,
            "elements": [],
            "note": "BIM volume extraction planned for implementation"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения объемов из BIM: {e}")
        return {}


def _parse_volume_table(table: List[List[str]]) -> dict:
    """Парсит таблицу для поиска данных об объемах"""
    volumes = {"volume_m3": 0.0, "area_m2": 0.0, "elements": []}
    
    if not table:
        return volumes
    
    # Look for volume/area keywords in headers
    headers = table[0] if table else []
    volume_col = -1
    area_col = -1
    
    for i, header in enumerate(headers):
        if header and ("объем" in header.lower() or "volume" in header.lower() or "м3" in header.lower()):
            volume_col = i
        elif header and ("площадь" in header.lower() or "area" in header.lower() or "м2" in header.lower()):
            area_col = i
    
    # Extract numeric values
    for row in table[1:]:  # Skip header
        if volume_col >= 0 and volume_col < len(row):
            try:
                vol = float(row[volume_col].replace(",", "."))
                volumes["volume_m3"] += vol
            except (ValueError, AttributeError):
                pass
        
        if area_col >= 0 and area_col < len(row):
            try:
                area = float(row[area_col].replace(",", "."))
                volumes["area_m2"] += area
            except (ValueError, AttributeError):
                pass
    
    return volumes


async def _analyze_geometry(files: List[dict]) -> dict:
    """Анализирует геометрию чертежей"""
    try:
        geometry_data = {
            "total_elements": 0,
            "lines": 0,
            "circles": 0,
            "polygons": 0,
            "text_blocks": 0,
            "dimensions": []
        }
        
        # Placeholder implementation
        # Real implementation would use CAD parsing libraries
        
        return geometry_data
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа геометрии: {e}")
        return {"error": str(e)}


async def _detect_materials_in_drawings(files: List[dict]) -> dict:
    """Определяет материалы на чертежах"""
    try:
        materials = {
            "concrete": [],
            "steel": [],
            "wood": [],
            "brick": [],
            "other": []
        }
        
        # Placeholder implementation
        # Real implementation would analyze drawing annotations and hatching patterns
        
        return materials
        
    except Exception as e:
        logger.error(f"❌ Ошибка определения материалов: {e}")
        return {"error": str(e)}


async def _detect_concrete_elements(files: List[dict]) -> dict:
    """Определяет бетонные элементы на чертежах"""
    try:
        concrete_elements = {
            "foundations": [],
            "columns": [],
            "beams": [],
            "slabs": [],
            "walls": [],
            "stairs": []
        }
        
        # Placeholder implementation
        # Real implementation would analyze structural drawings for concrete elements
        
        return concrete_elements
        
    except Exception as e:
        logger.error(f"❌ Ошибка определения бетонных элементов: {e}")
        return {"error": str(e)}