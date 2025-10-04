"""
Site Foreman Agent - Construction Planning and Scheduling (TOV)
Generates technology of work plans, schedules, and resource allocation
"""

from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SiteForemanAgent:
    """
    Site Foreman Agent - TOV Planning
    
    Plans construction activities:
    - Schedule generation
    - TOV (Technology of Work) planning
    - Resource allocation
    - Risk assessment
    """
    
    name = "site_foreman"
    supported_types = [
        "tov_planning",
        "scheduling",
        "construction_plan",
        "resource_data"
    ]
    
    def __init__(self):
        """Initialize Site Foreman Agent"""
        logger.info("SiteForemanAgent initialized")
    
    def _generate_schedule(self, resource_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate construction schedule"""
        schedule = []
        
        labor = resource_data.get("labor", {})
        duration_months = labor.get("estimated_duration_months", 3)
        
        # Define typical construction phases
        phases = [
            {"name": "Site preparation", "duration_ratio": 0.1},
            {"name": "Foundation work", "duration_ratio": 0.15},
            {"name": "Structural work", "duration_ratio": 0.30},
            {"name": "Envelope", "duration_ratio": 0.20},
            {"name": "Interior work", "duration_ratio": 0.15},
            {"name": "Finishing", "duration_ratio": 0.10}
        ]
        
        start_date = datetime.now()
        current_date = start_date
        
        for phase in phases:
            phase_duration = int(duration_months * phase["duration_ratio"] * 30)  # Days
            end_date = current_date + timedelta(days=phase_duration)
            
            schedule.append({
                "phase": phase["name"],
                "start_date": current_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "duration_days": phase_duration
            })
            
            current_date = end_date
        
        return schedule
    
    def _generate_tov_plan(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Technology of Work (TOV) plan"""
        tov = {
            "work_stages": [],
            "resource_allocation": {},
            "safety_measures": [],
            "quality_control": []
        }
        
        # Extract material and labor categories
        materials = resource_data.get("materials", [])
        labor_by_category = resource_data.get("labor", {}).get("by_category", {})
        
        # Generate work stages based on materials
        for material in materials[:10]:  # Limit to first 10
            stage = {
                "activity": material.get("material", "Unknown activity"),
                "quantity": material.get("quantity", 0),
                "unit": material.get("unit", "unit"),
                "resources_needed": []
            }
            tov["work_stages"].append(stage)
        
        # Resource allocation
        for category, hours in labor_by_category.items():
            tov["resource_allocation"][category] = {
                "total_hours": hours,
                "workers_needed": max(1, int(hours / 160))
            }
        
        # Standard safety measures
        tov["safety_measures"] = [
            "Personal protective equipment (PPE) mandatory",
            "Safety barriers around work zones",
            "Regular safety inspections",
            "Emergency evacuation plan"
        ]
        
        # Quality control points
        tov["quality_control"] = [
            "Material quality verification on delivery",
            "Dimensional checks at each phase",
            "Concrete strength testing",
            "Final inspection before handover"
        ]
        
        return tov
    
    def _assess_risks(self, resource_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess project risks"""
        risks = [
            {
                "risk": "Weather delays",
                "probability": "medium",
                "impact": "medium",
                "mitigation": "Plan for weather-protected storage, adjust schedule for season"
            },
            {
                "risk": "Material delivery delays",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Order materials in advance, identify alternative suppliers"
            },
            {
                "risk": "Labor shortage",
                "probability": "low",
                "impact": "high",
                "mitigation": "Maintain relationships with subcontractors, plan recruitment early"
            },
            {
                "risk": "Cost overruns",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Include contingency budget (10-15%), regular cost tracking"
            }
        ]
        
        return risks
    
    async def analyze(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate construction plan and TOV.
        
        Args:
            resource_data: Dictionary containing resource estimates
            
        Returns:
            Dictionary with construction plan:
                - schedule: Project schedule
                - tov_plan: Technology of work plan
                - risks: Risk assessment
        """
        try:
            # Generate schedule
            schedule = self._generate_schedule(resource_data)
            
            # Generate TOV plan
            tov_plan = self._generate_tov_plan(resource_data)
            
            # Assess risks
            risks = self._assess_risks(resource_data)
            
            result = {
                "schedule": schedule,
                "tov_plan": tov_plan,
                "risks": risks,
                "summary": {
                    "total_phases": len(schedule),
                    "total_duration_days": sum(p["duration_days"] for p in schedule),
                    "total_risks_identified": len(risks)
                },
                "processing_metadata": {
                    "agent": self.name,
                    "status": "planned"
                }
            }
            
            logger.info(f"Construction plan generated: {len(schedule)} phases, {len(risks)} risks")
            return result
            
        except Exception as e:
            logger.error(f"Construction planning failed: {e}")
            return {
                "schedule": [],
                "tov_plan": {},
                "risks": [],
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
        return f"SiteForemanAgent(name='{self.name}', supported_types={self.supported_types})"
