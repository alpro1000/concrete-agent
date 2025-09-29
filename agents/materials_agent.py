import re
import json
import logging
from typing import List, Dict, Any, Optional
import sys
import os

# Add path for new modules
sys.path.append('/home/runner/work/concrete-agent/concrete-agent')

from parsers.doc_parser import DocParser
from app.core.llm_service import get_llm_service
from app.core.prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)

class MaterialsAgent:
    """
    Refactored Materials Agent using centralized LLM service
    """
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.prompt_loader = get_prompt_loader()
        self.parser = DocParser()
        
        # Load patterns from new prompt system
        try:
            # Try to load from old prompts folder first for backward compatibility
            with open("prompts/materials_prompt.json", encoding="utf-8") as f:
                materials_data = json.load(f)
                self.patterns = materials_data.get("patterns", {})
        except FileNotFoundError:
            # Use fallback patterns
            self.patterns = {
                "reinforcement": {
                    "regex": r"\b(výztuž|Fe\s?\d{3}|R\d{2,3}|ocel|арматура|Fe500|B500B)\b",
                    "description": "Арматура и стальные элементы"
                },
                "windows": {
                    "regex": r"\b(okno|okna|PVC|dřevo|sklo|окно|окна|стекло)\b",
                    "description": "Окна и остекление"
                },
                "seals": {
                    "regex": r"\b(těsnění|těsnicí|pryž|guma|EPDM|уплотнение|герметик)\b",
                    "description": "Уплотнительные материалы"
                },
                "metal_structures": {
                    "regex": r"\b(konstrukce z oceli|kovová konstrukce|ocelový rám|nosník|металлоконструкции)\b",
                    "description": "Металлические конструкции"
                },
                "concrete": {
                    "regex": r"\b(beton|C\d{1,2}/\d{1,2}|LC\d{1,2}/\d{1,2}|бетон)\b",
                    "description": "Бетон и бетонные смеси"
                },
                "insulation": {
                    "regex": r"\b(izolace|tepelná izolace|polystyren|пенопласт|утеплитель)\b",
                    "description": "Изоляционные материалы"
                }
            }
        
    async def analyze_with_llm(self, text: str) -> Dict[str, Any]:
        """
        Enhanced analysis using LLM service
        """
        try:
            system_prompt = self.prompt_loader.get_system_prompt("materials")
            prompt_config = self.prompt_loader.get_prompt_config("materials")
            
            provider = prompt_config.get("provider", "claude")
            model = prompt_config.get("model")
            
            user_prompt = f"""
            Analyze this construction document text and identify all building materials (excluding concrete).
            Focus on: reinforcement, windows, insulation, sealing materials, metal structures.
            
            Text to analyze:
            {text[:15000]}  # Limit text length
            
            Return results in structured JSON format with material categories and specifications.
            """
            
            response = await self.llm_service.run_prompt(
                provider=provider,
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=model
            )
            
            if response.get("success"):
                return {
                    "llm_analysis": response.get("content", ""),
                    "provider": provider,
                    "model": response.get("model", ""),
                    "success": True
                }
            else:
                return {
                    "llm_analysis": "",
                    "error": response.get("error", "Unknown error"),
                    "success": False
                }
                
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {
                "llm_analysis": "",
                "error": str(e),
                "success": False
            }
    
    async def analyze_materials_enhanced(self, doc_paths: List[str]) -> Dict[str, Any]:
        """
        Enhanced materials analysis using both pattern matching and LLM
        """
        all_text = ""
        
        # Parse documents
        for path in doc_paths:
            try:
                text = self.parser.parse(path)
                all_text += "\n" + text
            except Exception as e:
                logger.error(f"Error parsing {path}: {e}")
        
        # Pattern-based analysis (legacy)
        pattern_results = []
        for category, pattern_data in self.patterns.items():
            if isinstance(pattern_data, dict):
                pattern = pattern_data.get("regex", pattern_data.get("pattern", ""))
                description = pattern_data.get("description", category)
            else:
                pattern = pattern_data
                description = category
                
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                pattern_results.append({
                    "type": category,
                    "description": description,
                    "found_terms": sorted(set(matches)),
                    "total_mentions": len(matches)
                })
        
        # LLM-based analysis (enhanced)
        llm_analysis = await self.analyze_with_llm(all_text)
        
        return {
            "materials_found": pattern_results,
            "document_count": len(doc_paths),
            "documents_processed": [os.path.basename(path) for path in doc_paths],
            "llm_analysis": llm_analysis,
            "analysis_method": "hybrid_pattern_llm",
            "text_length": len(all_text)
        }

# Create instance for backward compatibility
_materials_agent = None

def get_materials_agent() -> MaterialsAgent:
    """Get global MaterialsAgent instance"""
    global _materials_agent
    if _materials_agent is None:
        _materials_agent = MaterialsAgent()
    return _materials_agent

# Legacy function for backward compatibility
def analyze_materials(doc_paths: list[str]) -> dict:
    """
    Legacy function - now uses enhanced MaterialsAgent
    """
    import asyncio
    
    agent = get_materials_agent()
    
    # For backward compatibility, run async function in sync context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create new event loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, agent.analyze_materials_enhanced(doc_paths))
                return future.result()
        else:
            return loop.run_until_complete(agent.analyze_materials_enhanced(doc_paths))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(agent.analyze_materials_enhanced(doc_paths))
