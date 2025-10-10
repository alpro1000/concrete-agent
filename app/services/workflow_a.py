"""
Workflow A: Import and Audit Construction Estimates
Simplified version - user selects positions to analyze
WITH specialized parsers for better accuracy
"""
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional
import json

from app.core.claude_client import ClaudeClient
from app.core.config import settings
from app.core.nanonets_client import NanonetsClient
from app.core.mineru_client import MinerUClient
from app.parsers import KROSParser, PDFParser, ExcelParser

logger = logging.getLogger(__name__)


class WorkflowA:
    """
    Simplified Workflow A: Import ALL positions, user selects what to analyze
    
    New workflow:
    1. Import all positions without limitations
    2. Display positions with checkboxes
    3. User selects positions to analyze
    4. Analyze only selected positions
    
    NOW WITH: Specialized parsers for better accuracy
    """
    
    def __init__(self):
        self.claude = ClaudeClient()
        self.kb_dir = settings.KB_DIR
        
        # Initialize optional clients
        self.nanonets = None
        self.mineru = None
        
        if settings.NANONETS_API_KEY:
            try:
                self.nanonets = NanonetsClient()
                logger.info("✅ Nanonets client initialized")
            except Exception as e:
                logger.warning(f"Nanonets initialization failed: {e}")
        
        try:
            self.mineru = MinerUClient(
                output_dir=settings.MINERU_OUTPUT_DIR,
                ocr_engine=settings.MINERU_OCR_ENGINE
            )
            if self.mineru.available:
                logger.info("✅ MinerU client initialized")
        except Exception as e:
            logger.warning(f"MinerU initialization failed: {e}")
        
        # Initialize parsers
        self.kros_parser = KROSParser(
            claude_client=self.claude,
            nanonets_client=self.nanonets
        )
        self.pdf_parser = PDFParser(
            claude_client=self.claude,
            mineru_client=self.mineru
        )
        self.excel_parser = ExcelParser(
            claude_client=self.claude
        )
    
    async def import_and_prepare(
        self,
        file_path: Path,
        project_name: str
    ) -> Dict[str, Any]:
        """
        Import ALL positions from document without limitations
        
        Args:
            file_path: Path to document file
            project_name: Name of the project
        
        Returns:
            Dict with all imported positions
        """
        try:
            logger.info(f"Importing positions from: {file_path}")
            
            # Step 1: Detect file format and parse
            file_format = self._detect_format(file_path)
            logger.info(f"Detected file format: {file_format}")
            
            # Step 2: Parse document (NO LIMITATIONS!)
            positions = await self._parse_document(file_path, file_format)
            logger.info(f"Imported {len(positions)} positions")
            
            if not positions:
                logger.warning("No positions found in document!")
                return {
                    "success": False,
                    "error": "No positions found in document",
                    "positions": []
                }
            
            # Step 3: Add metadata
            for idx, pos in enumerate(positions):
                pos['index'] = idx
                pos['selected'] = False  # User will select via checkboxes
            
            return {
                "success": True,
                "project_name": project_name,
                "total_positions": len(positions),
                "positions": positions,
                "file_format": file_format,
                "project_context": {
                    "file_name": file_path.name,
                    "project_name": project_name
                }
            }
        
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "positions": []
            }
    
    async def analyze_selected_positions(
        self,
        positions: List[Dict[str, Any]],
        selected_indices: List[int],
        project_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze only selected positions
        
        Args:
            positions: All positions
            selected_indices: Indices of positions to analyze
            project_context: Optional project context
        
        Returns:
            Analysis results for selected positions
        """
        try:
            logger.info(f"Analyzing {len(selected_indices)} selected positions out of {len(positions)}")
            
            # Filter selected positions
            selected_positions = [positions[i] for i in selected_indices if i < len(positions)]
            
            if not selected_positions:
                return {
                    "success": False,
                    "error": "No valid positions selected",
                    "results": []
                }
            
            # Load Knowledge Base
            kb_data = self._load_knowledge_base()
            logger.info(f"Loaded KB with {len(kb_data)} categories")
            
            # Analyze each selected position
            results = []
            for idx, position in enumerate(selected_positions, 1):
                logger.info(f"Analyzing position {idx}/{len(selected_positions)}: {position.get('description', 'N/A')[:50]}")
                
                try:
                    audit_result = await self._audit_position(position, kb_data, project_context)
                    results.append(audit_result)
                except Exception as e:
                    logger.error(f"Failed to audit position {idx}: {e}")
                    results.append({
                        "position": position,
                        "status": "ERROR",
                        "error": str(e),
                        "classification": "RED",
                        "hitl_required": True
                    })
            
            return {
                "success": True,
                "total_analyzed": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "results": []
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
        Parse document based on format using SPECIALIZED PARSERS
        
        Args:
            file_path: Path to document
            file_format: Format type
        
        Returns:
            List of ALL parsed positions
        """
        try:
            logger.info(f"Parsing {file_format} document with specialized parser...")
            
            if file_format == 'excel':
                # Use Excel parser
                result = self.excel_parser.parse(file_path)
            elif file_format == 'xml':
                # Use KROS parser with auto-detection and fallback
                result = self.kros_parser.parse(file_path)
            elif file_format == 'pdf':
                # Use PDF parser with MinerU/pdfplumber
                result = self.pdf_parser.parse(file_path)
            else:
                raise ValueError(f"Unsupported format: {file_format}")
            
            # Extract positions from result
            positions = result.get('positions', [])
            
            logger.info(f"✅ Parsed {len(positions)} positions with specialized parser")
            
            # Validate positions
            valid_positions = []
            for pos in positions:
                if self._is_valid_position(pos):
                    valid_positions.append(pos)
                else:
                    logger.warning(f"Skipping invalid position: {pos}")
            
            logger.info(f"✅ {len(valid_positions)} valid positions after validation")
            
            return valid_positions
        
        except Exception as e:
            logger.error(f"Failed to parse document with specialized parser: {e}")
            
            # Fallback to Claude direct parsing if enabled
            if settings.FALLBACK_ENABLED:
                logger.warning("Falling back to Claude direct parsing...")
                try:
                    if file_format == 'excel':
                        result = self.claude.parse_excel(file_path)
                    elif file_format == 'xml':
                        result = self.claude.parse_xml(file_path)
                    elif file_format == 'pdf':
                        result = self.claude.parse_pdf(file_path)
                    else:
                        raise ValueError(f"Unsupported format: {file_format}")
                    
                    positions = result.get('positions', [])
                    logger.info(f"✅ Fallback: Parsed {len(positions)} positions")
                    return positions
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")
                    raise
            else:
                raise
    
    def _is_valid_position(self, position: Dict[str, Any]) -> bool:
        """
        Check if position has minimum required fields
        
        Args:
            position: Position dict
        
        Returns:
            True if valid
        """
        # Minimum requirement: must have description
        return 'description' in position and position['description']
    
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
            if json_file.name == "metadata.json":
                continue  # Skip metadata
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
        kb_data: Dict[str, Any],
        project_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Audit single position using Claude
        
        Args:
            position: Position to audit
            kb_data: Knowledge Base data
            project_context: Optional project context
        
        Returns:
            Audit result with classification
        """
        try:
            # Build audit prompt
            prompt = self._build_audit_prompt(position, kb_data, project_context)
            
            # Call Claude to audit
            result = self.claude.call(prompt)
            
            # Ensure required fields
            result['position'] = position
            result.setdefault('classification', 'AMBER')
            result.setdefault('hitl_required', False)
            
            # Determine HITL based on classification
            if result['classification'] == 'RED':
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
    
    def _build_audit_prompt(
        self,
        position: Dict[str, Any],
        kb_data: Dict[str, Any],
        project_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build audit prompt for Claude
        
        Args:
            position: Position to audit
            kb_data: Knowledge Base data
            project_context: Optional project context
        
        Returns:
            Prompt string
        """
        prompt = f"""Analyzuj tuto pozici stavebního výkazu výměr a proveď audit.

===== POZICE K AUDITU =====
{json.dumps(position, ensure_ascii=False, indent=2)}

===== KNOWLEDGE BASE =====
Dostupné kódy KROS/ÚRS: {len(kb_data.get('codes', []))} položek
Dostupné ČSN standardy: {len(kb_data.get('standards', []))} položek
Aktuální ceny: {len(kb_data.get('prices', []))} položek

===== ÚKOL =====
1. Zkontroluj kód pozice (KROS/ÚRS)
2. Zkontroluj popis a jednotku
3. Zkontroluj cenu (pokud je uvedena)
4. Zkontroluj množství (pokud je uvedeno)
5. Identifikuj případné problémy

===== VÝSTUP =====
Vrať JSON:
{{
  "classification": "GREEN/AMBER/RED",
  "issues": ["seznam problémů"],
  "recommendations": ["doporučení"],
  "price_check": "OK/WARNING/ERROR",
  "code_check": "OK/WARNING/ERROR",
  "notes": "poznámky"
}}

Vrať POUZE JSON, bez markdown.
"""
        
        if project_context:
            prompt += f"\n\n===== KONTEXT PROJEKTU =====\n{json.dumps(project_context, ensure_ascii=False, indent=2)}\n"
        
        return prompt
    
    # ========================================
    # UNIFIED EXECUTE METHOD
    # ========================================
    
    async def execute(
        self,
        project_id: str,
        vykaz_path: Optional[Path],
        vykresy_paths: List[Path],
        project_name: str
    ) -> Dict[str, Any]:
        """
        Execute Workflow A with unified interface
        
        This method provides a unified interface compatible with routes.py.
        It processes the vykaz file and uses vykresy for context.
        
        Args:
            project_id: Project ID
            vykaz_path: Path to vykaz file (required for Workflow A)
            vykresy_paths: Paths to drawing files (for context)
            project_name: Name of the project
        
        Returns:
            Dict with audit results compatible with project_store
        """
        try:
            logger.info(f"🚀 Executing Workflow A for project {project_id}: {project_name}")
            
            # Validate vykaz_path
            if not vykaz_path or not vykaz_path.exists():
                logger.error("Workflow A requires vykaz_path")
                return {
                    "success": False,
                    "error": "Vykaz file is required for Workflow A",
                    "project_id": project_id,
                    "total_positions": 0
                }
            
            logger.info(f"  Vykaz file: {vykaz_path}")
            logger.info(f"  Vykresy files: {len(vykresy_paths)}")
            
            # Use the existing run() method for core processing
            result = await self.run(
                file_path=vykaz_path,
                project_name=project_name
            )
            
            # Add project_id to result
            result["project_id"] = project_id
            
            # Ensure result has expected fields for project_store
            if result.get("success"):
                # Extract counts from summary or categorized results
                summary = result.get("summary", {})
                result.setdefault("green_count", summary.get("green_count", 0))
                result.setdefault("amber_count", summary.get("amber_count", 0))
                result.setdefault("red_count", summary.get("red_count", 0))
                result.setdefault("total_positions", summary.get("total_positions", 0))
            
            logger.info(f"✅ Workflow A completed for project {project_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Workflow A failed for project {project_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "project_id": project_id,
                "total_positions": 0
            }
    
    # ========================================
    # BACKWARD COMPATIBILITY METHOD
    # ========================================
    
    async def run(
        self,
        file_path: Path,
        project_name: str
    ) -> Dict[str, Any]:
        """
        Run complete Workflow A (backward compatibility)
        
        This method provides backward compatibility with the old API.
        It calls the new simplified workflow methods.
        
        Args:
            file_path: Path to document file
            project_name: Name of the project
        
        Returns:
            Audit results
        """
        try:
            logger.info(f"Starting Workflow A (compatibility mode) for: {file_path}")
            
            # Step 1: Import and prepare all positions
            import_result = await self.import_and_prepare(file_path, project_name)
            
            if not import_result.get("success"):
                return import_result
            
            positions = import_result.get("positions", [])
            
            if not positions:
                logger.warning("No positions to audit")
                return {
                    "success": False,
                    "error": "No positions found in document",
                    "positions": []
                }
            
            # Step 2: For backward compatibility, analyze ALL positions
            # (In new workflow, user selects which positions to analyze)
            logger.info(f"Auto-analyzing all {len(positions)} positions for compatibility")
            
            position_ids = [i for i in range(len(positions))]
            
            # Step 3: Analyze selected positions
            audit_result = await self.analyze_selected_positions(
                positions=positions,
                selected_indices=position_ids,
                project_context=import_result.get("project_context", {})
            )
            
            # Step 4: Add summary statistics
            categorized = self._categorize_results(audit_result.get("results", []))
            summary = self._generate_summary(categorized)
            
            return {
                "success": True,
                "project_name": project_name,
                "total_positions": len(positions),
                "analyzed_positions": len(position_ids),
                "summary": summary,
                "positions": categorized,
                "hitl_positions": [p for p in audit_result.get("results", []) 
                                  if p.get("hitl_required")],
                "audit_results": audit_result
            }
            
        except Exception as e:
            logger.error(f"Workflow A failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "positions": []
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
