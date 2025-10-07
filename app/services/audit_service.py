"""
Audit Service - AUDIT логика с multi-role system
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.core.claude_client import ClaudeClient
from app.core.prompt_manager import prompt_manager


class AuditService:
    """
    AUDIT service s multi-role expertízou
    
    3 checks:
    1. CODE MATCHING - hledá kód v KROS/RTS
    2. PRICE CHECK - porovnává s trhem
    3. NORM VALIDATION - kontroluje ČSN
    
    Optional: Multi-role (SME/ARCH/ENG/SUP)
    """
    
    def __init__(self, claude_client: ClaudeClient):
        self.claude = claude_client
        self.config = settings
        self.prompt_manager = prompt_manager
        
        # Load knowledge base (simplified for now)
        self.kros_db = self._load_kros_database()
        self.csn_standards = self._load_csn_standards()
        self.productivity_rates = self._load_productivity_rates()
    
    async def audit_position(
        self,
        position: Dict[str, Any],
        project_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        AUDIT jedné pozice
        
        Args:
            position: Pozice ze smetá
            project_context: Kontext projektu
        
        Returns:
            Audit result s classification
        """
        
        # Krok 1: Preliminary classification
        classification = self._classify_position(position)
        
        # Krok 2: Get audit prompt (with adaptive multi-role)
        audit_prompt = self.prompt_manager.get_audit_prompt(
            position=position,
            kros_database=self.kros_db,
            csn_standards=self.csn_standards,
            classification=classification
        )
        
        # Krok 3: Call Claude
        try:
            audit_result = self.claude.call(audit_prompt)
            
            # Add original position
            audit_result["position"] = position
            
            # Ensure status field
            if "status" not in audit_result:
                audit_result["status"] = classification
            
        except Exception as e:
            # Fallback na chybu
            audit_result = {
                "position": position,
                "status": "RED",
                "error": str(e),
                "code_match": {"found": False, "confidence": 0.0},
                "price_check": {"status": "UNKNOWN"},
                "norm_validation": {"compliant": False, "issues": [str(e)]},
                "overall_assessment": {
                    "classification": "RED",
                    "confidence": 0.0,
                    "main_issues": ["AUDIT failed", str(e)]
                },
                "hitl_required": True,
                "hitl_reason": f"AUDIT error: {str(e)}"
            }
        
        # Krok 4: Check HITL triggers
        audit_result["hitl_required"] = self._requires_hitl(
            audit_result, 
            classification
        )
        
        if audit_result["hitl_required"] and "hitl_reason" not in audit_result:
            audit_result["hitl_reason"] = self._get_hitl_reason(audit_result)
        
        return audit_result
    
    def _classify_position(self, position: Dict[str, Any]) -> str:
        """
        Preliminary classification (před AUDIT)
        
        Na základě:
        - Má cenu? (pokud ne → AMBER minimum)
        - Je popis jasný?
        - Známý typ práce?
        
        Returns:
            GREEN/AMBER/RED
        """
        
        # Check data completeness
        has_price = position.get("unit_price") is not None
        has_description = bool(position.get("description"))
        has_quantity = position.get("quantity", 0) > 0
        
        if not has_description or not has_quantity:
            return "RED"
        
        if not has_price:
            return "AMBER"
        
        # Check if we know this work type
        description = position.get("description", "").lower()
        
        # Common keywords
        known_keywords = [
            "beton", "zdivo", "výkop", "cihla", "ocel", 
            "omítka", "izolace", "dlažba", "obklad"
        ]
        
        has_known_keyword = any(kw in description for kw in known_keywords)
        
        if has_known_keyword:
            return "GREEN"
        else:
            return "AMBER"
    
    def _requires_hitl(
        self, 
        result: Dict[str, Any], 
        classification: str
    ) -> bool:
        """
        Check if HITL is required based on multi-role config
        
        HITL triggers:
        1. RED classification → always
        2. Price difference >15%
        3. Code confidence <0.5
        4. Norm violations
        5. Multi-role conflicts (if enabled)
        """
        
        if not settings.multi_role.enabled:
            # Simple triggers
            if classification == "RED":
                return True
            
            if result.get("status") == "RED":
                return True
            
            return False
        
        # Multi-role HITL triggers
        
        # 1. Always HITL for RED
        if classification == "RED" and settings.multi_role.hitl_on_red:
            return True
        
        # 2. Price threshold exceeded
        price_check = result.get("price_check", {})
        price_diff = price_check.get("difference_pct", 0)
        if abs(price_diff) > settings.multi_role.hitl_price_threshold * 100:
            return True
        
        # 3. Low code confidence
        code_match = result.get("code_match", {})
        if code_match.get("confidence", 1.0) < 0.5:
            return True
        
        # 4. Norm violations
        norm_validation = result.get("norm_validation", {})
        if not norm_validation.get("compliant", True):
            return True
        
        # 5. Multi-role conflicts
        if "multi_role_review" in result:
            disagreements = result["multi_role_review"].get("disagreements", [])
            for conflict in disagreements:
                if conflict.get("priority_level") in settings.multi_role.hitl_on_conflict_levels:
                    return True
        
        return False
    
    def _get_hitl_reason(self, result: Dict[str, Any]) -> str:
        """Get human-readable HITL reason"""
        
        reasons = []
        
        if result.get("status") == "RED":
            reasons.append("RED classification")
        
        price_check = result.get("price_check", {})
        price_diff = price_check.get("difference_pct", 0)
        if abs(price_diff) > 15:
            reasons.append(f"Price difference {price_diff:.1f}%")
        
        code_match = result.get("code_match", {})
        if code_match.get("confidence", 1.0) < 0.5:
            reasons.append("Low code confidence")
        
        norm_validation = result.get("norm_validation", {})
        if not norm_validation.get("compliant", True):
            reasons.append("Norm violations")
        
        if not reasons:
            reasons.append("Manual review recommended")
        
        return ", ".join(reasons)
    
    def _load_kros_database(self) -> List[Dict]:
        """Load KROS database (sample for now)"""
        
        kros_file = settings.KB_DIR / "B5_URS_KROS4" / "kros_sample.json"
        
        if kros_file.exists():
            with open(kros_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("positions", [])
        
        # Fallback: prázdná databáze
        print("⚠️  KROS database not found, using empty database")
        return []
    
    def _load_csn_standards(self) -> List[Dict]:
        """Load ČSN standards (sample for now)"""
        
        csn_file = settings.KB_DIR / "B1_Normy_Standardy" / "csn_en_206.json"
        
        if csn_file.exists():
            with open(csn_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # Fallback: prázdná databáze
        print("⚠️  ČSN database not found, using empty database")
        return []
    
    def _load_productivity_rates(self) -> Dict:
        """Load productivity rates"""
        
        rates_file = settings.KB_DIR / "B3_Pricing" / "productivity_rates.json"
        
        if rates_file.exists():
            with open(rates_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        print("⚠️  Productivity rates not found")
        return {}
