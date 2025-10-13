"""
Workflow A - ENHANCED with Drawing Enrichment
Audit existing Výkaz výměr + Enrich with Drawing Specifications
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from app.parsers.smart_parser import SmartParser
from app.parsers.drawing_specs_parser import DrawingSpecsParser
from app.services.position_enricher import PositionEnricher
from app.services.specifications_validator import SpecificationsValidator
from app.core.config import settings
from app.models.project import ProjectStatus
from app.state.project_store import project_store

logger = logging.getLogger(__name__)


class WorkflowA:
    """
    Workflow A: Audit existing Výkaz výměr with Drawing Enrichment
    
    Enhanced workflow:
    1. Parse výkaz výměr (Excel/XML/PDF)
    2. Parse vykresy (drawings) for technical specifications
    3. Enrich positions with drawing specifications
    4. Validate specifications against ČSN standards
    5. Audit positions
    6. Generate report
    """
    
    def __init__(self):
        self.parser = SmartParser()
        self.drawing_parser = DrawingSpecsParser()
        self.enricher = PositionEnricher()
        self.validator = SpecificationsValidator()
    
    async def execute(
        self,
        project_id: str,
        generate_summary: bool = True,
        enable_enrichment: bool = True  # NEW: Enable/disable enrichment
    ) -> Dict[str, Any]:
        """
        Execute Workflow A with optional enrichment
        
        Args:
            project_id: Project identifier
            generate_summary: Whether to generate AI summary
            enable_enrichment: Whether to enrich positions with drawing specs
            
        Returns:
            Audit results dict with enriched positions
        """
        logger.info(
            f"Starting Workflow A for project {project_id} "
            f"(enrichment={'enabled' if enable_enrichment else 'disabled'})"
        )
        
        try:
            # Find project directory
            project_dir = settings.DATA_DIR / "raw" / project_id
            
            if not project_dir.exists():
                raise FileNotFoundError(f"Project directory not found: {project_dir}")
            
            # Step 1: Parse výkaz výměr
            logger.info("Step 1: Parsing výkaz výměr...")
            parse_result = await self._parse_vykaz_vymer(project_dir)
            positions = parse_result["positions"]
            parsing_diagnostics = parse_result["diagnostics"]

            if not positions:
                message = (
                    "No positions found in výkaz výměr"
                    f" (raw={parsing_diagnostics.get('raw_total', 0)}, "
                    f"skipped={parsing_diagnostics.get('skipped_total', 0)})"
                )
                logger.warning(message)
                self._update_project_record(
                    project_id,
                    status=ProjectStatus.FAILED,
                    progress=100,
                    positions_total=0,
                    positions_processed=0,
                    positions_raw=parsing_diagnostics.get('raw_total', 0),
                    positions_skipped=parsing_diagnostics.get('skipped_total', 0),
                    diagnostics={"parsing": parsing_diagnostics},
                    message=message,
                    error=message
                )
                return {
                    "project_id": project_id,
                    "status": "FAILED",
                    "workflow": "A",
                    "success": False,
                    "error": message,
                    "diagnostics": {
                        "parsing": parsing_diagnostics
                    },
                    "positions_total": 0,
                    "positions_raw": parsing_diagnostics.get('raw_total', 0),
                    "positions_skipped": parsing_diagnostics.get('skipped_total', 0)
                }

            logger.info(f"Parsed {len(positions)} positions from výkaz výměr")
            self._update_project_record(
                project_id,
                status=ProjectStatus.PROCESSING,
                progress=30,
                positions_total=len(positions),
                positions_processed=len(positions),
                positions_raw=parsing_diagnostics.get('raw_total', len(positions)),
                positions_skipped=parsing_diagnostics.get('skipped_total', 0),
                diagnostics={"parsing": parsing_diagnostics},
                message="Výkaz výměr parsed successfully"
            )
            
            # Step 2: Parse drawings (if enrichment enabled)
            drawing_specs = []
            if enable_enrichment:
                logger.info("Step 2: Parsing drawings for specifications...")
                drawing_specs = await self._parse_drawings(project_dir)
                logger.info(f"Found {len(drawing_specs)} specifications from drawings")
            else:
                logger.info("Step 2: Skipping drawing parsing (enrichment disabled)")
            
            # Step 3: Enrich positions (if specifications found)
            if enable_enrichment and drawing_specs:
                logger.info("Step 3: Enriching positions with drawing specifications...")
                positions = await self.enricher.enrich_positions(positions, drawing_specs)
                logger.info("Positions enriched successfully")
            else:
                logger.info("Step 3: Skipping enrichment (no specifications or disabled)")
            
            # Step 4: Validate specifications
            logger.info("Step 4: Validating technical specifications...")
            positions = self.validator.validate_positions_batch(positions)
            logger.info("Specifications validated")
            
            # Step 5: Audit positions
            logger.info("Step 5: Auditing positions...")
            audit_results = await self._audit_positions(positions)
            logger.info("Audit completed")
            
            # Step 6: Generate summary
            summary = None
            if generate_summary:
                logger.info("Step 6: Generating summary...")
                summary = self._generate_enhanced_summary(audit_results, enable_enrichment)

            logger.info(f"✅ Workflow A completed for project {project_id}")

            self._update_project_record(
                project_id,
                status=ProjectStatus.COMPLETED,
                progress=100,
                positions_total=len(positions),
                positions_processed=len(positions),
                positions_raw=parsing_diagnostics.get('raw_total', len(positions)),
                positions_skipped=parsing_diagnostics.get('skipped_total', 0),
                drawing_specs_count=len(drawing_specs),
                audit_results=audit_results,
                summary=summary,
                completed_at=datetime.now().isoformat(),
                message="Workflow A completed successfully",
                error=None,
                diagnostics={
                    "parsing": parsing_diagnostics,
                    "drawing_enrichment": {
                        "enabled": enable_enrichment,
                        "drawing_specs_count": len(drawing_specs)
                    }
                }
            )

            return {
                "project_id": project_id,
                "status": "COMPLETED",
                "workflow": "A",
                "enrichment_enabled": enable_enrichment,
                "positions_count": len(positions),
                "drawing_specs_count": len(drawing_specs),
                "audit_results": audit_results,
                "summary": summary,
                "completed_at": datetime.now().isoformat(),
                "diagnostics": {
                    "parsing": parsing_diagnostics,
                    "drawing_enrichment": {
                        "enabled": enable_enrichment,
                        "drawing_specs_count": len(drawing_specs)
                    }
                }
            }

        except Exception as e:
            logger.error(f"❌ Workflow A failed: {str(e)}", exc_info=True)
            self._update_project_record(
                project_id,
                status=ProjectStatus.FAILED,
                progress=100,
                error=str(e),
                message=str(e)
            )
            return {
                "project_id": project_id,
                "status": "FAILED",
                "workflow": "A",
                "error": str(e),
                "positions_count": 0
            }

    async def _parse_vykaz_vymer(self, project_dir: Path) -> Dict[str, Any]:
        """
        Parse výkaz výměr documents
        
        Args:
            project_dir: Project directory
            
        Returns:
            Dict with normalized positions and diagnostics
        """
        vykaz_dir = project_dir / "vykaz_vymer"
        
        if not vykaz_dir.exists():
            raise FileNotFoundError(f"Vykaz vymer directory not found: {vykaz_dir}")
        
        vykaz_files = [f for f in vykaz_dir.glob("*") if f.is_file()]
        
        if not vykaz_files:
            raise FileNotFoundError(f"No files found in {vykaz_dir}")
        
        all_positions: List[Dict[str, Any]] = []
        diagnostics = {
            "files": [],
            "raw_total": 0,
            "normalized_total": 0,
            "skipped_total": 0
        }

        for file_path in vykaz_files:
            logger.info(f"Parsing: {file_path.name}")

            result = self.parser.parse(file_path)
            file_positions = result.get('positions') or []
            file_diagnostics = result.get('diagnostics', {})

            raw_count = file_diagnostics.get('raw_total')
            normalized_count = file_diagnostics.get('normalized_total', len(file_positions))
            skipped_count = file_diagnostics.get('skipped_total')

            if raw_count is None:
                raw_count = len(file_positions)
            if skipped_count is None:
                skipped_count = max(raw_count - normalized_count, 0)

            diagnostics['files'].append({
                "filename": file_path.name,
                "raw_total": raw_count,
                "normalized_total": normalized_count,
                "skipped_total": skipped_count,
                "details": file_diagnostics.get('sheet_summaries') or file_diagnostics
            })

            diagnostics['raw_total'] += raw_count
            diagnostics['normalized_total'] += normalized_count
            diagnostics['skipped_total'] += skipped_count

            if file_positions:
                logger.info(f"Got {len(file_positions)} positions from {file_path.name}")
                all_positions.extend(file_positions)
            else:
                logger.warning(f"No positions found in {file_path.name}")

        return {
            "positions": all_positions,
            "diagnostics": diagnostics
        }

    def _update_project_record(self, project_id: str, **updates: Any) -> None:
        """Safely update the in-memory project store."""

        project = project_store.get(project_id)
        if not project:
            logger.debug(
                "Project %s not found in store while updating with %s",
                project_id,
                updates
            )
            return

        if updates:
            project.update(updates)

        project["updated_at"] = datetime.now().isoformat()
    
    async def _parse_drawings(self, project_dir: Path) -> List[Dict[str, Any]]:
        """
        Parse drawings for technical specifications
        
        Args:
            project_dir: Project directory
            
        Returns:
            List of technical specifications from drawings
        """
        vykresy_dir = project_dir / "vykresy"
        
        if not vykresy_dir.exists():
            logger.warning(f"Vykresy directory not found: {vykresy_dir}")
            return []
        
        drawing_files = [
            f for f in vykresy_dir.glob("*.pdf")
            if f.is_file()
        ]
        
        if not drawing_files:
            logger.warning(f"No PDF drawings found in {vykresy_dir}")
            return []
        
        logger.info(f"Found {len(drawing_files)} drawing files")
        
        all_specs = []
        
        for drawing_path in drawing_files:
            logger.info(f"Parsing drawing: {drawing_path.name}")
            
            result = self.drawing_parser.parse(drawing_path)
            
            if result and result.get('specifications'):
                specs = result['specifications']
                logger.info(
                    f"Extracted {len(specs)} specifications from {drawing_path.name}"
                )
                all_specs.extend(specs)
            else:
                logger.debug(f"No specifications found in {drawing_path.name}")
        
        return all_specs
    
    async def _audit_positions(
        self,
        positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Audit positions with enhanced classification
        
        Takes into account:
        - Basic position data (code, price, quantity)
        - Technical specifications (if enriched)
        - Validation results
        
        Args:
            positions: List of positions (potentially enriched)
            
        Returns:
            Audit results with statistics
        """
        logger.info(f"Auditing {len(positions)} positions...")
        
        audit_results = {
            "total_positions": len(positions),
            "green": 0,  # All good
            "amber": 0,  # Needs attention
            "red": 0,    # Critical issues
            "positions": []
        }
        
        # Statistics for enrichment
        enrichment_stats = {
            'matched': 0,
            'partial': 0,
            'unmatched': 0
        }
        
        # Statistics for validation
        validation_stats = {
            'passed': 0,
            'warning': 0,
            'failed': 0,
            'no_specs': 0
        }
        
        for position in positions:
            # Determine classification based on multiple factors
            classification = self._classify_position(position)
            
            # Update statistics
            audit_results[classification.lower()] += 1
            
            # Track enrichment status
            if 'enrichment_status' in position:
                status = position['enrichment_status']
                enrichment_stats[status] = enrichment_stats.get(status, 0) + 1
            
            # Track validation status
            if 'validation_status' in position:
                val_status = position['validation_status']
                validation_stats[val_status] = validation_stats.get(val_status, 0) + 1
            
            # Create audit position
            audit_position = {
                "position_number": position.get('position_number', ''),
                "description": position.get('description', '')[:100],
                "quantity": position.get('quantity', 0),
                "unit": position.get('unit', ''),
                "classification": classification,
                "issues": self._get_issues(position),
                "recommendations": self._get_recommendations(position)
            }
            
            # Add enrichment info if present
            if 'technical_specs' in position:
                audit_position['technical_specs'] = position['technical_specs']
            
            if 'drawing_source' in position:
                audit_position['drawing_source'] = position['drawing_source']
            
            if 'validation_results' in position:
                audit_position['validation_summary'] = {
                    'status': position['validation_status'],
                    'errors_count': len(position['validation_results'].get('errors', [])),
                    'warnings_count': len(position['validation_results'].get('warnings', []))
                }
            
            audit_results["positions"].append(audit_position)
        
        # Add enrichment and validation statistics
        audit_results['enrichment_stats'] = enrichment_stats
        audit_results['validation_stats'] = validation_stats
        
        logger.info(
            f"Audit complete: "
            f"GREEN={audit_results['green']}, "
            f"AMBER={audit_results['amber']}, "
            f"RED={audit_results['red']}"
        )
        
        if enrichment_stats['matched'] > 0:
            logger.info(
                f"Enrichment: "
                f"matched={enrichment_stats['matched']}, "
                f"partial={enrichment_stats.get('partial', 0)}, "
                f"unmatched={enrichment_stats.get('unmatched', 0)}"
            )
        
        if validation_stats.get('failed', 0) > 0:
            logger.warning(
                f"Validation: {validation_stats['failed']} positions failed validation"
            )
        
        return audit_results
    
    def _classify_position(self, position: Dict[str, Any]) -> str:
        """
        Classify position as GREEN, AMBER, or RED
        
        Classification logic:
        - RED: Critical issues (missing code, validation failed, critical spec mismatch)
        - AMBER: Needs attention (missing price, validation warnings, partial match)
        - GREEN: All good
        
        Args:
            position: Position to classify
            
        Returns:
            Classification: "GREEN", "AMBER", or "RED"
        """
        issues = []
        
        # Check basic requirements
        has_code = 'code' in position and position['code']
        has_price = 'unit_price' in position and position['unit_price']
        
        # Check validation status
        validation_status = position.get('validation_status')
        validation_failed = validation_status == 'failed'
        validation_warning = validation_status == 'warning'
        
        # Check enrichment
        enrichment_status = position.get('enrichment_status')
        enrichment_partial = enrichment_status == 'partial'
        
        # Determine classification
        if not has_code:
            issues.append("Missing KROS code")
        
        if validation_failed:
            issues.append("Validation failed")
        
        # RED: Critical issues
        if not has_code or validation_failed:
            return "RED"
        
        # AMBER: Needs attention
        if not has_price or validation_warning or enrichment_partial:
            return "AMBER"
        
        # GREEN: All good
        return "GREEN"
    
    def _get_issues(self, position: Dict[str, Any]) -> List[str]:
        """Get list of issues for position"""
        issues = []
        
        if not position.get('code'):
            issues.append("Missing KROS code")
        
        if not position.get('unit_price'):
            issues.append("Missing unit price")
        
        # Add validation errors
        if position.get('validation_results'):
            validation = position['validation_results']
            issues.extend(validation.get('errors', []))
        
        return issues
    
    def _get_recommendations(self, position: Dict[str, Any]) -> List[str]:
        """Get list of recommendations for position"""
        recommendations = []
        
        # Add validation warnings as recommendations
        if position.get('validation_results'):
            validation = position['validation_results']
            recommendations.extend(validation.get('warnings', []))
        
        # Add enrichment-based recommendations
        if position.get('enrichment_status') == 'unmatched':
            recommendations.append(
                "Nebyla nalezena odpovídající specifikace ve výkresech. "
                "Ověřte správnost materiálu."
            )
        
        if position.get('enrichment_status') == 'partial':
            recommendations.append(
                "Částečná shoda se specifikací. "
                "Doporučeno ověřit parametry materiálu."
            )
        
        return recommendations
    
    def _generate_enhanced_summary(
        self,
        audit_results: Dict[str, Any],
        enrichment_enabled: bool
    ) -> str:
        """
        Generate enhanced summary with enrichment statistics
        
        Args:
            audit_results: Audit results
            enrichment_enabled: Whether enrichment was enabled
            
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
Audit Summary (Enhanced with Drawing Specifications)
====================================================

Total Positions: {total}

Classification:
  🟢 GREEN: {green} ({green_pct:.1f}%) - All requirements met
  🟡 AMBER: {amber} ({amber_pct:.1f}%) - Minor issues, needs attention
  🔴 RED: {red} ({red_pct:.1f}%) - Critical issues, requires correction

"""
        
        # Add enrichment statistics
        if enrichment_enabled:
            enrichment_stats = audit_results.get('enrichment_stats', {})
            matched = enrichment_stats.get('matched', 0)
            partial = enrichment_stats.get('partial', 0)
            unmatched = enrichment_stats.get('unmatched', 0)
            
            if matched > 0 or partial > 0:
                matched_pct = (matched / total * 100) if total > 0 else 0
                summary += f"""
Enrichment with Drawings:
  ✅ Matched: {matched} ({matched_pct:.1f}%) - Full technical specifications found
  ⚠️ Partial: {partial} - Some specifications found
  ❌ Unmatched: {unmatched} - No specifications in drawings

"""
        
        # Add validation statistics
        validation_stats = audit_results.get('validation_stats', {})
        if validation_stats:
            passed = validation_stats.get('passed', 0)
            warning = validation_stats.get('warning', 0)
            failed = validation_stats.get('failed', 0)
            
            summary += f"""
Standards Validation (ČSN EN 206):
  ✅ Passed: {passed} - Compliant with standards
  ⚠️ Warnings: {warning} - Minor compliance issues
  ❌ Failed: {failed} - Non-compliant
  
"""
        
        # Recommendations
        summary += "Recommendations:\n"
        
        if red > 0:
            summary += f"  - Review {red} RED positions immediately\n"
        if amber > 0:
            summary += f"  - Check {amber} AMBER positions for completeness\n"
        if enrichment_enabled:
            unmatched = enrichment_stats.get('unmatched', 0)
            if unmatched > 0:
                summary += f"  - {unmatched} positions have no drawing specifications - verify manually\n"
        if validation_stats.get('failed', 0) > 0:
            summary += f"  - {validation_stats['failed']} positions failed standards validation - correct immediately\n"
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
        
        # Test with enrichment enabled
        result = await workflow.execute(
            project_id="proj_test123",
            generate_summary=True,
            enable_enrichment=True
        )
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test_workflow())
