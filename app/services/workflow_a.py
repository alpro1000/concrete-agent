"""
Workflow A: S výkazem výměr (má seznam práce)
"""
import json
from pathlib import Path
from typing import Dict, List, Any

from app.core.config import settings
from app.core.claude_client import ClaudeClient
from app.core.prompt_manager import prompt_manager
from app.services.audit_service import AuditService
from app.services.resource_calculator import ResourceCalculator


class WorkflowA:
    """
    Workflow A: Má výkaz výměr
    
    Kroky:
    1. Parse výkaz (Excel/PDF)
    2. Extract pozice
    3. AUDIT každé pozice (code/price/norm)
    4. Resource calculation (optional)
    5. Classification (GREEN/AMBER/RED)
    6. Generate report
    """
    
    def __init__(self):
        self.claude = ClaudeClient()
        self.audit_service = AuditService(self.claude)
        self.resource_calculator = ResourceCalculator(self.claude)
    
    async def run(self, project_id: str, calculate_resources: bool = False) -> Dict[str, Any]:
        """
        Spustit celý Workflow A
        
        Args:
            project_id: ID projektu
            calculate_resources: Počítat zdroje (TOV)?
        
        Returns:
            Kompletní report
        """
        print(f"🚀 Starting Workflow A for project: {project_id}")
        
        # Krok 1: Načíst soubory
        project_dir = settings.DATA_DIR / "raw" / project_id
        if not project_dir.exists():
            raise FileNotFoundError(f"Project {project_id} not found")
        
        # Krok 2: Parse výkaz
        print("📄 Step 1: Parsing výkaz výměr...")
        parsed_data = await self._parse_vykaz(project_dir)
        
        # Uložit parsed data
        processed_dir = settings.DATA_DIR / "processed" / project_id
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        with open(processed_dir / "positions.json", "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
        
        positions = parsed_data.get("positions", [])
        print(f"✅ Parsed {len(positions)} positions")
        
        # Krok 3: AUDIT všech pozic
        print("🔍 Step 2: Auditing positions...")
        audit_results = await self._audit_positions(positions, calculate_resources)
        
        # Krok 4: Statistics
        statistics = self._calculate_statistics(audit_results)
        
        # Krok 5: Generate report
        print("📊 Step 3: Generating report...")
        report = {
            "project_id": project_id,
            "workflow": "A",
            "has_vykaz": True,
            "parsed_data": parsed_data.get("document_info", {}),
            "statistics": statistics,
            "positions": audit_results
        }
        
        # Uložit report
        results_dir = settings.DATA_DIR / "results" / project_id
        results_dir.mkdir(parents=True, exist_ok=True)
        
        with open(results_dir / "audit_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Workflow A completed!")
        print(f"   GREEN: {statistics['green']}")
        print(f"   AMBER: {statistics['amber']}")
        print(f"   RED: {statistics['red']}")
        
        return report
    
    async def _parse_vykaz(self, project_dir: Path) -> Dict[str, Any]:
        """Parse výkaz výměr z Excel nebo PDF"""
        
        # Hledej Excel
        excel_files = list(project_dir.glob("*.xlsx")) + list(project_dir.glob("*.xls"))
        
        # Načti prompt
        prompt = prompt_manager.get_parsing_prompt("vykaz")
        
        if excel_files:
            print(f"   Parsing Excel: {excel_files[0].name}")
            return self.claude.parse_excel(excel_files[0], prompt)
        
        # Hledej PDF
        pdf_files = list(project_dir.glob("*.pdf"))
        if pdf_files:
            print(f"   Parsing PDF: {pdf_files[0].name}")
            return self.claude.parse_pdf(pdf_files[0], prompt)
        
        raise FileNotFoundError("No výkaz výměr found (Excel or PDF)")
    
    async def _audit_positions(
        self, 
        positions: List[Dict], 
        calculate_resources: bool
    ) -> List[Dict[str, Any]]:
        """AUDIT všech pozic"""
        
        results = []
        
        for idx, position in enumerate(positions):
            print(f"   [{idx+1}/{len(positions)}] {position.get('description', 'N/A')[:50]}...")
            
            try:
                # AUDIT pozice
                audit_result = await self.audit_service.audit_position(
                    position=position,
                    project_context={}
                )
                
                # Resource calculation (optional)
                if calculate_resources and settings.ENABLE_RESOURCE_CALCULATION:
                    try:
                        resources = await self.resource_calculator.calculate(position)
                        audit_result["resources"] = resources
                    except Exception as e:
                        print(f"      ⚠️  Resource calculation failed: {e}")
                        audit_result["resources"] = None
                
                results.append(audit_result)
            
            except Exception as e:
                print(f"      ❌ AUDIT failed: {e}")
                # Fallback result
                results.append({
                    "position": position,
                    "status": "RED",
                    "error": str(e),
                    "hitl_required": True
                })
        
        return results
    
    def _calculate_statistics(self, audit_results: List[Dict]) -> Dict[str, Any]:
        """Vypočítat statistiky"""
        
        stats = {
            "total": len(audit_results),
            "green": 0,
            "amber": 0,
            "red": 0,
            "hitl_required": 0,
            "total_savings_estimate": 0.0
        }
        
        for result in audit_results:
            status = result.get("status", "AMBER").lower()
            stats[status] = stats.get(status, 0) + 1
            
            if result.get("hitl_required", False):
                stats["hitl_required"] += 1
            
            # Sečíst úspory
            savings = result.get("overall_assessment", {}).get("estimated_savings", 0)
            if savings:
                stats["total_savings_estimate"] += savings
        
        return stats


# Instance pro import
workflow_a = WorkflowA()
