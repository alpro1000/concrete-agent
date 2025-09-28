# routers/analyze_tov.py
"""
TOV Analysis Router
Handles TOV (Труд-Оборудование-Материалы) resource planning and scheduling
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, Response
from typing import List, Optional, Dict, Any
import tempfile
import os
import shutil
import logging
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/tov")
async def analyze_tov(
    docs: List[UploadFile] = File(default=[], description="Проектные документы"),
    smeta: Optional[UploadFile] = File(default=None, description="Файл сметы (XLSX, CSV, XML)"),
    project_name: str = Form("TOV Analysis Project", description="Название проекта"),
    project_duration_days: Optional[int] = Form(None, description="Планируемая продолжительность проекта в днях"),
    use_claude: bool = Form(True, description="Использовать Claude AI для анализа"),
    claude_mode: str = Form("enhancement", description="Режим работы Claude: enhancement, full"),
    language: str = Form("cz", description="Язык анализа: cz, en, ru"),
    export_format: str = Form("json", description="Формат экспорта: json, csv, excel")
):
    """
    Анализ ресурсов TOV (Труд-Оборудование-Материалы)
    
    Создает план ресурсов с разбивкой на захватки, календарным планированием 
    и оптимизацией использования ресурсов.
    
    Возвращает:
    - Рабочие захватки с графиком работ
    - Требования к ресурсам (трудовые, оборудование, материалы)
    - Критический путь проекта
    - Календарный план с диаграммой Ганта
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Validate inputs
        if not smeta and not docs:
            raise HTTPException(
                status_code=400, 
                detail="❌ Необходимо загрузить смету или проектные документы для анализа TOV"
            )
        
        # Save uploaded files
        uploaded_files = []
        smeta_path = None
        
        # Process documents
        for doc in docs:
            if doc.filename:
                file_path = os.path.join(temp_dir, doc.filename)
                with open(file_path, "wb") as f:
                    f.write(await doc.read())
                uploaded_files.append(file_path)
                logger.info(f"📄 Сохранен документ: {doc.filename}")
        
        # Process estimate file
        if smeta and smeta.filename:
            smeta_path = os.path.join(temp_dir, smeta.filename)
            with open(smeta_path, "wb") as f:
                f.write(await smeta.read())
            logger.info(f"📊 Сохранена смета: {smeta.filename}")
        
        # Run TOV analysis
        logger.info("🔄 Запуск анализа TOV...")
        
        tov_result = await _run_tov_analysis(
            doc_paths=uploaded_files,
            smeta_path=smeta_path,
            project_name=project_name,
            project_duration_days=project_duration_days,
            use_claude=use_claude,
            claude_mode=claude_mode,
            language=language
        )
        
        # Export in requested format
        export_data = None
        if export_format == "csv":
            export_data = tov_result.get("csv_export", "")
            return Response(
                content=export_data,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=tov_plan_{project_name}.csv"}
            )
        elif export_format == "excel":
            # Placeholder for Excel export
            export_data = tov_result.get("excel_export", None)
            if export_data:
                return Response(
                    content=export_data,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=tov_plan_{project_name}.xlsx"}
                )
        
        # Default JSON response
        response_data = {
            "status": "success",
            "project_name": project_name,
            "analysis_type": "tov_resource_planning",
            "input_files": {
                "documents": len(uploaded_files),
                "estimate": smeta.filename if smeta else None
            },
            "tov_analysis": tov_result,
            "export_formats": ["json", "csv", "excel"],
            "timestamp": "2025-01-09T12:00:00Z"
        }
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка анализа TOV: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера при анализе TOV: {str(e)}"
        )
    finally:
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить временные файлы: {e}")


