"""
OrchestratorService - Central coordination system for construction document analysis
Enhanced version with consistency validation and parallel execution support
"""

import os
import sys
import logging
import asyncio
import mimetypes
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from app.core.llm_service import LLMService, get_llm_service
from app.core.prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)


def discover_agents(agents_dir: str = "app/agents") -> Dict[str, Any]:
    """
    Dynamically discover and load agents from the agents directory.
    
    Each agent must:
    - Be in a subdirectory of agents_dir
    - Have an agent.py file
    - Contain a class that has 'name' and 'supported_types' attributes
    - Implement an 'analyze' method
    
    Args:
        agents_dir: Path to agents directory (default: "app/agents")
        
    Returns:
        Dictionary mapping agent names to agent instances
    """
    discovered_agents = {}
    agents_path = Path(agents_dir)
    
    if not agents_path.exists():
        logger.warning(f"Agents directory not found: {agents_dir}")
        return discovered_agents
    
    # Add parent directory to Python path if needed
    parent_dir = str(agents_path.parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    logger.info(f"Discovering agents in: {agents_dir}")
    
    # Iterate through subdirectories in agents directory
    for agent_folder in agents_path.iterdir():
        if not agent_folder.is_dir():
            continue
            
        if agent_folder.name.startswith('_') or agent_folder.name.startswith('.'):
            continue
        
        agent_file = agent_folder / "agent.py"
        if not agent_file.exists():
            logger.debug(f"No agent.py found in {agent_folder.name}, skipping")
            continue
        
        try:
            # Import the agent module
            module_path = f"{agents_dir.replace('/', '.')}.{agent_folder.name}.agent"
            logger.debug(f"Attempting to import: {module_path}")
            
            agent_module = importlib.import_module(module_path)
            
            # Look for agent class in the module
            agent_class = None
            for attr_name in dir(agent_module):
                attr = getattr(agent_module, attr_name)
                
                # Check if it's a class with required attributes
                if (isinstance(attr, type) and 
                    hasattr(attr, 'name') and 
                    hasattr(attr, 'supported_types') and
                    hasattr(attr, 'analyze')):
                    
                    # Skip base classes
                    if attr_name in ['BaseAgent', 'ABC']:
                        continue
                    
                    agent_class = attr
                    break
            
            if agent_class:
                # Instantiate the agent
                agent_instance = agent_class()
                agent_name = getattr(agent_instance, 'name', agent_folder.name)
                
                discovered_agents[agent_name] = agent_instance
                
                supported = getattr(agent_instance, 'supported_types', [])
                logger.info(f"✅ Discovered agent: {agent_name} (supports: {supported})")
            else:
                logger.warning(f"No valid agent class found in {agent_folder.name}/agent.py")
                
        except Exception as e:
            logger.error(f"Failed to load agent from {agent_folder.name}: {e}")
            continue
    
    logger.info(f"Agent discovery complete: {len(discovered_agents)} agents loaded")
    return discovered_agents


@dataclass
class FileAnalysis:
    """Structure for file analysis results"""
    file_path: str
    file_type: str
    detected_type: str
    agent_used: str
    result: Dict[str, Any]
    success: bool
    error: Optional[str] = None


class OrchestratorService:
    """
    Enhanced orchestrator service that coordinates all construction analysis agents
    with consistency validation and parallel execution support
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or get_llm_service()
        self.prompt_loader = get_prompt_loader()
        
        # Agent instances - discovered dynamically
        self._agents = {}
        self._initialized = False
        
        logger.info("OrchestratorService initialized with enhanced features")
    
    def _ensure_agents_loaded(self):
        """Ensure agents are discovered and loaded (lazy loading)"""
        if not self._initialized:
            logger.info("Performing agent discovery...")
            self._agents = discover_agents("app/agents")
            self._initialized = True
            
            if self._agents:
                logger.info(f"Loaded {len(self._agents)} agent(s): {list(self._agents.keys())}")
            else:
                logger.warning("No agents discovered")
    
    def get_agent_for_type(self, file_type: str):
        """
        Get the appropriate agent for a given file type.
        
        Args:
            file_type: Type of file or document (e.g., "technical_assignment", "pdf")
            
        Returns:
            Agent instance or None if no agent supports this type
        """
        self._ensure_agents_loaded()
        
        # Find first agent that supports this type
        for agent_name, agent in self._agents.items():
            if hasattr(agent, 'supports_type') and agent.supports_type(file_type):
                logger.info(f"Selected agent '{agent_name}' for type '{file_type}'")
                return agent
            elif file_type.lower() in [t.lower() for t in getattr(agent, 'supported_types', [])]:
                logger.info(f"Selected agent '{agent_name}' for type '{file_type}'")
                return agent
        
        logger.warning(f"No agent found for type '{file_type}'")
        return None

    def detect_file_type(self, file_path: str) -> str:
        """
        Enhanced file type detection with content analysis
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected file type category
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        filename = file_path.name.lower()
        
        # Enhanced detection logic
        if extension in ['.xlsx', '.xls'] or 'smeta' in filename or 'výkaz' in filename:
            return 'smeta'
        elif extension in ['.xml', '.xc4'] or 'výměr' in filename:
            return 'smeta'
        elif extension in ['.pdf', '.docx', '.doc', '.txt']:
            # Content-based detection for technical documents
            if any(keyword in filename for keyword in ['tzd', 'zadání', 'assignment', 'technick']):
                return 'technical_assignment'
            elif any(keyword in filename for keyword in ['specifikace', 'specification', 'material']):
                return 'material_specification'
            else:
                return 'technical_document'
        elif extension in ['.dwg', '.dxf']:
            return 'drawing'
        else:
            return 'general_document'

    async def process_file(self, file_path: str) -> FileAnalysis:
        """
        Process file using dynamically discovered agents
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            FileAnalysis with detailed results
        """
        try:
            file_type = self.detect_file_type(file_path)
            logger.info(f"Processing {file_path} as {file_type}")
            
            # Get appropriate agent for this file type
            agent = self.get_agent_for_type(file_type)
            
            if agent:
                # Use agent's analyze method
                result = await agent.analyze(file_path)
                agent_used = getattr(agent, 'name', agent.__class__.__name__)
            else:
                # Fallback if no agent available
                result = await self._fallback_analysis([file_path])
                agent_used = "fallback"

            return FileAnalysis(
                file_path=file_path,
                file_type=Path(file_path).suffix.lower(),
                detected_type=file_type,
                agent_used=agent_used,
                result=result,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return FileAnalysis(
                file_path=file_path,
                file_type=Path(file_path).suffix.lower(),
                detected_type="unknown",
                agent_used="none",
                result={},
                success=False,
                error=str(e)
            )

    async def run_project(self, files: List[str]) -> Dict[str, Any]:
        """
        Process multiple files using TZD Reader
        
        Args:
            files: List of file paths to analyze
            
        Returns:
            Comprehensive project analysis
        """
        logger.info(f"Starting project analysis for {len(files)} files")
        
        # Process files in parallel for better performance
        tasks = [self.process_file(file_path) for file_path in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [r for r in results if not isinstance(r, Exception)]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        if exceptions:
            for exc in exceptions:
                logger.error(f"File processing exception: {exc}")
        
        successful_analyses = [r for r in valid_results if r.success]
        failed_analyses = [r for r in valid_results if not r.success]
        
        # Calculate file type distribution
        file_types = {}
        for analysis in valid_results:
            detected_type = analysis.detected_type
            file_types[detected_type] = file_types.get(detected_type, 0) + 1

        project_summary = {
            "total_files": len(files),
            "successful_analyses": len(successful_analyses),
            "failed_analyses": len(failed_analyses),
            "file_type_distribution": file_types,
            "agents_used": list(set([r.agent_used for r in successful_analyses])),
            
            # Detailed per-file results
            "detailed_results": [
                {
                    "file": r.file_path,
                    "type": r.detected_type,
                    "agent": r.agent_used,
                    "success": r.success,
                    "result": r.result if r.success else None,
                    "error": r.error
                }
                for r in valid_results
            ]
        }
        
        logger.info(f"Project analysis completed: {len(successful_analyses)}/{len(files)} files processed successfully")
        
        return project_summary

    # Fallback analysis method
    async def _fallback_analysis(self, files: List[str]) -> Dict[str, Any]:
        """Fallback analysis using LLM service directly when no agent is available"""
        try:
            # Try to get a system prompt (prefer tzd for now, but could be made more generic)
            try:
                system_prompt = self.prompt_loader.get_system_prompt("tzd")
            except:
                system_prompt = "Analyze this document and extract key information."
            
            if files:
                with open(files[0], 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:15000]
                    
                response = await self.llm.run_prompt(
                    provider="gpt",
                    prompt=f"Analyze this document:\n\n{content}",
                    system_prompt=system_prompt
                )
                
                return {
                    "method": "fallback_llm",
                    "analysis": response.get("content", ""),
                    "success": response.get("success", False)
                }
        except Exception as e:
            logger.error(f"Fallback analysis failed: {e}")
            
        return {"method": "fallback", "error": "Analysis unavailable"}


# Global instance
_orchestrator_service = None


def get_orchestrator_service() -> OrchestratorService:
    """Get global orchestrator service instance"""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service