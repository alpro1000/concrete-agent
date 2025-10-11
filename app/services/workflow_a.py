"""
Workflow A: Import and Audit Construction Estimates
Simplified version - user selects positions to analyze
WITH specialized parsers for better accuracy
БЕЗ Claude fallback в парсерах - только для аудита!
"""
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional
import json

from app.core.claude_client import ClaudeClient
from app.core.config import settings

# ✅ Импортируем SmartParser
from app.parsers import SmartParser

logger = logging.getLogger(__name__)


class WorkflowA:
    """
    Simplified Workflow A: Import ALL positions, user selects what to analyze
    
    New workflow:
    1. Import all positions without limitations (БЕЗ Claude - бесплатно!)
    2. Display positions with checkboxes
    3. User selects positions to analyze
    4. Analyze only selected positions (С Claude - платно!)
    
    NOW WITH: Specialized parsers WITHOUT Claude fallback
    """
    
    def __init__(self):
        """Initialize Workflow A"""
        self.kb_dir = settings.KB_DIR
        
        # ✅ ПРАВИЛЬНО: SmartParser БЕЗ параметров
        self.smart_parser = SmartParser()
    
    async def import_and_prepare(
        self,
        file_path: Path,
        project_name: str
    ) -> Dict[str, Any]:
        """
        Import ALL positions from document without limitations
        ✅ БЕЗ Claude - парсинг бесплатный!
        
        Args:
            file_path: Path to document file
            project_name: Name of the project
        
        Returns:
            Dict with all imported positions
        """
        try:
            logger.info(f"Importing positions from: {file_path}")
            
            file_format = self._detect_format(file_path)
            logger.info(f"Detected file format: {file_format}")
            
            # ✅ Используем SmartParser - он сам выберет оптимальный метод
            positions = await self._parse_document(file_path, file_format)
            logger.info(f"Imported {len(positions)} positions")
            
            if not positions:
                logger.warning("No positions found in document!")
                return {
                    "success": False,
                    "error": "No positions found in document",
                    "positions": []
                }
            
            # Add index and selected flag
            for idx, pos in enumerate(positions):
                pos['index'] = idx
                pos['selected'] = False
            
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
        ✅ С Claude - платный аудит!
        """
        try:
            logger.info(f"Analyzing {len(selected_indices)} selected positions")
            
            selected_positions = [positions[i] for i in selected_indices if i < len(positions)]
            
            if not selected_positions:
                return {
                    "success": False,
                    "error": "No valid positions selected",
                    "results": []
                }
            
            # Load knowledge base
            kb_data = self._load_knowledge_base()
            logger.info(f"Loaded KB with {len(kb_data)} categories")
            
            results = []
            for idx, position in enumerate(selected_positions, 1):
                logger.info(f"Analyzing position {idx}/{len(selected_positions)}")
                
                try:
                    # ✅ Аудит С Claude - это платная часть
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
        """Detect file format by extension"""
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
        Parse document using specialized parsers
        ✅ БЕЗ Claude - парсинг бесплатный!
        """
        try:
            logger.info(f"Parsing {file_format} document with specialized parser")
            
            # ✅ SmartParser автоматически выберет оптимальный метод
            if file_format == 'excel':
                result = self.smart_parser.parse_excel(file_path)
            elif file_format == 'xml':
                result = self.smart_parser.parse_xml(file_path)
            elif file_format == 'pdf':
                result = self.smart_parser.parse_pdf(file_path)
            else:
                raise ValueError(f"Unsupported format: {file_format}")
            
            positions = result.get('positions', [])
            logger.info(f"Parsed {len(positions)} positions")
            
            # Validate positions
            valid_positions = []
            for pos in positions:
                if self._is_valid_position(pos):
                    valid_positions.append(pos)
                else:
                    logger.warning(f"Skipping invalid position")
            
            logger.info(f"{len(valid_positions)} valid positions after validation")
            return valid_positions
        
        except Exception as e:
            logger.error(f"Failed to parse document: {e}", exc_info=True)
            # ✅ Просто выбрасываем ошибку - БЕЗ Claude fallback!
            raise
    
    def _is_valid_position(self, position: Dict[str, Any]) -> bool:
        """Check if position has required fields"""
        return 'description' in position and position['description']
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load knowledge base data"""
        kb_data = {}
        
        # B1: KROS/URS codes
        b1_path = self.kb_dir / "B1_kros_urs_codes"
        if b1_path.exists():
            kb_data['codes'] = self._load_category(b1_path)
        
        # B2: CSN standards
        b2_path = self.kb_dir / "B2_csn_standards"
        if b2_path.exists():
            kb_data['standards'] = self._load_category(b2_path)
        
        # B3: Current prices
        b3_path = self.kb_dir / "B3_current_prices"
        if b3_path.exists():
            kb_data['prices'] = self._load_category(b3_path)
        
        return kb_data
    
    def _load_category(self, category_path: Path) -> List[Dict[str, Any]]:
        """Load JSON files from category directory"""
        data = []
        
        for json_file in category_path.glob("*.json"):
            if json_file.name == "metadata.json":
                continue
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
        ✅ С Claude - платная часть!
        """
        try:
            prompt = self._build_audit_prompt(position, kb_data, project_context)
            
            # ✅ Используем Claude для аудита
            claude = ClaudeClient()
            result = claude.call(prompt)
            
            result['position'] = position
            result.setdefault('classification', 'AMBER')
            result.setdefault('hitl_required', False)
            
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
        """Build audit prompt for Claude"""
        prompt = f"""Analyzuj tuto pozici stavebniho vykazu vymer a proved audit.

===== POZICE K AUDITU =====
{json.dumps(position, ensure_ascii=False, indent=2)}

===== KNOWLEDGE BASE =====
Dostupne kody KROS/URS: {len(kb_data.get('codes', []))} polozek
Dostupne CSN standardy: {len(kb_data.get('standards', []))} polozek
Aktualni ceny: {len(kb_data.get('prices', []))} polozek

===== UKOL =====
1. Zkontroluj kod pozice (KROS/URS)
2. Zkontroluj popis a jednotku
3. Zkontroluj cenu (pokud je uvedena)
4. Zkontroluj mnozstvi (pokud je uvedeno)
5. Identifikuj pripadne problemy

===== VYSTUP =====
Vrat JSON:
{{
  "classification": "GREEN/AMBER/RED",
  "issues": ["seznam problemu"],
  "recommendations": ["doporuceni"],
  "price_check": "OK/WARNING/ERROR",
  "code_check": "OK/WARNING/ERROR",
  "notes": "poznamky"
}}

Vrat POUZE JSON, bez markdown.
"""
        
        if project_context:
            prompt += f"\n\n===== KONTEXT PROJEKTU =====\n{json.dumps(project_context, ensure_ascii=False, indent=2)}\n"
        
        return prompt
    
    async def run(
        self,
        file_path: Path,
        project_name: str
    ) -> Dict[str, Any]:
        """
        Run complete Workflow A
        
        Args:
            file_path: Path to document file
            project_name: Project name
            
        Returns:
            Complete audit results
        """
        try:
            logger.info(f"Starting Workflow A for: {file_path}")
            
            import_result = await self.import_and_prepare(file_path, project_name)
            
            if not import_result.get("success"):
                return import_result
            
            positions = import_result.get("positions", [])
            
            if not positions:
                return {
                    "success": False,
                    "error": "No positions found in document",
                    "positions": []
                }
            
            logger.info(f"Auto-analyzing all {len(positions)} positions")
            position_ids = [i for i in range(len(positions))]
            
            audit_result = await self.analyze_selected_positions(
                positions=positions,
                selected_indices=position_ids,
                project_context=import_result.get("project_context", {})
            )
            
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
        """Categorize audit results by classification"""
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
        """Generate summary statistics"""
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
    
    async def execute(
        self,
        project_id: str,
        vykaz_path: Optional[Path],
        vykresy_paths: List[Path],
        project_name: str
    ) -> Dict[str, Any]:
        """
        Execute Workflow A with full project analysis
        
        Args:
            project_id: Project ID
            vykaz_path: Path to vykaz vymer (optional)
            vykresy_paths: List of paths to drawings
            project_name: Project name
            
        Returns:
            Complete project analysis results
        """
        try:
            logger.info(f"Starting execute() for project {project_id}")
            
            all_data = await self._collect_project_data(
                vykaz_path=vykaz_path,
                vykresy_paths=vykresy_paths,
                project_name=project_name
            )
            
            validated_positions = await self._basic_validation_with_urs(
                positions=all_data["positions"],
                project_id=project_id
            )
            
            project_context = await self._extract_project_context(
                drawings_data=all_data["drawings"],
                tech_specs=all_data["technical_specs"]
            )
            
            green_count = len([p for p in validated_positions if p.get("basic_status") == "OK"])
            amber_count = len([p for p in validated_positions if p.get("basic_status") == "WARNING"])
            red_count = len([p for p in validated_positions if p.get("basic_status") == "ERROR"])
            
            return {
                "success": True,
                "project_id": project_id,
                "total_positions": len(validated_positions),
                "positions": validated_positions,
                "project_context": project_context,
                "green_count": green_count,
                "amber_count": amber_count,
                "red_count": red_count,
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
        """Collect all project data from documents"""
        positions = []
        drawings_data = []
        technical_specs = []
        
        if vykaz_path and vykaz_path.exists():
            logger.info(f"Parsing vykaz vymer: {vykaz_path.name}")
            import_result = await self.import_and_prepare(vykaz_path, project_name)
            positions = import_result.get("positions", [])
            logger.info(f"Extracted {len(positions)} positions")
        
        for drawing_path in vykresy_paths:
            if drawing_path.exists():
                logger.info(f"Parsing drawing: {drawing_path.name}")
                try:
                    drawing_content = await self._parse_drawing_document(drawing_path)
                    drawings_data.append(drawing_content)
                    
                    tech_specs = self._extract_technical_specs(drawing_content)
                    technical_specs.extend(tech_specs)
                except Exception as e:
                    logger.warning(f"Failed to parse drawing: {e}")
        
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
        """Basic validation against local knowledge base"""
        from app.core.kb_loader import get_knowledge_base
        
        kb = get_knowledge_base()
        validated_positions = []
        
        for position in positions:
            kb_match = self._check_local_knowledge_base(position, kb)
            
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
        
        return validated_positions
    
    def _check_local_knowledge_base(
        self,
        position: Dict[str, Any],
        kb: Any
    ) -> Dict[str, Any]:
        """Check position against local knowledge base"""
        description = position.get("description", "").lower()
        unit_price = position.get("unit_price", 0)
        
        found = False
        matched_code = None
        kb_price = None
        price_variance = 100
        
        if hasattr(kb, 'data') and 'B1_kros_urs_codes' in kb.data:
            codes_data = kb.data['B1_kros_urs_codes']
            for item in codes_data if isinstance(codes_data, list) else []:
                if isinstance(item, dict):
                    item_desc = item.get("description", "").lower()
                    if any(word in item_desc for word in description.split()[:3]):
                        found = True
                        matched_code = item.get("code")
                        break
        
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
        """Parse drawing document to extract text and metadata"""
        drawing_data = {
            "filename": drawing_path.name,
            "path": str(drawing_path),
            "text": "",
            "format": drawing_path.suffix.lower()
        }
        
        if drawing_path.suffix.lower() == '.pdf':
            try:
                # ✅ Use SmartParser for PDF
                result = self.smart_parser.parse_pdf(drawing_path)
                drawing_data["text"] = result.get("raw_text", "")
                drawing_data["metadata"] = result.get("document_info", {})
            except Exception as e:
                logger.warning(f"PDF parsing failed: {e}")
        elif drawing_path.suffix.lower() == '.txt':
            try:
                with open(drawing_path, 'r', encoding='utf-8') as f:
                    drawing_data["text"] = f.read()
            except Exception as e:
                logger.warning(f"TXT parsing failed: {e}")
        
        return drawing_data
    
    def _extract_technical_specs(self, drawing_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract technical specifications from drawing text"""
        specs = []
        text = drawing_content.get("text", "")
        
        if not text:
            return specs
        
        import re
        
        # Extract concrete grades (e.g., C25/30)
        concrete_pattern = r'C\d{2}/\d{2}'
        concrete_grades = re.findall(concrete_pattern, text)
        for grade in set(concrete_grades):
            specs.append({
                "type": "concrete_grade",
                "value": grade,
                "source": drawing_content.get("filename", "unknown")
            })
        
        # Extract environmental classes (e.g., XC3, XD1)
        env_pattern = r'X[A-Z]\d'
        env_classes = re.findall(env_pattern, text)
        for env_class in set(env_classes):
            specs.append({
                "type": "environmental_class",
                "value": env_class,
                "source": drawing_content.get("filename", "unknown")
            })
        
        # Extract CSN standards (e.g., CSN EN 206)
        csn_pattern = r'CSN\s+(?:EN\s+)?\d+'
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
        """Extract project context from drawings and technical specs"""
        context = {
            "construction_type": None,
            "concrete_grades": [],
            "environmental_classes": [],
            "special_conditions": [],
            "formwork_requirements": {},
            "csn_standards": []
        }
        
        # Extract from technical specs
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
        
        # Use Claude to analyze drawings if available
        if drawings_data and settings.ANTHROPIC_API_KEY:
            try:
                claude = ClaudeClient()
                
                for drawing in drawings_data:
                    if drawing.get("text"):
                        context_prompt = f"""Analyzuj tento stavebni dokument a extrahuj klicove technicke informace:

Dokument: {drawing.get("filename", "unknown")}

Text (prvnich 2000 znaku):
{drawing.get("text", "")[:2000]}

Najdi a vrat v JSON formatu:
{{
  "construction_type": "typ stavby",
  "special_conditions": ["specialni podminky"],
  "formwork_requirements": {{"kategorie": "kategorie povrchu"}}
}}

Vrat POUZE JSON, bez markdown.
"""
                        
                        analysis_result = claude.call(context_prompt)
                        
                        if isinstance(analysis_result, str):
                            try:
                                parsed = json.loads(analysis_result)
                                context.update(parsed)
                            except:
                                pass
                        elif isinstance(analysis_result, dict):
                            context.update(analysis_result)
                        
                        break
                        
            except Exception as e:
                logger.warning(f"Claude analysis failed: {e}")
        
        return context