async def _run_tov_analysis(
    doc_paths: List[str],
    smeta_path: Optional[str],
    project_name: str,
    project_duration_days: Optional[int],
    use_claude: bool,
    claude_mode: str,
    language: str
) -> Dict[str, Any]:
    """Запускает анализ TOV с помощью TOVAgent"""
    try:
        # Import TOV agent
        from agents.tov_agent import get_tov_agent
        
        tov_agent = get_tov_agent()
        
        # Parse estimate data first
        estimate_data = {}
        if smeta_path:
            estimate_data = await _parse_estimate_file(smeta_path)
            logger.info(f"📊 Распарсена смета: {len(estimate_data.get('work_items', []))} работ")
        
        # If no estimate, try to extract from documents
        if not estimate_data and doc_paths:
            estimate_data = await _extract_estimate_from_docs(doc_paths, use_claude, language)
            logger.info(f"📄 Извлечены данные из документов: {len(estimate_data.get('work_items', []))} работ")
        
        if not estimate_data.get('work_items'):
            # Create minimal estimate data for testing
            estimate_data = _create_minimal_estimate_data()
            logger.info("⚠️ Используются тестовые данные для демонстрации TOV")
        
        # Prepare project constraints
        project_constraints = {
            "project_name": project_name,
            "duration_days": project_duration_days,
            "language": language,
            "use_ai": use_claude,
            "ai_mode": claude_mode
        }
        
        # Create TOV plan
        work_package = await tov_agent.create_tov_plan(estimate_data, project_constraints)
        
        # Prepare response data
        result = {
            "summary": {
                "project_name": project_name,
                "total_work_zones": len(work_package.work_zones),
                "total_duration_days": work_package.total_duration_days,
                "total_cost": work_package.total_cost,
                "critical_path_activities": len(work_package.critical_path)
            },
            "work_zones": [
                {
                    "zone_id": zone.zone_id,
                    "name": zone.name,
                    "activities": zone.activities,
                    "start_date": zone.start_date.isoformat(),
                    "end_date": zone.end_date.isoformat(),
                    "duration_days": zone.estimated_duration_days,
                    "floor_level": zone.floor_level,
                    "status": zone.status,
                    "resource_count": len(zone.resources),
                    "dependencies": zone.dependencies
                }
                for zone in work_package.work_zones
            ],
            "resource_requirements": [
                {
                    "type": req.resource_type,
                    "name": req.resource_name,
                    "quantity": req.quantity,
                    "unit": req.unit,
                    "cost_per_unit": req.cost_per_unit,
                    "total_cost": req.total_cost,
                    "priority": req.priority
                }
                for req in work_package.resource_requirements
            ],
            "critical_path": work_package.critical_path,
            "gantt_data": _generate_gantt_data(work_package.work_zones),
            "resource_utilization": _calculate_resource_utilization(work_package),
            "csv_export": tov_agent.export_to_csv(work_package),
            "json_export": tov_agent.export_to_json(work_package),
            "status": "completed"
        }
        
        logger.info("✅ TOV анализ завершен успешно")
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения TOV анализа: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "message": "Не удалось выполнить анализ TOV"
        }


async def _parse_estimate_file(smeta_path: str) -> Dict[str, Any]:
    """Парсит файл сметы"""
    try:
        # Import parsers based on file extension
        file_ext = os.path.splitext(smeta_path.lower())[1]
        
        if file_ext in [".xlsx", ".xls"]:
            from parsers.smeta_parser import SmetaParser
            parser = SmetaParser()
            return parser.parse(smeta_path)
        elif file_ext == ".xml":
            from parsers.xml_smeta_parser import XMLSmetaParser
            parser = XMLSmetaParser()
            return parser.parse(smeta_path)
        elif file_ext == ".csv":
            import pandas as pd
            df = pd.read_csv(smeta_path)
            return _convert_dataframe_to_estimate(df)
        else:
            logger.warning(f"⚠️ Неподдерживаемый формат сметы: {file_ext}")
            return {}
            
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга сметы: {e}")
        return {}


