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
    
    # ========================================
    # NEW: EXECUTE METHOD FOR INTELLIGENT SYSTEM
    # ========================================
    
    async def execute(
        self,
        project_id: str,
        vykaz_path: Optional[Path],
        vykresy_paths: List[Path],
        project_name: str
    ) -> Dict[str, Any]:
        """
        PHASE 1: Basic data collection and preparation for intelligent queries
        
        This method implements the intelligent system approach:
        1. Parse all documents → structured data
        2. Basic validation → quick URS code checks
        3. Prepare context → for intelligent prompts
        4. URS integration → dual validation (local KB + podminky.urs.cz)
        
        Args:
            project_id: Project ID
            vykaz_path: Path to vykaz vymer (optional for Workflow B)
            vykresy_paths: List of paths to drawings
            project_name: Project name
        
        Returns:
            Dict with collected data and validation results
        """
        try:
            logger.info(f"🚀 Starting execute() for project {project_id}")
            
            # 1. COLLECT ALL PROJECT DATA
            all_data = await self._collect_project_data(
                vykaz_path=vykaz_path,
                vykresy_paths=vykresy_paths,
                project_name=project_name
            )
            
            # 2. BASIC VALIDATION WITH URS
            validated_positions = await self._basic_validation_with_urs(
                positions=all_data["positions"],
                project_id=project_id
            )
            
            # 3. PREPARE PROJECT CONTEXT
            project_context = await self._extract_project_context(
                drawings_data=all_data["drawings"],
                tech_specs=all_data["technical_specs"]
            )
            
            # 4. URS INTEGRATION - Dual validation with Perplexity
            if settings.PERPLEXITY_API_KEY and settings.ALLOW_WEB_SEARCH:
                try:
                    from app.core.perplexity_client import PerplexityClient
                    perplexity = PerplexityClient()
                    
                    logger.info("🔍 Starting dual URS validation (local KB + podminky.urs.cz)")
                    
                    for pos in validated_positions:
                        try:
                            # Search on podminky.urs.cz
                            urs_result = await perplexity.search_kros_code(
                                description=pos.get("description", ""),
                                quantity=pos.get("quantity"),
                                unit=pos.get("unit")
                            )
                            
                            pos["urs_validation"] = {
                                "local_kb": pos.get("kb_match", {}),
                                "online_urs": {
                                    "found": urs_result.get("found", False),
                                    "codes": urs_result.get("codes", []),
                                    "confidence": urs_result.get("confidence", 0),
                                    "source": "podminky.urs.cz"
                                }
                            }
                        except Exception as e:
                            logger.warning(f"URS online validation failed for position: {e}")
                            pos["urs_validation"] = {
                                "local_kb": pos.get("kb_match", {}),
                                "online_urs": {
                                    "found": False,
                                    "error": str(e)
                                }
                            }
                
                except Exception as e:
                    logger.warning(f"Perplexity integration failed: {e}")
            else:
                logger.info("ℹ️  Perplexity not configured, using local KB only")
            
            # 5. CALCULATE REAL STATISTICS
            green_count = len([p for p in validated_positions if p.get("basic_status") == "OK"])
            amber_count = len([p for p in validated_positions if p.get("basic_status") == "WARNING"])
            red_count = len([p for p in validated_positions if p.get("basic_status") == "ERROR"])
            
            logger.info(
                f"✅ Execute complete: {len(validated_positions)} positions "
                f"(Green: {green_count}, Amber: {amber_count}, Red: {red_count})"
            )
            
            return {
                "success": True,
                "project_id": project_id,
                "total_positions": len(validated_positions),
                "positions": validated_positions,
                "project_context": project_context,
                "green_count": green_count,
                "amber_count": amber_count,
                "red_count": red_count,
                "urs_validation": {
                    "local_kb_matches": len([p for p in validated_positions if p.get("kb_match", {}).get("found")]),
                    "online_matches": len([p for p in validated_positions if p.get("urs_validation", {}).get("online_urs", {}).get("found")]),
                    "total_validated": len(validated_positions)
                },
                "ready_for_analysis": True
            }
            
        except Exception as e:
            logger.error(f"Execute failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "project_id": project_id
            }
    
    async def _collect_project_data(
        self,
        vykaz_path: Optional[Path],
        vykresy_paths: List[Path],
        project_name: str
    ) -> Dict[str, Any]:
        """
        Collect all data from documents
        
        Args:
            vykaz_path: Path to vykaz vymer
            vykresy_paths: List of paths to drawings
            project_name: Project name
        
        Returns:
            Dict with positions, drawings, and technical specs
        """
        positions = []
        drawings_data = []
        technical_specs = []
        
        # Parse vykaz vymer if provided
        if vykaz_path and vykaz_path.exists():
            logger.info(f"📄 Parsing vykaz vymer: {vykaz_path.name}")
            import_result = await self.import_and_prepare(vykaz_path, project_name)
            positions = import_result.get("positions", [])
            logger.info(f"✅ Extracted {len(positions)} positions from vykaz")
        else:
            logger.info("ℹ️  No vykaz vymer provided")
        
        # Parse drawings
        for drawing_path in vykresy_paths:
            if drawing_path.exists():
                logger.info(f"📐 Parsing drawing: {drawing_path.name}")
                try:
                    drawing_content = await self._parse_drawing_document(drawing_path)
                    drawings_data.append(drawing_content)
                    
                    # Extract technical specifications
                    tech_specs = self._extract_technical_specs(drawing_content)
                    technical_specs.extend(tech_specs)
                    
                    logger.info(f"✅ Parsed drawing with {len(tech_specs)} technical specs")
                except Exception as e:
                    logger.warning(f"Failed to parse drawing {drawing_path.name}: {e}")
        
        logger.info(
            f"📊 Data collection complete: {len(positions)} positions, "
            f"{len(drawings_data)} drawings, {len(technical_specs)} specs"
        )
        
        return {
            "positions": positions,
            "drawings": drawings_data,
            "technical_specs": technical_specs
        }
    
    async def _basic_validation_with_urs(
        self,
        positions: List[Dict[str, Any]],
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Basic validation with Knowledge Base check
        
        Args:
            positions: List of positions to validate
            project_id: Project ID
        
        Returns:
            Validated positions with status
        """
        from app.core.kb_loader import get_knowledge_base
        
        kb = get_knowledge_base()
        validated_positions = []
        
        logger.info(f"🔍 Validating {len(positions)} positions against KB")
        
        for position in positions:
            # Check against local KB
            kb_match = self._check_local_knowledge_base(position, kb)
            
            # Basic categorization
            if kb_match.get("found") and kb_match.get("price_variance", 0) <= 10:
                basic_status = "OK"
            elif kb_match.get("found") and kb_match.get("price_variance", 0) <= 20:
                basic_status = "WARNING"
            else:
                basic_status = "ERROR"
            
            position.update({
                "kb_match": kb_match,
                "basic_status": basic_status
            })
            
            validated_positions.append(position)
        
        ok_count = len([p for p in validated_positions if p.get("basic_status") == "OK"])
        logger.info(f"✅ Validation complete: {ok_count}/{len(positions)} positions OK")
        
        return validated_positions
    
    def _check_local_knowledge_base(
        self,
        position: Dict[str, Any],
        kb: Any
    ) -> Dict[str, Any]:
        """
        Check position against local Knowledge Base
        
        Args:
            position: Position to check
            kb: Knowledge Base instance
        
        Returns:
            Match result with price variance
        """
        description = position.get("description", "").lower()
        unit_price = position.get("unit_price", 0)
        
        # Simple keyword matching (can be improved)
        # Check B1 (KROS codes) and B3 (prices)
        found = False
        matched_code = None
        kb_price = None
        price_variance = 100
        
        # Check KROS codes
        if hasattr(kb, 'data') and 'B1_kros_urs_codes' in kb.data:
            codes_data = kb.data['B1_kros_urs_codes']
            # Simple search - in production, use more sophisticated matching
            for item in codes_data if isinstance(codes_data, list) else []:
                if isinstance(item, dict):
                    item_desc = item.get("description", "").lower()
                    if any(word in item_desc for word in description.split()[:3]):
                        found = True
                        matched_code = item.get("code")
                        break
        
        # Check prices
        if hasattr(kb, 'data') and 'B3_current_prices' in kb.data and unit_price:
            prices_data = kb.data['B3_current_prices']
            for item in prices_data if isinstance(prices_data, list) else []:
                if isinstance(item, dict):
                    item_desc = item.get("description", "").lower()
                    if any(word in item_desc for word in description.split()[:3]):
                        kb_price = item.get("unit_price", 0)
                        if kb_price and unit_price:
                            price_variance = abs((unit_price - kb_price) / kb_price * 100)
                        break
        
        return {
            "found": found,
            "matched_code": matched_code,
            "kb_price": kb_price,
            "price_variance": price_variance
        }
    
    async def _parse_drawing_document(self, drawing_path: Path) -> Dict[str, Any]:
        """
        Parse drawing document to extract text and metadata
        
        Args:
            drawing_path: Path to drawing document
        
        Returns:
            Dict with drawing data
        """
        drawing_data = {
            "filename": drawing_path.name,
            "path": str(drawing_path),
            "text": "",
            "format": drawing_path.suffix.lower()
        }
        
        # Extract text based on format
        if drawing_path.suffix.lower() == '.pdf':
            try:
                # Use PDF parser
                result = self.pdf_parser.parse(drawing_path)
                drawing_data["text"] = result.get("text", "")
                drawing_data["metadata"] = result.get("metadata", {})
            except Exception as e:
                logger.warning(f"PDF parsing failed: {e}")
        elif drawing_path.suffix.lower() == '.txt':
            try:
                with open(drawing_path, 'r', encoding='utf-8') as f:
                    drawing_data["text"] = f.read()
            except Exception as e:
                logger.warning(f"TXT parsing failed: {e}")
        else:
            # For other formats (DWG, DXF, images), just store metadata
            logger.info(f"Format {drawing_path.suffix} - metadata only")
        
        return drawing_data
    
    def _extract_technical_specs(self, drawing_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract technical specifications from drawing content
        
        Args:
            drawing_content: Parsed drawing content
        
        Returns:
            List of technical specifications
        """
        specs = []
        text = drawing_content.get("text", "")
        
        if not text:
            return specs
        
        # Extract concrete grades (C20/25, C30/37, etc.)
        import re
        concrete_pattern = r'C\d{2}/\d{2}'
        concrete_grades = re.findall(concrete_pattern, text)
        
        for grade in set(concrete_grades):
            specs.append({
                "type": "concrete_grade",
                "value": grade,
                "source": drawing_content.get("filename", "unknown")
            })
        
        # Extract environmental classes (XA2, XF3, XC2, etc.)
        env_pattern = r'X[A-Z]\d'
        env_classes = re.findall(env_pattern, text)
        
        for env_class in set(env_classes):
            specs.append({
                "type": "environmental_class",
                "value": env_class,
                "source": drawing_content.get("filename", "unknown")
            })
        
        # Extract ČSN standards
        csn_pattern = r'ČSN\s+(?:EN\s+)?\d+'
        csn_standards = re.findall(csn_pattern, text)
        
        for standard in set(csn_standards):
            specs.append({
                "type": "csn_standard",
                "value": standard,
                "source": drawing_content.get("filename", "unknown")
            })
        
        return specs
    
    async def _extract_project_context(
        self,
        drawings_data: List[Dict[str, Any]],
        tech_specs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract project context for intelligent prompts
        
        Args:
            drawings_data: List of parsed drawing data
            tech_specs: List of technical specifications
        
        Returns:
            Project context dict
        """
        # Aggregate technical specifications
        context = {
            "construction_type": None,
            "concrete_grades": [],
            "environmental_classes": [],
            "special_conditions": [],
            "formwork_requirements": {},
            "csn_standards": []
        }
        
        # Group specs by type
        for spec in tech_specs:
            spec_type = spec.get("type")
            spec_value = spec.get("value")
            
            if spec_type == "concrete_grade":
                if spec_value not in context["concrete_grades"]:
                    context["concrete_grades"].append(spec_value)
            elif spec_type == "environmental_class":
                if spec_value not in context["environmental_classes"]:
                    context["environmental_classes"].append(spec_value)
            elif spec_type == "csn_standard":
                if spec_value not in context["csn_standards"]:
                    context["csn_standards"].append(spec_value)
        
        # Try to analyze with Claude if available
        if drawings_data and settings.ANTHROPIC_API_KEY:
            try:
                # Take first drawing with text
                for drawing in drawings_data:
                    if drawing.get("text"):
                        context_prompt = f"""
Analyzuj tento stavební dokument a extrahuj klíčové technické informace:

Dokument: {drawing.get("filename", "unknown")}

Text (prvních 2000 znaků):
{drawing.get("text", "")[:2000]}

Najdi a vrať v JSON formátu:
{{
  "construction_type": "typ stavby (např. 'základy', 'stěny', 'stropy')",
  "special_conditions": ["speciální podmínky nebo požadavky"],
  "formwork_requirements": {{"kategorie": "kategorie povrchu (např. C2d)"}}
}}

Vrať POUZE JSON, bez markdown.
"""
                        
                        analysis_result = self.claude.call(context_prompt)
                        
                        # Try to parse JSON from result
                        import json
                        if isinstance(analysis_result, str):
                            try:
                                parsed = json.loads(analysis_result)
                                context.update(parsed)
                            except:
                                pass
                        elif isinstance(analysis_result, dict):
                            context.update(analysis_result)
                        
                        # Only analyze first drawing with text
                        break
                        
            except Exception as e:
                logger.warning(f"Claude analysis failed: {e}")
        
        logger.info(
            f"📋 Project context extracted: "
            f"{len(context['concrete_grades'])} concrete grades, "
            f"{len(context['environmental_classes'])} env classes, "
            f"{len(context['csn_standards'])} CSN standards"
        )
        
        return context
