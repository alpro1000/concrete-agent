"""
Material Analysis Router - Enhanced version using OrchestratorService
"""

import tempfile
import os
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse

from app.core.orchestrator import get_orchestrator_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/materials")
async def analyze_materials_endpoint(
    docs: List[UploadFile] = File(..., description="Construction documents to analyze for materials"),
    material_type: Optional[str] = Form(None, description="Focus on specific material type"),
    include_quantities: Optional[bool] = Form(True, description="Include quantity analysis")
):
    """
    Enhanced material analysis endpoint using OrchestratorService
    
    Features:
    - Comprehensive material identification
    - Quantity extraction
    - Material specification analysis
    - Cross-document consistency validation
    """
    if not docs:
        raise HTTPException(status_code=400, detail="No documents provided")
    
    temp_dir = tempfile.mkdtemp()
    orchestrator = get_orchestrator_service()
    
    try:
        # Save uploaded documents
        file_paths = []
        for doc in docs:
            file_path = os.path.join(temp_dir, doc.filename)
            with open(file_path, "wb") as f:
                content = await doc.read()
                f.write(content)
            file_paths.append(file_path)
            logger.info(f"📄 Uploaded document: {doc.filename}")
        
        # Run comprehensive analysis
        project_result = await orchestrator.run_project(file_paths)
        
        # Extract material-specific findings
        material_findings = project_result.get("findings", {}).get("materials", [])
        technical_requirements = project_result.get("findings", {}).get("technical_requirements", [])
        
        # Aggregate material data
        all_materials = []
        material_conflicts = []
        
        for finding in material_findings:
            if isinstance(finding, dict) and "materials" in finding:
                all_materials.extend(finding["materials"])
        
        # Check for material conflicts if consistency validation was performed
        if "consistency_validation" in project_result:
            material_conflicts = project_result["consistency_validation"]["validation_details"].get("material_conflicts", [])
        
        # Organize results
        result = {
            "total_documents": len(docs),
            "materials_found": all_materials,
            "material_conflicts": material_conflicts,
            "technical_requirements": technical_requirements,
            "consistency_validation": project_result.get("consistency_validation", {}),
            "detailed_analysis": project_result.get("detailed_results", [])
        }
        
        # Filter by material type if specified
        if material_type:
            filtered_materials = [
                mat for mat in all_materials 
                if material_type.lower() in str(mat).lower()
            ]
            result["filtered_materials"] = filtered_materials
            result["filter_applied"] = material_type
        
        logger.info(f"✅ Material analysis completed: {len(all_materials)} materials found")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Material analysis completed successfully",
                "data": result
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Material analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Material analysis failed: {str(e)}"
        )
    
    finally:
        # Cleanup temporary files
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@router.post("/materials/specifications")
async def analyze_material_specifications(
    spec_files: List[UploadFile] = File(..., description="Material specification documents")
):
    """
    Analyze material specification documents for detailed requirements
    """
    if not spec_files:
        raise HTTPException(status_code=400, detail="No specification files provided")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        results = []
        
        # Process each specification file individually
        for spec_file in spec_files:
            file_path = os.path.join(temp_dir, spec_file.filename)
            with open(file_path, "wb") as f:
                content = await spec_file.read()
                f.write(content)
            
            try:
                # Use material agent directly for specifications
                from agents.materials_agent import MaterialAgent
                
                material_agent = MaterialAgent()
                spec_result = await material_agent.analyze_specifications(file_path)
                
                results.append({
                    "file": spec_file.filename,
                    "success": True,
                    "specifications": spec_result.get("specifications", []),
                    "requirements": spec_result.get("requirements", []),
                    "standards": spec_result.get("standards", [])
                })
                
            except Exception as e:
                logger.error(f"Specification analysis failed for {spec_file.filename}: {e}")
                results.append({
                    "file": spec_file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Material specification analysis completed",
                "results": results
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Material specification analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Specification analysis failed: {str(e)}"
        )
    
    finally:
        # Cleanup
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@router.get("/materials/types")
async def get_supported_material_types():
    """
    Get list of supported material types and categories
    """
    try:
        # Define supported material categories
        material_types = {
            "structural": [
                "reinforcement", "steel", "rebar", "wire_mesh",
                "structural_steel", "profiles", "plates"
            ],
            "masonry": [
                "bricks", "blocks", "mortar", "cement",
                "lime", "sand", "aggregates"
            ],
            "insulation": [
                "thermal_insulation", "acoustic_insulation",
                "waterproofing", "vapor_barriers"
            ],
            "finishes": [
                "plaster", "paint", "tiles", "flooring",
                "cladding", "roofing_materials"
            ],
            "technical": [
                "pipes", "fittings", "electrical_materials",
                "mechanical_systems", "fixtures"
            ]
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "material_categories": material_types,
                "total_categories": len(material_types)
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get material types: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve material types"
        )