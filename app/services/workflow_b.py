"""
Workflow B: Generate estimate from technical drawings
Workflow B - Генерация сметы из чертежей (без готового выказа)
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.claude_client import ClaudeClient
from app.core.gpt4_client import GPT4VisionClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class WorkflowB:
    """
    Workflow B: Нет выказа, есть только чертежи
    
    Workflow:
    1. Upload → Только документация + чертежи
    2. GPT-4V анализ чертежей → размеры, объемы
    3. Calculate материалы → бетон, арматура, опалубка
    4. Claude генерация позиций → создание выказа
    5. AUDIT генерированных → как в Workflow A
    6. Generate отчет + Tech Card
    """
    
    def __init__(self):
        """Initialize Workflow B services"""
        self.claude = ClaudeClient()
        self.gpt4v = GPT4VisionClient() if settings.ENABLE_WORKFLOW_B else None
        
        if not self.gpt4v:
            logger.warning("GPT-4 Vision not available. Workflow B limited.")
    
    async def execute(
        self,
        project_id: str,
        vykresy_paths: List[Path],
        project_name: str
    ) -> Dict[str, Any]:
        """
        Execute Workflow B with unified interface
        
        This method provides a unified interface compatible with routes.py.
        It generates estimate from drawings without a vykaz file.
        
        Args:
            project_id: Project ID
            vykresy_paths: Paths to drawing files
            project_name: Name of the project
        
        Returns:
            Dict with generated estimate compatible with project_store
        """
        try:
            logger.info(f"🚀 Executing Workflow B for project {project_id}: {project_name}")
            logger.info(f"  Vykresy files: {len(vykresy_paths)}")
            
            # Use the existing process_drawings() method
            result = await self.process_drawings(
                drawings=vykresy_paths,
                documentation=None,
                project_name=project_name
            )
            
            # Add project_id to result
            result["project_id"] = project_id
            
            # Ensure result has expected fields for project_store
            # Workflow B generates positions, so we need to provide counts
            if result.get("success"):
                result.setdefault("green_count", 0)
                result.setdefault("amber_count", 0)
                result.setdefault("red_count", 0)
                # total_positions should already be in result from process_drawings
            
            logger.info(f"✅ Workflow B completed for project {project_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Workflow B failed for project {project_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "project_id": project_id,
                "total_positions": 0
            }
    
    async def process_drawings(
        self,
        drawings: List[Path],
        documentation: Optional[List[Path]] = None,
        project_name: str = "Unnamed Project"
    ) -> Dict[str, Any]:
        """
        Process construction drawings and generate estimate
        
        Args:
            drawings: List of drawing files (PDF/images)
            documentation: Optional technical documentation
            project_name: Project name
            
        Returns:
            Dict with generated estimate:
            {
                "generated_positions": List[Dict],
                "drawing_analysis": List[Dict],
                "calculations": Dict,
                "tech_card": Dict
            }
        """
        logger.info(f"Workflow B: Processing {len(drawings)} drawings for '{project_name}'")
        
        try:
            # Step 1: Analyze drawings with GPT-4V
            logger.info("Step 1: Analyzing drawings with GPT-4 Vision...")
            drawing_analysis = await self._analyze_drawings(drawings)
            
            # Step 2: Calculate materials
            logger.info("Step 2: Calculating materials...")
            calculations = self._calculate_materials(drawing_analysis)
            
            # Step 3: Generate positions with Claude
            logger.info("Step 3: Generating positions with Claude...")
            positions = await self._generate_positions(
                drawing_analysis,
                calculations,
                documentation
            )
            
            # Step 4: Create technical card
            logger.info("Step 4: Creating technical card...")
            tech_card = self._create_tech_card(
                project_name,
                drawing_analysis,
                calculations
            )
            
            result = {
                "success": True,
                "project_name": project_name,
                "generated_positions": positions,
                "drawing_analysis": drawing_analysis,
                "calculations": calculations,
                "tech_card": tech_card,
                "total_positions": len(positions)
            }
            
            logger.info(f"✅ Workflow B complete: Generated {len(positions)} positions")
            return result
            
        except Exception as e:
            logger.error(f"Workflow B failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "project_name": project_name
            }
    
    async def _analyze_drawings(self, drawings: List[Path]) -> List[Dict[str, Any]]:
        """
        Analyze drawings with GPT-4 Vision
        
        Returns:
            List of analyzed drawing data:
            [{
                "drawing_file": str,
                "elements": List[Dict],
                "dimensions": Dict,
                "materials": Dict,
                "notes": str
            }, ...]
        """
        if not self.gpt4v:
            raise ValueError("GPT-4 Vision not available")
        
        analysis_results = []
        
        for drawing in drawings:
            logger.info(f"  Analyzing drawing: {drawing.name}")
            
            try:
                # Use GPT-4V to analyze drawing
                analysis = await self.gpt4v.analyze_construction_drawing(drawing)
                
                analysis_results.append({
                    "drawing_file": drawing.name,
                    "elements": analysis.get("elements", []),
                    "dimensions": analysis.get("dimensions", {}),
                    "materials": analysis.get("materials", {}),
                    "notes": analysis.get("notes", ""),
                    "raw_analysis": analysis
                })
                
            except Exception as e:
                logger.error(f"Failed to analyze {drawing.name}: {e}")
                analysis_results.append({
                    "drawing_file": drawing.name,
                    "error": str(e)
                })
        
        return analysis_results
    
    def _calculate_materials(self, drawing_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate materials from drawing analysis
        
        Returns:
            Dict with material calculations:
            {
                "concrete": {
                    "volume": float,
                    "grade": str,
                    "positions": List
                },
                "reinforcement": {...},
                "formwork": {...}
            }
        """
        logger.info("Calculating materials from drawings...")
        
        calculations = {
            "concrete": {
                "volume": 0.0,
                "grade": "C25/30",
                "positions": []
            },
            "reinforcement": {
                "weight": 0.0,
                "class": "B500B",
                "positions": []
            },
            "formwork": {
                "area": 0.0,
                "type": "Standard",
                "positions": []
            }
        }
        
        # Extract and sum up materials from each drawing
        for analysis in drawing_analysis:
            if "error" in analysis:
                continue
            
            materials = analysis.get("materials", {})
            dimensions = analysis.get("dimensions", {})
            
            # Calculate concrete volume
            if "concrete" in materials:
                concrete_data = materials["concrete"]
                volume = concrete_data.get("volume", 0.0)
                calculations["concrete"]["volume"] += volume
                
                calculations["concrete"]["positions"].append({
                    "source": analysis["drawing_file"],
                    "volume": volume,
                    "grade": concrete_data.get("grade", "C25/30")
                })
            
            # Calculate reinforcement
            if "reinforcement" in materials:
                rebar_data = materials["reinforcement"]
                weight = rebar_data.get("weight", 0.0)
                calculations["reinforcement"]["weight"] += weight
                
                calculations["reinforcement"]["positions"].append({
                    "source": analysis["drawing_file"],
                    "weight": weight,
                    "class": rebar_data.get("class", "B500B")
                })
            
            # Calculate formwork
            if "formwork" in materials or dimensions:
                # Estimate formwork area from dimensions
                area = self._estimate_formwork_area(dimensions)
                calculations["formwork"]["area"] += area
                
                calculations["formwork"]["positions"].append({
                    "source": analysis["drawing_file"],
                    "area": area
                })
        
        logger.info(f"  Concrete: {calculations['concrete']['volume']:.2f} m³")
        logger.info(f"  Reinforcement: {calculations['reinforcement']['weight']:.2f} kg")
        logger.info(f"  Formwork: {calculations['formwork']['area']:.2f} m²")
        
        return calculations
    
    def _estimate_formwork_area(self, dimensions: Dict[str, Any]) -> float:
        """Estimate formwork area from dimensions"""
        # Simple heuristic - can be improved
        area = 0.0
        
        if "length" in dimensions and "height" in dimensions:
            length = dimensions.get("length", 0.0)
            height = dimensions.get("height", 0.0)
            area = length * height * 2  # Both sides
        
        return area
    
    # ========================================
    # NEW: EXECUTE METHOD FOR CONSISTENCY
    # ========================================
    
    async def execute(
        self,
        project_id: str,
        vykresy_paths: List[Path],
        project_name: str
    ) -> Dict[str, Any]:
        """
        Execute Workflow B: Generate estimate from drawings
        
        This is a wrapper around process_drawings() for consistency with WorkflowA.
        
        Args:
            project_id: Project ID
            vykresy_paths: List of paths to drawings
            project_name: Project name
        
        Returns:
            Dict with generated estimate and statistics
        """
        try:
            logger.info(f"🚀 Starting execute() for Workflow B project {project_id}")
            
            # Call the existing process_drawings method
            result = await self.process_drawings(
                drawings=vykresy_paths,
                documentation=None,
                project_name=project_name
            )
            
            # Add project_id to result
            result["project_id"] = project_id
            
            # Calculate statistics for consistency with WorkflowA
            positions = result.get("generated_positions", [])
            
            # For Workflow B, all generated positions are initially "OK" (green)
            # They would need validation in a later step
            result.update({
                "total_positions": len(positions),
                "green_count": len(positions),
                "amber_count": 0,
                "red_count": 0,
                "ready_for_analysis": True
            })
            
            logger.info(f"✅ Workflow B execute complete: {len(positions)} positions generated")
            
            return result
            
        except Exception as e:
            logger.error(f"Workflow B execute failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "project_id": project_id
            }
    
    async def _generate_positions(
        self,
        drawing_analysis: List[Dict[str, Any]],
        calculations: Dict[str, Any],
        documentation: Optional[List[Path]]
    ) -> List[Dict[str, Any]]:
        """
        Generate estimate positions using Claude
        
        Returns:
            List of generated positions with KROS codes
        """
        logger.info("Generating positions with Claude...")
        
        # Prepare context for Claude
        context = {
            "drawing_analysis": drawing_analysis,
            "calculations": calculations,
            "documentation": []
        }
        
        # Add documentation if available
        if documentation:
            for doc in documentation:
                # Read documentation
                try:
                    with open(doc, 'r', encoding='utf-8') as f:
                        content = f.read()[:5000]  # First 5000 chars
                    context["documentation"].append({
                        "file": doc.name,
                        "content": content
                    })
                except Exception as e:
                    logger.warning(f"Failed to read {doc.name}: {e}")
        
        # Load generation prompt
        prompt = self.claude._load_prompt_from_file("generation/generate_from_drawings")
        
        # Build full prompt
        import json
        full_prompt = f"""{prompt}

===== CONTEXT =====
{json.dumps(context, ensure_ascii=False, indent=2)}
"""
        
        # Generate positions with Claude
        result = self.claude.call(full_prompt)
        
        positions = result.get("positions", [])
        
        logger.info(f"✅ Generated {len(positions)} positions")
        return positions
    
    def _create_tech_card(
        self,
        project_name: str,
        drawing_analysis: List[Dict[str, Any]],
        calculations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create technical card
        
        Returns:
            Technical card with project details
        """
        tech_card = {
            "project_name": project_name,
            "drawings_analyzed": len(drawing_analysis),
            "materials": {
                "concrete": {
                    "total_volume": calculations["concrete"]["volume"],
                    "grade": calculations["concrete"]["grade"]
                },
                "reinforcement": {
                    "total_weight": calculations["reinforcement"]["weight"],
                    "class": calculations["reinforcement"]["class"]
                },
                "formwork": {
                    "total_area": calculations["formwork"]["area"],
                    "type": calculations["formwork"]["type"]
                }
            },
            "elements": []
        }
        
        # Extract unique elements
        all_elements = []
        for analysis in drawing_analysis:
            if "error" not in analysis:
                all_elements.extend(analysis.get("elements", []))
        
        # Deduplicate elements
        unique_elements = {}
        for elem in all_elements:
            elem_type = elem.get("type", "Unknown")
            if elem_type not in unique_elements:
                unique_elements[elem_type] = {
                    "type": elem_type,
                    "count": 0,
                    "instances": []
                }
            unique_elements[elem_type]["count"] += 1
            unique_elements[elem_type]["instances"].append(elem)
        
        tech_card["elements"] = list(unique_elements.values())
        
        return tech_card
