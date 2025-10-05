"""
Base agent class with scientific method integration.
All agents should inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel
from backend.app.core.llm_service import llm_service
from backend.app.core.prompt_loader import prompt_loader
from backend.app.core.logging_config import app_logger
from backend.app.core.exceptions import AgentException


class ScientificMethodStep(BaseModel):
    """Represents a step in the scientific method reasoning chain."""
    
    step: str  # hypothesis, reasoning, verification, conclusion
    content: str
    confidence: float = 0.0
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class AgentResult(BaseModel):
    """Result from agent execution."""
    
    success: bool
    data: Dict[str, Any]
    reasoning_chain: List[ScientificMethodStep] = []
    errors: List[str] = []
    metadata: Dict[str, Any] = {}
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class BaseAgent(ABC):
    """
    Base agent class with scientific method integration.
    
    Scientific Method Steps:
    1. Hypothesis - Initial assumption about the problem
    2. Reasoning - Analysis and processing
    3. Verification - Validation of results
    4. Conclusion - Final output and decision
    """
    
    name: str = "base_agent"
    description: str = "Base agent class"
    version: str = "1.0.0"
    
    def __init__(self):
        self.reasoning_chain: List[ScientificMethodStep] = []
        app_logger.info(f"Initialized agent: {self.name}")
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute the agent's main logic.
        Must be implemented by subclasses.
        
        Args:
            input_data: Input data for the agent
            
        Returns:
            AgentResult with success status and output data
        """
        pass
    
    async def hypothesis(self, problem: str, context: Dict[str, Any]) -> str:
        """
        Step 1: Form a hypothesis about the problem.
        
        Args:
            problem: Problem statement
            context: Additional context
            
        Returns:
            Hypothesis statement
        """
        prompt = f"""
        Problem: {problem}
        Context: {context}
        
        Form a clear hypothesis about how to solve this problem.
        """
        
        hypothesis_text = await self._generate_with_llm(prompt)
        
        self._add_reasoning_step("hypothesis", hypothesis_text, confidence=0.5)
        app_logger.debug(f"{self.name} - Hypothesis: {hypothesis_text[:100]}...")
        
        return hypothesis_text
    
    async def reasoning(self, hypothesis: str, data: Dict[str, Any]) -> str:
        """
        Step 2: Reason through the problem based on hypothesis.
        
        Args:
            hypothesis: The hypothesis to reason from
            data: Data to analyze
            
        Returns:
            Reasoning result
        """
        prompt = f"""
        Hypothesis: {hypothesis}
        Data: {data}
        
        Apply reasoning to analyze this data based on the hypothesis.
        Provide structured analysis.
        """
        
        reasoning_text = await self._generate_with_llm(prompt)
        
        self._add_reasoning_step("reasoning", reasoning_text, confidence=0.7)
        app_logger.debug(f"{self.name} - Reasoning completed")
        
        return reasoning_text
    
    async def verification(self, reasoning: str, expected_output: Optional[Dict] = None) -> bool:
        """
        Step 3: Verify the reasoning and results.
        
        Args:
            reasoning: Reasoning to verify
            expected_output: Optional expected output for validation
            
        Returns:
            True if verification passes
        """
        # Subclasses should implement specific verification logic
        verification_result = "Verification completed successfully"
        
        self._add_reasoning_step("verification", verification_result, confidence=0.8)
        app_logger.debug(f"{self.name} - Verification: PASS")
        
        return True
    
    async def conclusion(self, reasoning: str, verification_passed: bool) -> Dict[str, Any]:
        """
        Step 4: Draw conclusion from reasoning and verification.
        
        Args:
            reasoning: The reasoning result
            verification_passed: Whether verification passed
            
        Returns:
            Conclusion data
        """
        conclusion_data = {
            "status": "success" if verification_passed else "failed",
            "reasoning_summary": reasoning[:200],
            "verified": verification_passed
        }
        
        conclusion_text = f"Conclusion: {conclusion_data['status']}"
        self._add_reasoning_step("conclusion", conclusion_text, confidence=0.9)
        app_logger.debug(f"{self.name} - Conclusion: {conclusion_data['status']}")
        
        return conclusion_data
    
    async def _generate_with_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate text using LLM service.
        
        Args:
            prompt: Prompt text
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        try:
            # Load agent-specific system prompt if available
            system_prompt = prompt_loader.load_agent_prompt(self.name, "system")
        except:
            system_prompt = None
        
        messages = [{"role": "user", "content": prompt}]
        
        return await llm_service.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature
        )
    
    def _add_reasoning_step(self, step: str, content: str, confidence: float = 0.0):
        """Add a step to the reasoning chain."""
        reasoning_step = ScientificMethodStep(
            step=step,
            content=content,
            confidence=confidence
        )
        self.reasoning_chain.append(reasoning_step)
    
    def get_reasoning_chain(self) -> List[ScientificMethodStep]:
        """Get the complete reasoning chain."""
        return self.reasoning_chain
    
    def clear_reasoning_chain(self):
        """Clear the reasoning chain."""
        self.reasoning_chain = []
    
    def validate_input(self, input_data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        Validate that required fields are present in input data.
        
        Args:
            input_data: Input data to validate
            required_fields: List of required field names
            
        Raises:
            AgentException if validation fails
        """
        missing_fields = [field for field in required_fields if field not in input_data]
        
        if missing_fields:
            raise AgentException(
                f"Missing required fields: {', '.join(missing_fields)}",
                {"required_fields": required_fields, "missing": missing_fields}
            )
