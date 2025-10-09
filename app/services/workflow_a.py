"""
Workflow A: Parse Výkaz Výměr → Audit → Generate Report
FIXED: Proper file format detection and error handling
"""
from pathlib import Path
import logging
from typing import Dict, Any, List
import json

from app.core.claude_client import ClaudeClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class WorkflowA:
    """
    Workflow A: Audit existing výkaz výměr
    
    Steps:
    1. Parse document (Excel/PDF/XML)
    2. Load relevant KB
    3. Audit each position
    4. Generate triage report
    5. Return results with HITL flags
    """
    
    def __init__(self):
        self.claude = ClaudeClient()
        self.kb_dir = settings.KB_DIR
    
    async def run(
        self,
        file_path: Path,
        project_name: str
    ) -> Dict[str, Any]:
        """
        Run complete Workflow A
        
        Args:
            file_path: Path to výkaz výměr file
            project_name: Name of the project
        
        Returns:
            Audit results with positions categorized as GREEN/AMBER/RED
        """
        try:
            logger.info(f"Starting Workflow A for: {file_path}")
            
            # Step 1: Detect file format and parse
            file_format = self._detect_format(file_path)
            logger.info(f"Detected file format: {file_format}")
            
            positions = await self._parse_document(file_path, file_format)
            logger.info(f"Parsed {len(positions)} positions")
            
            if not positions:
                logger.warning("No positions found in document!")
                return {
                    "success": False,
                    "error": "No positions found in document",
                    "positions": []
                }
            
            # Step 2: Load Knowledge Base
            kb_data = self._load_knowledge_base()
            logger.info(f"Loaded KB with {len(kb_data)} categories")
            
            # Step 3: Audit each position
            audit_results = []
            for idx, position in enumerate(positions, 1):
                logger.info(f"Auditing position {idx}/{len(positions)}: {position.get('description', 'N/A')[:50]}")
                
                try:
                    audit_result = await self._audit_position(position, kb_data)
                    audit_results.append(audit_result)
                except Exception as e:
                    logger.error(f"Failed to audit position {idx}: {e}")
                    audit_results.append({
                        "position": position,
                        "status": "ERROR",
                        "error": str(e),
                        "classification": "RED",
                        "hitl_required": True
                    })
            
            # Step 4: Categorize results
            categorized = self._categorize_results(audit_results)
            
            # Step 5: Generate summary
            summary = self._generate_summary(categorized)
            
            logger.info(f"Workflow A completed. GREEN: {len(categorized['green'])}, "
                       f"AMBER: {len(categorized['amber'])}, RED: {len(categorized['red'])}")
            
            return {
                "success": True,
                "project_name": project_name,
                "total_positions": len(positions),
                "summary": summary,
                "positions": categorized,
                "hitl_positions": [p for p in audit_results if p.get('hitl_required')]
            }
        
        except Exception as e:
            logger.error(f"Workflow A failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "positions": []
            }
    
    def _detect_format(self, file_path: Path) -> str:
        """
        Detect file format from extension
        
        Args:
            file_path: Path to file
        
        Returns:
            Format string: 'excel', 'pdf', or 'xml'
        """
        suffix = file_path.suffix.lower()
        
        if suffix in ['.xlsx', '.xls']:
            return 'excel'
        elif suffix == '.pdf':
            return 'pdf'
        elif suffix == '.xml':
            return 'xml'
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    async def _parse_document(
        self,
        file_path: Path,
        file_format: str
    ) -> List[Dict[str, Any]]:
        """
        Parse document based on format
        
        Args:
            file_path: Path to document
            file_format: Format type
        
        Returns:
            List of parsed positions
        """
        try:
            if file_format == 'excel':
                result = self.claude.parse_excel(file_path)
            elif file_format == 'xml':
                result = self.claude.parse_xml(file_path)
            elif file_format == 'pdf':
                result = self.claude.parse_pdf(file_path)
            else:
                raise ValueError(f"Unsupported format: {file_format}")
            
            # Extract positions from result
            positions = result.get('positions', [])
            
            # Validate positions
            valid_positions = []
            for pos in positions:
                if self._is_valid_position(pos):
                    valid_positions.append(pos)
                else:
                    logger.warning(f"Skipping invalid position: {pos}")
            
            return valid_positions
        
        except Exception as e:
            logger.error(f"Failed to parse document: {e}")
            raise
    
    def _is_valid_position(self, position: Dict[str, Any]) -> bool:
        """
        Check if position has minimum required fields
        
        Args:
            position: Position dict
        
        Returns:
            True if valid
        """
        required_fields = ['description']
        return all(field in position and position[field] for field in required_fields)
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """
        Load relevant Knowledge Base data
        
        Returns:
            KB data organized by category
        """
        kb_data = {}
        
        # B1: KROS/ÚRS codes
        b1_path = self.kb_dir / "B1_kros_urs_codes"
        if b1_path.exists():
            kb_data['codes'] = self._load_category(b1_path)
        
        # B2: ČSN Standards
        b2_path = self.kb_dir / "B2_csn_standards"
        if b2_path.exists():
            kb_data['standards'] = self._load_category(b2_path)
        
        # B3: Current Prices
        b3_path = self.kb_dir / "B3_current_prices"
        if b3_path.exists():
            kb_data['prices'] = self._load_category(b3_path)
        
        return kb_data
    
    def _load_category(self, category_path: Path) -> List[Dict[str, Any]]:
        """
        Load all JSON/CSV files from a KB category
        
        Args:
            category_path: Path to category folder
        
        Returns:
            List of loaded data
        """
        data = []
        
        # Load JSON files
        for json_file in category_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        data.extend(content)
                    else:
                        data.append(content)
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")
        
        return data
    
    async def _audit_position(
        self,
        position: Dict[str, Any],
        kb_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Audit single position
        
        Args:
            position: Position to audit
            kb_data: Knowledge Base data
        
        Returns:
            Audit result with classification
        """
        try:
            # Call Claude to audit
            result = self.claude.audit_position(
                position=position,
                knowledge_base=kb_data
            )
            
            # Ensure required fields
            result['position'] = position
            result.setdefault('classification', 'AMBER')
            result.setdefault('hitl_required', False)
            
            # Determine HITL based on classification and config
            if result['classification'] == 'RED' and settings.multi_role.hitl_on_red:
                result['hitl_required'] = True
            
            return result
        
        except Exception as e:
            logger.error(f"Audit failed for position: {e}")
            return {
                "position": position,
                "status": "ERROR",
                "error": str(e),
                "classification": "RED",
                "hitl_required": True
            }
    
    def _categorize_results(
        self,
        audit_results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize audit results by classification
        
        Args:
            audit_results: List of audit results
        
        Returns:
            Dict with 'green', 'amber', 'red' keys
        """
        categorized = {
            'green': [],
            'amber': [],
            'red': []
        }
        
        for result in audit_results:
            classification = result.get('classification', 'AMBER').upper()
            
            if classification == 'GREEN':
                categorized['green'].append(result)
            elif classification == 'RED':
                categorized['red'].append(result)
            else:
                categorized['amber'].append(result)
        
        return categorized
    
    def _generate_summary(
        self,
        categorized: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics
        
        Args:
            categorized: Categorized results
        
        Returns:
            Summary dict
        """
        total = sum(len(v) for v in categorized.values())
        
        return {
            "total_positions": total,
            "green_count": len(categorized['green']),
            "amber_count": len(categorized['amber']),
            "red_count": len(categorized['red']),
            "green_percent": len(categorized['green']) / total * 100 if total > 0 else 0,
            "amber_percent": len(categorized['amber']) / total * 100 if total > 0 else 0,
            "red_percent": len(categorized['red']) / total * 100 if total > 0 else 0
        }


# Create singleton instance for import
workflow_a = WorkflowA()
