"""
Resource Estimator Agent - Material and Labor Resource Estimation
Calculates material quantities, labor hours, and equipment requirements based on project data
"""

from typing import Dict, Any, List, Optional
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class ResourceEstimatorAgent:
    """
    Resource Estimator Agent
    
    Estimates project resources:
    - Material quantities
    - Labor hours
    - Equipment requirements
    - Cost projections
    """
    
    name = "resource_estimator"
    supported_types = [
        "resource_estimation",
        "project_data",
        "boq_result",
        "drawing_result"
    ]
    
    def __init__(self):
        """Initialize Resource Estimator Agent"""
        logger.info("ResourceEstimatorAgent initialized")
        
        # Load labor norms from knowledge base
        self.labor_norms = self._load_labor_norms()
    
    def _load_labor_norms(self) -> Dict[str, float]:
        """Load labor productivity norms"""
        # Default norms (man-hours per unit)
        return {
            "concrete_m3": 2.5,
            "formwork_m2": 1.5,
            "reinforcement_kg": 0.01,
            "excavation_m3": 0.5,
            "masonry_m3": 8.0
        }
    
    def _estimate_materials(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Estimate material quantities"""
        materials = []
        
        # Extract from BOQ if available
        if "boq_data" in project_data and "items" in project_data["boq_data"]:
            for item in project_data["boq_data"]["items"]:
                if item.get("quantity") and item.get("unit"):
                    materials.append({
                        "material": item.get("description", "Unknown"),
                        "quantity": item["quantity"],
                        "unit": item["unit"],
                        "source": "boq"
                    })
        
        # Extract from drawings if available
        if "drawing_data" in project_data and "materials" in project_data["drawing_data"]:
            for material in project_data["drawing_data"]["materials"]:
                materials.append({
                    "material": material.get("name", "Unknown"),
                    "quantity": material.get("quantity", 0),
                    "unit": material.get("unit", "unit"),
                    "source": "drawing"
                })
        
        return materials
    
    def _estimate_labor(self, materials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate labor requirements"""
        total_hours = 0.0
        labor_by_category = {}
        
        for material in materials:
            material_type = material.get("material", "").lower()
            quantity = material.get("quantity", 0)
            
            # Match material to labor norm
            hours = 0.0
            if "concrete" in material_type or "beton" in material_type:
                hours = quantity * self.labor_norms.get("concrete_m3", 2.5)
                category = "concrete_work"
            elif "formwork" in material_type or "bedněn" in material_type:
                hours = quantity * self.labor_norms.get("formwork_m2", 1.5)
                category = "formwork"
            elif "steel" in material_type or "ocel" in material_type or "reinforcement" in material_type:
                hours = quantity * self.labor_norms.get("reinforcement_kg", 0.01)
                category = "reinforcement"
            elif "excavation" in material_type or "výkop" in material_type:
                hours = quantity * self.labor_norms.get("excavation_m3", 0.5)
                category = "excavation"
            elif "brick" in material_type or "cihla" in material_type or "masonry" in material_type:
                hours = quantity * self.labor_norms.get("masonry_m3", 8.0)
                category = "masonry"
            else:
                hours = quantity * 1.0  # Default norm
                category = "other"
            
            total_hours += hours
            labor_by_category[category] = labor_by_category.get(category, 0) + hours
        
        return {
            "total_hours": round(total_hours, 2),
            "by_category": labor_by_category,
            "estimated_workers": max(1, int(total_hours / 160)),  # Assuming 160 hours/month
            "estimated_duration_months": round(total_hours / 160, 1)
        }
    
    def _estimate_equipment(self, materials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Estimate equipment requirements"""
        equipment = []
        
        # Simple heuristics for equipment needs
        has_concrete = any("concrete" in m.get("material", "").lower() or "beton" in m.get("material", "").lower() 
                          for m in materials)
        has_excavation = any("excavation" in m.get("material", "").lower() or "výkop" in m.get("material", "").lower() 
                            for m in materials)
        has_lifting = any("steel" in m.get("material", "").lower() or "ocel" in m.get("material", "").lower() 
                         for m in materials)
        
        if has_concrete:
            equipment.append({"type": "concrete_mixer", "quantity": 1, "unit": "unit"})
            equipment.append({"type": "concrete_pump", "quantity": 1, "unit": "unit"})
        
        if has_excavation:
            equipment.append({"type": "excavator", "quantity": 1, "unit": "unit"})
            equipment.append({"type": "dump_truck", "quantity": 2, "unit": "unit"})
        
        if has_lifting:
            equipment.append({"type": "crane", "quantity": 1, "unit": "unit"})
        
        return equipment
    
    async def analyze(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate resources for a project.
        
        Args:
            project_data: Dictionary containing BOQ data, drawing data, or other project info
            
        Returns:
            Dictionary with resource estimates:
                - materials: Material quantities
                - labor: Labor hour estimates
                - equipment: Equipment requirements
        """
        try:
            # Estimate materials
            materials = self._estimate_materials(project_data)
            
            # Estimate labor
            labor = self._estimate_labor(materials)
            
            # Estimate equipment
            equipment = self._estimate_equipment(materials)
            
            result = {
                "materials": materials,
                "labor": labor,
                "equipment": equipment,
                "summary": {
                    "total_materials": len(materials),
                    "total_labor_hours": labor["total_hours"],
                    "total_equipment_items": len(equipment)
                },
                "processing_metadata": {
                    "agent": self.name,
                    "status": "estimated"
                }
            }
            
            logger.info(f"Resources estimated: {len(materials)} materials, {labor['total_hours']} labor hours")
            return result
            
        except Exception as e:
            logger.error(f"Resource estimation failed: {e}")
            return {
                "materials": [],
                "labor": {"total_hours": 0},
                "equipment": [],
                "error": str(e),
                "processing_metadata": {
                    "agent": self.name,
                    "status": "failed"
                }
            }
    
    def supports_type(self, file_type: str) -> bool:
        """Check if this agent supports a given file type"""
        return file_type.lower() in [t.lower() for t in self.supported_types]
    
    def __repr__(self) -> str:
        """String representation of the agent"""
        return f"ResourceEstimatorAgent(name='{self.name}', supported_types={self.supported_types})"