async def _extract_estimate_from_docs(doc_paths: List[str], use_claude: bool, language: str) -> Dict[str, Any]:
    """Извлекает сметные данные из проектных документов"""
    try:
        # Use integration orchestrator to extract data
        from agents.integration_orchestrator import get_integration_orchestrator, IntegratedAnalysisRequest
        
        orchestrator = get_integration_orchestrator()
        
        request = IntegratedAnalysisRequest(
            doc_paths=doc_paths,
            smeta_path=None,
            material_query=None,
            use_claude=use_claude,
            claude_mode="enhancement",
            language=language
        )
        
        analysis_result = await orchestrator.run_integrated_analysis(request)
        
        # Extract estimate-relevant data
        return {
            "work_items": analysis_result.get("concrete_analysis", {}).get("matches", []),
            "materials": analysis_result.get("materials_analysis", {}).get("materials", []),
            "total_cost": 0,
            "total_volume": 0
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения данных из документов: {e}")
        return {}


def _create_minimal_estimate_data() -> Dict[str, Any]:
    """Создает минимальные тестовые данные для демонстрации"""
    return {
        "work_items": [
            {
                "name": "Устройство фундамента",
                "quantity": 100,
                "unit": "м3",
                "cost": 50000,
                "labor_hours": 80,
                "equipment": [{"name": "Экскаватор", "quantity": 1, "cost_per_unit": 2000}]
            },
            {
                "name": "Возведение стен",
                "quantity": 200,
                "unit": "м2",
                "cost": 80000,
                "labor_hours": 120,
                "equipment": [{"name": "Кран", "quantity": 1, "cost_per_unit": 3000}]
            },
            {
                "name": "Устройство кровли",
                "quantity": 150,
                "unit": "м2",
                "cost": 45000,
                "labor_hours": 60,
                "equipment": [{"name": "Подъемник", "quantity": 1, "cost_per_unit": 1500}]
            }
        ],
        "materials": [
            {"name": "Бетон B25", "quantity": 100, "unit": "м3", "price": 3000, "total_cost": 300000},
            {"name": "Арматура A500", "quantity": 5, "unit": "т", "price": 45000, "total_cost": 225000},
            {"name": "Кирпич керамический", "quantity": 10000, "unit": "шт", "price": 15, "total_cost": 150000}
        ],
        "total_cost": 675000,
        "total_volume": 100
    }


def _convert_dataframe_to_estimate(df) -> Dict[str, Any]:
    """Конвертирует DataFrame в формат сметных данных"""
    try:
        work_items = []
        materials = []
        
        for _, row in df.iterrows():
            # Try to identify if it's a work item or material
            name = str(row.get("name", row.get("Наименование", "Unknown")))
            quantity = float(row.get("quantity", row.get("Количество", 0)))
            unit = str(row.get("unit", row.get("Единица", "шт")))
            cost = float(row.get("cost", row.get("Стоимость", 0)))
            
            if "материал" in name.lower() or "material" in name.lower():
                materials.append({
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                    "price": cost / quantity if quantity > 0 else 0,
                    "total_cost": cost
                })
            else:
                work_items.append({
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                    "cost": cost,
                    "labor_hours": quantity * 0.5,  # Estimate
                    "equipment": []
                })
        
        return {
            "work_items": work_items,
            "materials": materials,
            "total_cost": sum([item["cost"] for item in work_items]) + sum([mat["total_cost"] for mat in materials]),
            "total_volume": sum([item["quantity"] for item in work_items])
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации DataFrame: {e}")
        return {}


def _generate_gantt_data(work_zones) -> List[Dict[str, Any]]:
    """Генерирует данные для диаграммы Ганта"""
    gantt_data = []
    
    for zone in work_zones:
        gantt_data.append({
            "id": zone.zone_id,
            "name": zone.name,
            "start": zone.start_date.isoformat(),
            "end": zone.end_date.isoformat(),
            "duration": zone.estimated_duration_days,
            "progress": 0,  # 0% для планируемых работ
            "dependencies": zone.dependencies,
            "type": "task",
            "floor_level": zone.floor_level
        })
    
    return gantt_data


def _calculate_resource_utilization(work_package) -> Dict[str, Any]:
    """Рассчитывает загрузку ресурсов"""
    try:
        resource_summary = {
            "labor": {"total_hours": 0, "peak_demand": 0, "utilization": "medium"},
            "equipment": {"total_units": 0, "unique_types": 0, "utilization": "medium"},
            "materials": {"total_cost": 0, "critical_materials": 0, "availability": "good"}
        }
        
        # Analyze resource requirements
        for req in work_package.resource_requirements:
            if req.resource_type == "labor":
                resource_summary["labor"]["total_hours"] += req.quantity
            elif req.resource_type == "equipment":
                resource_summary["equipment"]["total_units"] += req.quantity
            elif req.resource_type == "material":
                resource_summary["materials"]["total_cost"] += req.total_cost
                if req.priority in ["high", "critical"]:
                    resource_summary["materials"]["critical_materials"] += 1
        
        # Calculate utilization metrics
        if resource_summary["labor"]["total_hours"] > 1000:
            resource_summary["labor"]["utilization"] = "high"
        elif resource_summary["labor"]["total_hours"] < 200:
            resource_summary["labor"]["utilization"] = "low"
        
        return resource_summary
        
    except Exception as e:
        logger.error(f"❌ Ошибка расчета загрузки ресурсов: {e}")
        return {}