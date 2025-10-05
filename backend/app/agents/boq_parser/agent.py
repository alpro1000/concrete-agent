"""
BOQ Parser Agent - Bill of Quantities parser.
"""

from typing import Dict, Any
from backend.app.agents.base_agent import BaseAgent, AgentResult
from backend.app.core.logging_config import app_logger


class BOQParserAgent(BaseAgent):
    """
    BOQ (Bill of Quantities) Parser Agent.
    Parses construction bill of quantities documents and extracts items.
    """
    
    name = "boq_parser"
    description = "Parses bill of quantities (BOQ/výkaz výměr) documents"
    version = "1.0.0"
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute BOQ parsing.
        
        Expected input_data:
            - document: Text content of BOQ document
            - options: Optional parsing options
        
        Returns:
            AgentResult with parsed BOQ items
        """
        try:
            # Validate input
            self.validate_input(input_data, required_fields=["document"])
            
            document = input_data.get("document", "")
            options = input_data.get("options", {})
            
            # Clear previous reasoning chain
            self.clear_reasoning_chain()
            
            # Step 1: Hypothesis
            hypothesis = await self.hypothesis(
                problem="Parse BOQ document and extract line items with quantities and prices",
                context={"document_length": len(document), "options": options}
            )
            
            # Step 2: Reasoning - Parse document
            reasoning_result = await self.reasoning(
                hypothesis=hypothesis,
                data={"document": document}
            )
            
            # Step 3: Parse items
            parsed_items = self._parse_boq_items(document)
            
            # Step 4: Verification
            verification_passed = await self.verification(
                reasoning=reasoning_result,
                expected_output=parsed_items
            )
            
            # Step 5: Conclusion
            conclusion = await self.conclusion(
                reasoning=reasoning_result,
                verification_passed=verification_passed
            )
            
            # Calculate totals
            total_cost = sum(item.get("total_price", 0) for item in parsed_items)
            
            # Return result
            return AgentResult(
                success=True,
                data={
                    "items": parsed_items,
                    "summary": {
                        "item_count": len(parsed_items),
                        "total_cost": total_cost
                    },
                    "conclusion": conclusion
                },
                reasoning_chain=self.get_reasoning_chain(),
                metadata={
                    "agent": self.name,
                    "version": self.version
                }
            )
            
        except Exception as e:
            app_logger.error(f"BOQ Parser execution failed: {e}")
            return AgentResult(
                success=False,
                data={},
                errors=[str(e)],
                reasoning_chain=self.get_reasoning_chain()
            )
    
    def _parse_boq_items(self, document: str) -> list:
        """
        Parse BOQ items from document.
        
        Args:
            document: Document text
            
        Returns:
            List of parsed BOQ items
        """
        items = []
        lines = document.split('\n')
        
        current_item = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Simple parsing logic (to be enhanced with LLM)
            # Look for lines with item numbers
            if line[0].isdigit():
                if current_item:
                    items.append(current_item)
                
                parts = line.split()
                current_item = {
                    "item_number": parts[0] if parts else "",
                    "description": " ".join(parts[1:]) if len(parts) > 1 else "",
                    "quantity": 0,
                    "unit": "",
                    "unit_price": 0,
                    "total_price": 0
                }
            elif current_item and any(keyword in line.lower() for keyword in ['ks', 'm2', 'm3', 'm', 'kg', 't']):
                # Try to extract quantity and unit
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.replace(',', '').replace('.', '').isdigit():
                        try:
                            current_item["quantity"] = float(part.replace(',', '.'))
                            if i + 1 < len(parts):
                                current_item["unit"] = parts[i + 1]
                        except ValueError:
                            pass
        
        if current_item:
            items.append(current_item)
        
        return items
