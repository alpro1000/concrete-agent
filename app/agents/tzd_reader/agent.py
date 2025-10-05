"""
TZD Reader Agent - Technical Requirements Document parser.
"""

from typing import Dict, Any
from app.agents.base_agent import BaseAgent, AgentResult
from app.core.logging_config import app_logger


class TZDReaderAgent(BaseAgent):
    """
    TZD (Technická Zadávací Dokumentace) Reader Agent.
    Parses technical requirements documents and extracts key information.
    """
    
    name = "tzd_reader"
    description = "Parses technical requirements documents (TZD)"
    version = "1.0.0"
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute TZD document parsing.
        
        Expected input_data:
            - document: Text content of TZD document
            - options: Optional parsing options
        
        Returns:
            AgentResult with parsed TZD data
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
                problem="Parse TZD document and extract structured information",
                context={"document_length": len(document), "options": options}
            )
            
            # Step 2: Reasoning - Parse document
            reasoning_result = await self.reasoning(
                hypothesis=hypothesis,
                data={"document": document}
            )
            
            # Step 3: Verification
            parsed_data = self._parse_document(document)
            verification_passed = await self.verification(
                reasoning=reasoning_result,
                expected_output=parsed_data
            )
            
            # Step 4: Conclusion
            conclusion = await self.conclusion(
                reasoning=reasoning_result,
                verification_passed=verification_passed
            )
            
            # Return result
            return AgentResult(
                success=True,
                data={
                    "parsed_data": parsed_data,
                    "conclusion": conclusion,
                    "document_info": {
                        "length": len(document),
                        "sections": len(parsed_data.get("sections", []))
                    }
                },
                reasoning_chain=self.get_reasoning_chain(),
                metadata={
                    "agent": self.name,
                    "version": self.version
                }
            )
            
        except Exception as e:
            app_logger.error(f"TZD Reader execution failed: {e}")
            return AgentResult(
                success=False,
                data={},
                errors=[str(e)],
                reasoning_chain=self.get_reasoning_chain()
            )
    
    def _parse_document(self, document: str) -> Dict[str, Any]:
        """
        Parse TZD document structure.
        
        Args:
            document: Document text
            
        Returns:
            Parsed document data
        """
        # Basic parsing logic (to be enhanced with LLM)
        lines = document.split('\n')
        
        sections = []
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect section headers (lines ending with :)
            if line.endswith(':') or line.isupper():
                if current_section:
                    sections.append(current_section)
                current_section = {
                    "title": line.rstrip(':'),
                    "content": []
                }
            elif current_section:
                current_section["content"].append(line)
        
        if current_section:
            sections.append(current_section)
        
        return {
            "sections": sections,
            "total_lines": len(lines),
            "document_type": "TZD"
        }
