"""
Knowledge Base Agent - Standards and Materials Database Access
Provides access to Czech standards (ČSN), KROS codes, materials database, and labor norms
"""

from typing import Dict, Any, List, Optional
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeBaseAgent:
    """
    Knowledge Base Agent
    
    Provides access to:
    - Czech standards (ČSN EN)
    - KROS/URS budget codes
    - Materials database
    - Labor norms
    """
    
    name = "knowledge_base"
    supported_types = [
        "standards_lookup",
        "materials_lookup",
        "codes_lookup",
        "norms_lookup"
    ]
    
    def __init__(self):
        """Initialize Knowledge Base Agent"""
        logger.info("KnowledgeBaseAgent initialized")
        
        # Load knowledge base data
        self.standards = self._load_standards()
        self.materials = self._load_materials()
        self.codes = self._load_codes()
    
    def _load_standards(self) -> Dict[str, Any]:
        """Load standards from knowledge base"""
        kb_path = Path("/home/runner/work/concrete-agent/concrete-agent/knowledgebase")
        standards_file = kb_path / "standards" / "csn.json"
        
        if standards_file.exists():
            try:
                with open(standards_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load standards: {e}")
        
        # Return default standards
        return {
            "standards": [
                {
                    "code": "ČSN EN 206",
                    "title": "Beton - Specifikace, vlastnosti, výroba a shoda",
                    "category": "concrete"
                },
                {
                    "code": "ČSN 73 1001",
                    "title": "Zakládání staveb - Základová půda pod plošnými základy",
                    "category": "foundations"
                }
            ]
        }
    
    def _load_materials(self) -> Dict[str, Any]:
        """Load materials database"""
        kb_path = Path("/home/runner/work/concrete-agent/concrete-agent/knowledgebase")
        materials_file = kb_path / "materials" / "base.json"
        
        if materials_file.exists():
            try:
                with open(materials_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load materials: {e}")
        
        # Return default materials
        return {
            "materials": [
                {
                    "name": "Concrete C25/30",
                    "type": "concrete",
                    "properties": {"strength": "C25/30", "density": 2400}
                },
                {
                    "name": "Steel B500B",
                    "type": "reinforcement",
                    "properties": {"grade": "B500B", "yield_strength": 500}
                }
            ]
        }
    
    def _load_codes(self) -> Dict[str, Any]:
        """Load KROS/URS codes"""
        kb_path = Path("/home/runner/work/concrete-agent/concrete-agent/knowledgebase")
        codes_file = kb_path / "standards" / "urs_kros_codes.json"
        
        if codes_file.exists():
            try:
                with open(codes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load codes: {e}")
        
        # Return default codes
        return {
            "codes": [
                {
                    "code": "111",
                    "description": "Zemní práce",
                    "category": "earthworks"
                },
                {
                    "code": "211",
                    "description": "Základy a zvláštní zakládání",
                    "category": "foundations"
                }
            ]
        }
    
    def _search_standards(self, query: str) -> List[Dict[str, Any]]:
        """Search for standards matching query"""
        results = []
        query_lower = query.lower()
        
        for standard in self.standards.get("standards", []):
            if (query_lower in standard.get("code", "").lower() or 
                query_lower in standard.get("title", "").lower() or
                query_lower in standard.get("category", "").lower()):
                results.append(standard)
        
        return results
    
    def _search_materials(self, query: str) -> List[Dict[str, Any]]:
        """Search for materials matching query"""
        results = []
        query_lower = query.lower()
        
        for material in self.materials.get("materials", []):
            if (query_lower in material.get("name", "").lower() or 
                query_lower in material.get("type", "").lower()):
                results.append(material)
        
        return results
    
    def _search_codes(self, query: str) -> List[Dict[str, Any]]:
        """Search for KROS/URS codes matching query"""
        results = []
        query_lower = query.lower()
        
        for code in self.codes.get("codes", []):
            if (query_lower in code.get("code", "").lower() or 
                query_lower in code.get("description", "").lower() or
                query_lower in code.get("category", "").lower()):
                results.append(code)
        
        return results
    
    async def analyze(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query the knowledge base.
        
        Args:
            query_data: Dictionary with query parameters:
                - query: Search query string
                - type: Type of lookup (standards/materials/codes)
            
        Returns:
            Dictionary with search results
        """
        try:
            query = query_data.get("query", "")
            lookup_type = query_data.get("type", "all")
            
            results = {
                "standards": [],
                "materials": [],
                "codes": []
            }
            
            if lookup_type in ["standards", "all"]:
                results["standards"] = self._search_standards(query)
            
            if lookup_type in ["materials", "all"]:
                results["materials"] = self._search_materials(query)
            
            if lookup_type in ["codes", "all"]:
                results["codes"] = self._search_codes(query)
            
            result = {
                "results": results,
                "query": query,
                "total_results": (len(results["standards"]) + 
                                len(results["materials"]) + 
                                len(results["codes"])),
                "processing_metadata": {
                    "agent": self.name,
                    "status": "searched"
                }
            }
            
            logger.info(f"Knowledge base searched: {result['total_results']} results for '{query}'")
            return result
            
        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}")
            return {
                "results": {"standards": [], "materials": [], "codes": []},
                "total_results": 0,
                "error": str(e),
                "processing_metadata": {
                    "agent": self.name,
                    "status": "failed"
                }
            }
    
    def supports_type(self, file_type: str) -> bool:
        """Check if this agent supports a given file type"""
        return file_type.lower() in [t.lower() for t in self.supported_types]
    
    def __repr__(self) -> str:
        """String representation of the agent"""
        return f"KnowledgeBaseAgent(name='{self.name}', supported_types={self.supported_types})"
