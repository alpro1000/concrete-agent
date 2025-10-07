"""
Resource Calculator - výpočet zdrojů (TOV) s moduly
"""
import json
from typing import Dict, Any, Optional
from pathlib import Path

from app.core.config import settings
from app.core.claude_client import ClaudeClient
from app.core.prompt_manager import prompt_manager


class ResourceCalculator:
    """
    Resource Calculator s modulárními prompty
    
    Kroky:
    1. Klasifikace typu práce
    2. Načíst příslušný modul (concrete, masonry, earthwork...)
    3. Určit produktivitu (z B3 nebo B9)
    4. Vypočítat zdroje (lidé, technika, materiály)
    5. Určit čas a cenu
    
    Moduly:
    - concrete_work.txt (beton + zachytky logic)
    - masonry_work.txt (zdivo)
    - earthwork.txt (zemní práce)
    - steel_work.txt (ocel)
    - finishing_work.txt (dokončovací)
    """
    
    def __init__(self, claude_client: ClaudeClient):
        self.claude = claude_client
        self.config = settings
        self.prompt_manager = prompt_manager
        
        # Load knowledge base
        self.productivity_rates = self._load_productivity_rates()
        self.equipment_specs = self._load_equipment_specs()
    
    async def calculate(
        self,
        position: Dict[str, Any],
        depth: str = "standard"
    ) -> Dict[str, Any]:
        """
        Vypočítat zdroje pro pozici
        
        Args:
            position: Pozice ze smetá
            depth: Hloubka analýzy (quick/standard/deep)
        
        Returns:
            Resource breakdown (lidé, technika, materiály, čas, cena)
        """
        
        # Krok 1: Klasifikace typu práce
        work_type = self._classify_work_type(position)
        
        print(f"      Resource calc: {work_type}")
        
        # Krok 2: Get resource calculation prompt (with module)
        try:
            resource_prompt = self.prompt_manager.get_resource_calculation_prompt(
                work_type=work_type,
                position=position,
                depth=depth
            )
        except FileNotFoundError:
            # Fallback to master framework only
            print(f"      ⚠️  Module {work_type}_work.txt not found, using master only")
            resource_prompt = self._get_fallback_prompt(position, work_type)
        
        # Add knowledge base context
        kb_context = self._build_kb_context(work_type)
        
        full_prompt = f"{resource_prompt}\n\n# KNOWLEDGE BASE:\n{json.dumps(kb_context, ensure_ascii=False, indent=2)}"
        
        # Krok 3: Call Claude
        try:
            result = self.claude.call(full_prompt)
            
            # Ensure required fields
            if "total_cost_czk" not in result:
                result["total_cost_czk"] = self._estimate_cost(result)
            
            if "total_time_days" not in result:
                result["total_time_days"] = self._estimate_time(result)
            
            if "confidence" not in result:
                result["confidence"] = "MEDIUM"
            
            return result
        
        except Exception as e:
            print(f"      ❌ Resource calculation failed: {e}")
            return {
                "error": str(e),
                "work_type": work_type,
                "total_cost_czk": 0,
                "total_time_days": 0,
                "confidence": "LOW"
            }
    
    def _classify_work_type(self, position: Dict[str, Any]) -> str:
        """
        Klasifikovat typ práce
        
        Returns:
            concrete / masonry / earthwork / steel / finishing / general
        """
        
        description = position.get("description", "").lower()
        
        # Keyword mapping
        keywords = {
            "concrete": [
                "beton", "železobeton", "monolitický", "deska", 
                "sloup", "strop", "základy", "pilíř", "mostovka"
            ],
            "masonry": [
                "zdivo", "cihla", "blok", "příčka", "obklad",
                "dlažba", "porotherm", "ytong", "kámen"
            ],
            "earthwork": [
                "výkop", "zásyp", "terén", "zemní", "bagr",
                "rýpadlo", "úprava terénu"
            ],
            "steel": [
                "ocel", "konstrukce ocelová", "rošt", "svařování",
                "montáž ocelová"
            ],
            "finishing": [
                "omítka", "malba", "nátěr", "podlaha", "tapeta",
                "stěrka", "štuky"
            ]
        }
        
        # Check keywords
        for work_type, kws in keywords.items():
            if any(kw in description for kw in kws):
                return work_type
        
        # Check by code (if available)
        code = position.get("category", "")
        if code:
            code_first = code[:2] if len(code) >= 2 else ""
            code_mapping = {
                "11": "concrete",
                "12": "masonry",
                "21": "earthwork",
                "31": "steel",
                "71": "finishing"
            }
            if code_first in code_mapping:
                return code_mapping[code_first]
        
        return "general"
    
    def _build_kb_context(self, work_type: str) -> Dict[str, Any]:
        """Build knowledge base context for prompt"""
        
        context = {
            "productivity_rates": {},
            "equipment_specs": {},
            "benchmarks": []
        }
        
        # Add relevant productivity rates
        if work_type in self.productivity_rates:
            context["productivity_rates"] = self.productivity_rates.get(work_type, {})
        
        # Add equipment specs
        if work_type == "concrete" and "pumps" in self.equipment_specs:
            context["equipment_specs"]["pumps"] = self.equipment_specs["pumps"]
        
        if work_type == "earthwork" and "excavators" in self.equipment_specs:
            context["equipment_specs"]["excavators"] = self.equipment_specs["excavators"]
        
        # Add cranes (universal)
        if "cranes" in self.equipment_specs:
            context["equipment_specs"]["cranes"] = self.equipment_specs["cranes"]
        
        return context
    
    def _estimate_cost(self, result: Dict[str, Any]) -> float:
        """Estimate total cost from resources"""
        
        total = 0.0
        
        # Labor
        for labor in result.get("resources", {}).get("labor", []):
            total += labor.get("total_czk", 0)
        
        # Equipment
        for equipment in result.get("resources", {}).get("equipment", []):
            total += equipment.get("total_czk", 0)
        
        # Materials
        for material in result.get("resources", {}).get("materials", []):
            total += material.get("total_czk", 0)
        
        # Transport
        for transport in result.get("resources", {}).get("transport", []):
            total += transport.get("total_czk", 0)
        
        return total
    
    def _estimate_time(self, result: Dict[str, Any]) -> float:
        """Estimate total time from resources"""
        
        max_days = 0.0
        
        # Find maximum from labor days
        for labor in result.get("resources", {}).get("labor", []):
            days = labor.get("days", 0)
            if days > max_days:
                max_days = days
        
        # Check equipment days
        for equipment in result.get("resources", {}).get("equipment", []):
            days = equipment.get("days", 0)
            if days > max_days:
                max_days = days
        
        return max_days if max_days > 0 else 1.0
    
    def _get_fallback_prompt(self, position: Dict[str, Any], work_type: str) -> str:
        """Fallback prompt když modul neexistuje"""
        
        position_json = json.dumps(position, ensure_ascii=False, indent=2)
        
        return f"""Calculate resources for this construction work position.

WORK TYPE: {work_type}

POSITION:
{position_json}

Calculate:
1. Labor (type, count, hours/days, cost)
2. Equipment (type, days, cost)
3. Materials (type, quantity, cost)
4. Transport (if needed)
5. Total time (days)
6. Total cost (CZK)

Output as JSON:
{{
  "work_type": "{work_type}",
  "resources": {{
    "labor": [...],
    "equipment": [...],
    "materials": [...],
    "transport": [...]
  }},
  "total_cost_czk": <number>,
  "total_time_days": <number>,
  "confidence": "MEDIUM"
}}
"""
    
    def _load_productivity_rates(self) -> Dict:
        """Load productivity rates"""
        
        rates_file = settings.KB_DIR / "B3_Pricing" / "productivity_rates.json"
        
        if rates_file.exists():
            with open(rates_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        print("⚠️  Productivity rates not found")
        return {}
    
    def _load_equipment_specs(self) -> Dict:
        """Load equipment specifications"""
        
        specs = {}
        
        equipment_dir = settings.KB_DIR / "B9_Equipment_Specs"
        
        if equipment_dir.exists():
            # Load pumps
            pumps_file = equipment_dir / "pumps.json"
            if pumps_file.exists():
                with open(pumps_file, "r", encoding="utf-8") as f:
                    specs["pumps"] = json.load(f)
            
            # Load cranes
            cranes_file = equipment_dir / "cranes.json"
            if cranes_file.exists():
                with open(cranes_file, "r", encoding="utf-8") as f:
                    specs["cranes"] = json.load(f)
            
            # Load excavators
            excavators_file = equipment_dir / "excavators.json"
            if excavators_file.exists():
                with open(excavators_file, "r", encoding="utf-8") as f:
                    specs["excavators"] = json.load(f)
        
        if not specs:
            print("⚠️  Equipment specs not found")
        
        return specs
