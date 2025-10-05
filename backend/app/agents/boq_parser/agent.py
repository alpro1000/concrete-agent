"""
BOQParserAgent - Agent for parsing Czech Bill of Quantities (BOQ/výkaz výměr).

This agent reads XLS/XLSX files containing Czech BOQ data and extracts:
- Work items with descriptions
- KROS4 codes (Czech construction classification)
- URS codes (Unit Rate System codes)
- Quantities and units
- Prices and totals

Returns structured JSON data for further processing.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class BOQParserAgent:
    """
    Agent for parsing Czech Bill of Quantities (BOQ) documents.
    
    Processes XLS/XLSX files containing výkaz výměr (BOQ) with:
    - KROS4 codes (Klasifikační systém rozpočtových ukazatelů staveb)
    - URS codes (Jednotkový rozpočtový systém)
    - Work descriptions in Czech
    - Quantities, units, and prices
    """
    
    def __init__(self, prompt_path: Optional[str] = None):
        """
        Initialize the BOQParserAgent.
        
        Args:
            prompt_path: Path to the BOQ parsing prompt file.
                        Defaults to prompts/boq.txt
        """
        self.prompt_path = prompt_path or "prompts/boq.txt"
        self.prompt_template = self._load_prompt()
        
    def _load_prompt(self) -> str:
        """Load the BOQ parsing prompt template."""
        try:
            prompt_file = Path(self.prompt_path)
            if prompt_file.exists():
                return prompt_file.read_text(encoding='utf-8')
            else:
                return self._get_default_prompt()
        except Exception as e:
            print(f"Warning: Could not load prompt from {self.prompt_path}: {e}")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Return default BOQ parsing prompt."""
        return """Parse Czech Bill of Quantities (výkaz výměr) and extract:
1. Work item descriptions
2. KROS4 classification codes
3. URS unit rate codes
4. Quantities and measurement units
5. Unit prices and total costs

Return structured JSON format."""
    
    def parse_boq(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a BOQ file (XLS/XLSX) and extract work items.
        
        Args:
            file_path: Path to the BOQ file (XLS or XLSX)
            
        Returns:
            Dictionary containing parsed BOQ data in JSON format:
            {
                "file_name": str,
                "total_items": int,
                "work_items": [
                    {
                        "id": str,
                        "description": str,
                        "kros4_code": str,
                        "urs_code": str,
                        "quantity": float,
                        "unit": str,
                        "unit_price": float,
                        "total_price": float
                    },
                    ...
                ],
                "summary": {
                    "total_cost": float,
                    "currency": str
                }
            }
        """
        # This is a placeholder implementation
        # In production, this would use actual Excel parsing libraries
        # (openpyxl, pandas, etc.) and LLM for intelligent extraction
        
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"BOQ file not found: {file_path}")
        
        if not file_path_obj.suffix.lower() in ['.xls', '.xlsx']:
            raise ValueError(f"Unsupported file format: {file_path_obj.suffix}. Expected .xls or .xlsx")
        
        # Placeholder response structure
        result = {
            "file_name": file_path_obj.name,
            "total_items": 0,
            "work_items": [],
            "summary": {
                "total_cost": 0.0,
                "currency": "CZK"
            },
            "metadata": {
                "parsed_at": "timestamp",
                "agent": "BOQParserAgent",
                "version": "1.0"
            }
        }
        
        return result
    
    def parse_boq_from_bytes(self, file_bytes: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse a BOQ file from bytes.
        
        Args:
            file_bytes: Bytes content of the BOQ file
            file_name: Original file name
            
        Returns:
            Dictionary containing parsed BOQ data in JSON format
        """
        # This would handle in-memory parsing
        # Useful for API uploads without saving to disk
        
        result = {
            "file_name": file_name,
            "total_items": 0,
            "work_items": [],
            "summary": {
                "total_cost": 0.0,
                "currency": "CZK"
            },
            "metadata": {
                "parsed_at": "timestamp",
                "agent": "BOQParserAgent",
                "version": "1.0",
                "source": "bytes"
            }
        }
        
        return result
    
    def validate_kros4_code(self, code: str) -> bool:
        """
        Validate KROS4 classification code format.
        
        Args:
            code: KROS4 code to validate
            
        Returns:
            True if code format is valid, False otherwise
        """
        # KROS4 codes typically follow format like: 801.11.12
        # This is a simplified validation
        if not code:
            return False
        
        parts = code.split('.')
        return len(parts) >= 2 and all(part.isdigit() for part in parts)
    
    def validate_urs_code(self, code: str) -> bool:
        """
        Validate URS (Unit Rate System) code format.
        
        Args:
            code: URS code to validate
            
        Returns:
            True if code format is valid, False otherwise
        """
        # URS codes vary in format, basic validation
        if not code:
            return False
        
        # URS codes are typically alphanumeric with dots/dashes
        return len(code) > 0 and not code.isspace()
    
    def export_to_json(self, parsed_data: Dict[str, Any], output_path: str) -> None:
        """
        Export parsed BOQ data to JSON file.
        
        Args:
            parsed_data: Parsed BOQ data dictionary
            output_path: Path where to save the JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
    
    def get_work_item_by_code(self, parsed_data: Dict[str, Any], 
                               kros4_code: Optional[str] = None,
                               urs_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find work items by KROS4 or URS code.
        
        Args:
            parsed_data: Parsed BOQ data dictionary
            kros4_code: KROS4 code to search for
            urs_code: URS code to search for
            
        Returns:
            List of matching work items
        """
        work_items = parsed_data.get("work_items", [])
        results = []
        
        for item in work_items:
            if kros4_code and item.get("kros4_code") == kros4_code:
                results.append(item)
            elif urs_code and item.get("urs_code") == urs_code:
                results.append(item)
        
        return results


# Example usage
if __name__ == "__main__":
    # Example of how to use the BOQParserAgent
    agent = BOQParserAgent()
    
    # Example parsing a file
    try:
        result = agent.parse_boq("sample_boq.xlsx")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error parsing BOQ: {e}")
