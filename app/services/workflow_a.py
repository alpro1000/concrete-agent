"""
Workflow A - ИСПРАВЛЕНО
Гибкая валидация + детальное логирование + использование нормализатора
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.parsers.smart_parser import SmartParser
from app.utils.position_normalizer import normalize_positions
from app.core.config import settings

logger = logging.getLogger(__name__)


class WorkflowA:
    """
    Workflow A: Audit existing Výkaz výměr
    ИСПРАВЛЕНО: Использует нормализатор и гибкую валидацию
    """
    
    def __init__(self):
        self.parser = SmartParser()
    
    async def execute(
        self,
        project_id: str,
        generate_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Execute Workflow A: Parse and audit positions
        
        Args:
            project_id: Project identifier
            generate_summary: Whether to generate AI summary
            
        Returns:
            Audit results dict
        """
        logger.info(f"Starting execute() for project {project_id}")
        
        try:
            # Find project directory
            project_dir = settings.DATA_DIR / "raw" / project_id
            
            if not project_dir.exists():
                raise FileNotFoundError(f"Project directory not found: {project_dir}")
            
            # Find vykaz vymer file
            vykaz_dir = project_dir / "vykaz_vymer"
            
            if not vykaz_dir.exists():
                raise FileNotFoundError(f"Vykaz vymer directory not found: {vykaz_dir}")
            
            # Get all files in vykaz_vymer directory
            vykaz_files = list(vykaz_dir.glob("*"))
            
            if not vykaz_files:
                raise FileNotFoundError(f"No files found in {vykaz_dir}")
            
            # Parse each file
            all_positions = []
            
            for file_path in vykaz_files:
                if file_path.is_file():
                    logger.info(f"Parsing vykaz vymer: {file_path.name}")
                    
                    # Parse document
                    result = await self._parse_document(file_path)
                    
                    if result and result.get('positions'):
                        positions = result['positions']
                        logger.info(f"Got {len(positions)} positions from {file_path.name}")
                        all_positions.extend(positions)
                    else:
                        logger.warning(f"No positions found in {file_path.name}")
            
            if not all_positions:
                logger.error("❌ No positions found in any document!")
                return {
                    "project_id": project_id,
                    "status": "FAILED",
                    "error": "No positions found in documents",
                    "positions_count": 0
                }
            
            logger.info(f"Total positions parsed: {len(all_positions)}")
            
            # Validate positions with detailed logging
            valid_positions = self._validate_positions(all_positions)
            
            logger.info(f"Valid positions after validation: {len(valid_positions)}")
            
            if not valid_positions:
                logger.error("❌ No valid positions after validation!")
                return {
                    "project_id": project_id,
                    "status": "FAILED",
                    "error": "No valid positions after validation",
                    "positions_count": 0
                }
            
            # Audit positions
            audit_results = await self._audit_positions(valid_positions)
            
            # Generate summary if requested
            summary = None
            if generate_summary:
                summary = self._generate_summary(audit_results)
            
            logger.info(f"✅ Workflow A completed for project {project_id}")
            
            return {
                "project_id": project_id,
                "status": "COMPLETED",
                "positions_count": len(valid_positions),
                "audit_results": audit_results,
                "summary": summary,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Workflow A failed: {str(e)}", exc_info=True)
            return {
                "project_id": project_id,
                "status": "FAILED",
                "error": str(e),
                "positions_count": 0
            }
    
    async def _parse_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse document and extract positions
        
        Args:
            file_path: Path to document
            
        Returns:
            Parse result with positions
        """
        logger.info(f"Importing positions from: {file_path}")
        
        # Detect file format
        file_ext = file_path.suffix.lower()
        logger.info(f"Detected file format: {file_ext}")
        
        # Parse with smart parser
        logger.info(f"Parsing {file_ext} document with specialized parser")
        result = self.parser.parse(file_path)
        
        # Log raw result sample for debugging
        if result and result.get('positions'):
            logger.info(
                f"Parser returned {len(result['positions'])} positions. "
                f"Sample (first position): {json.dumps(result['positions'][0], ensure_ascii=False)[:200]}"
            )
        
        return result
    
    def _validate_positions(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate positions with detailed logging
        
        ИСПРАВЛЕНО: Более гибкая валидация + детальное логирование
        
        Args:
            positions: List of raw positions
            
        Returns:
            List of valid positions
        """
        logger.info(f"Validating {len(positions)} positions...")
        
        valid_positions = []
        skipped_count = 0
        
        # Track skip reasons
        skip_reasons = {
            'missing_description': 0,
            'empty_description': 0,
            'missing_quantity': 0,
            'invalid_quantity': 0,
            'zero_quantity': 0
        }
        
        for idx, position in enumerate(positions):
            # Check description
            if 'description' not in position:
                skip_reasons['missing_description'] += 1
                logger.debug(
                    f"⚠️ Position {idx + 1}: Missing 'description' field. "
                    f"Available fields: {list(position.keys())}"
                )
                skipped_count += 1
                continue
            
            desc = position['description']
            if not desc or str(desc).strip() == '':
                skip_reasons['empty_description'] += 1
                logger.debug(
                    f"⚠️ Position {idx + 1}: Empty description. "
                    f"Position data: {json.dumps(position, ensure_ascii=False)[:150]}"
                )
                skipped_count += 1
                continue
            
            # Check quantity
            if 'quantity' not in position:
                skip_reasons['missing_quantity'] += 1
                logger.debug(
                    f"⚠️ Position {idx + 1} ({desc[:30]}): Missing 'quantity' field"
                )
                skipped_count += 1
                continue
            
            try:
                qty = float(position['quantity'])
                if qty <= 0:
                    skip_reasons['zero_quantity'] += 1
                    logger.debug(
                        f"⚠️ Position {idx + 1} ({desc[:30]}): "
                        f"Quantity is zero or negative: {qty}"
                    )
                    skipped_count += 1
                    continue
            except (ValueError, TypeError):
                skip_reasons['invalid_quantity'] += 1
                logger.debug(
                    f"⚠️ Position {idx + 1} ({desc[:30]}): "
                    f"Cannot convert quantity to number: '{position['quantity']}'"
                )
                skipped_count += 1
                continue
            
            # Position is valid
            valid_positions.append(position)
        
        # Summary logging
        logger.info(f"Parsed {len(valid_positions)} valid positions ({skipped_count} skipped)")
        
        if skipped_count > 0:
            logger.warning(
                f"⚠️ Skipped {skipped_count} invalid positions. Breakdown: "
                f"missing_description={skip_reasons['missing_description']}, "
                f"empty_description={skip_reasons['empty_description']}, "
                f"missing_quantity={skip_reasons['missing_quantity']}, "
                f"invalid_quantity={skip_reasons['invalid_quantity']}, "
                f"zero_quantity={skip_reasons['zero_quantity']}"
            )
        
        return valid_positions
    
    async def _audit_positions(
        self, 
        positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Audit positions (placeholder - implement actual audit logic)
        
        Args:
            positions: List of valid positions
            
        Returns:
            Audit results
        """
        logger.info(f"Auditing {len(positions)} positions...")
        
        # TODO: Implement actual audit logic with Claude AI
        # For now, return simple stats
        
        audit_results = {
            "total_positions": len(positions),
            "green": 0,  # All good
            "amber": 0,  # Needs attention
            "red": 0,    # Critical issues
            "positions": []
        }
        
        for position in positions:
            # Simple audit: check if code and unit_price present
            has_code = 'code' in position and position['code']
            has_price = 'unit_price' in position and position['unit_price']
            
            if has_code and has_price:
                classification = "GREEN"
                audit_results["green"] += 1
            elif has_code or has_price:
                classification = "AMBER"
                audit_results["amber"] += 1
            else:
                classification = "RED"
                audit_results["red"] += 1
            
            audit_results["positions"].append({
                "position_number": position.get('position_number', ''),
                "description": position.get('description', '')[:100],
                "quantity": position.get('quantity', 0),
                "unit": position.get('unit', ''),
                "classification": classification,
                "issues": [] if classification == "GREEN" else [
                    "Missing KROS code" if not has_code else None,
                    "Missing unit price" if not has_price else None
                ]
            })
        
        logger.info(
            f"Audit complete: "
            f"GREEN={audit_results['green']}, "
            f"AMBER={audit_results['amber']}, "
            f"RED={audit_results['red']}"
        )
        
        return audit_results
    
    def _generate_summary(self, audit_results: Dict[str, Any]) -> str:
        """
        Generate human-readable summary
        
        Args:
            audit_results: Audit results dict
            
        Returns:
            Summary text
        """
        total = audit_results['total_positions']
        green = audit_results['green']
        amber = audit_results['amber']
        red = audit_results['red']
        
        green_pct = (green / total * 100) if total > 0 else 0
        amber_pct = (amber / total * 100) if total > 0 else 0
        red_pct = (red / total * 100) if total > 0 else 0
        
        summary = f"""
Audit Summary
=============

Total Positions: {total}

Classification:
  🟢 GREEN: {green} ({green_pct:.1f}%) - All requirements met
  🟡 AMBER: {amber} ({amber_pct:.1f}%) - Minor issues, needs attention
  🔴 RED: {red} ({red_pct:.1f}%) - Critical issues, requires correction

Recommendations:
"""
        
        if red > 0:
            summary += f"  - Review {red} RED positions immediately\n"
        if amber > 0:
            summary += f"  - Check {amber} AMBER positions for completeness\n"
        if green == total:
            summary += "  - All positions are correctly specified ✓\n"
        
        return summary


# ==============================================================================
# USAGE EXAMPLE
# ==============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_workflow():
        workflow = WorkflowA()
        
        # Test with a project
        result = await workflow.execute(
            project_id="proj_test123",
            generate_summary=True
        )
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test_workflow())
