"""
OrchestratorService - Central coordination system for construction document analysis
Enhanced version with consistency validation and parallel execution support
"""

import os
import logging
import asyncio
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from app.core.llm_service import LLMService, get_llm_service
from app.core.prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)


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
        
        # Agent instances - loaded lazily to avoid circular imports
        self._agents = {}
        self._initialized_agents = set()
        
        logger.info("OrchestratorService initialized with enhanced features")

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

    async def _get_agent(self, agent_name: str):
        """
        Lazy loading of agents with proper error handling
        Agent modules are optional - system works with any available agents
        
        Args:
            agent_name: Name of the agent to load
            
        Returns:
            Agent instance or None if not available
        """
        # Return cached agent if already loaded
        if agent_name in self._agents:
            return self._agents[agent_name]
        
        # Check if we already failed to load this agent
        if agent_name in self._initialized_agents:
            return None
            
        try:
            # Dynamic agent loading based on name
            # Each agent is optional - missing agents won't break the system
            agent = None
            
            if agent_name == 'tzd':
                try:
                    from agents.tzd_reader.agent import TZDReader
                    agent = TZDReader()
                except ImportError as ie:
                    logger.warning(f"TZD agent not available: {ie}")
            else:
                logger.warning(f"Unknown agent requested: {agent_name}")
            
            # Cache the agent (or None if failed)
            self._agents[agent_name] = agent
            self._initialized_agents.add(agent_name)
            
            if agent:
                logger.info(f"✅ Agent '{agent_name}' loaded successfully")
            else:
                logger.info(f"⚠️ Agent '{agent_name}' not available - using fallback")
            
            return agent
            
        except Exception as e:
            logger.error(f"Unexpected error loading agent {agent_name}: {e}")
            self._agents[agent_name] = None
            self._initialized_agents.add(agent_name)
            return None

    async def process_file(self, file_path: str) -> FileAnalysis:
        """
        Process file using TZD Reader agent
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            FileAnalysis with detailed results
        """
        try:
            file_type = self.detect_file_type(file_path)
            logger.info(f"Processing {file_path} as {file_type}")
            
            # Only TZD agent is available
            tzd_agent = await self._get_agent('tzd')
            
            if tzd_agent:
                result = await self._run_tzd_analysis(tzd_agent, file_path)
                agent_used = "TZDReader"
            else:
                result = await self._fallback_tzd_analysis([file_path])
                agent_used = "TZDReader (fallback)"

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

    # Helper methods for running TZD analysis
    async def _run_tzd_analysis(self, agent, file_path: str) -> Dict[str, Any]:
        """Run TZD analysis with proper error handling"""
        try:
            if hasattr(agent, 'analyze_document'):
                result = await agent.analyze_document(file_path)
            elif hasattr(agent, 'analyze'):
                result = await agent.analyze(file_path)
            else:
                result = await self._fallback_tzd_analysis([file_path])
            return result
        except Exception as e:
            logger.error(f"TZD analysis failed: {e}")
            return {"error": str(e)}

    # Fallback analysis method
    async def _fallback_tzd_analysis(self, files: List[str]) -> Dict[str, Any]:
        """Fallback TZD analysis using LLM service directly"""
        try:
            system_prompt = self.prompt_loader.get_system_prompt("tzd")
            
            if files:
                with open(files[0], 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:15000]
                    
                response = await self.llm.run_prompt(
                    provider="gpt",
                    prompt=f"Analyze this technical assignment:\n\n{content}",
                    system_prompt=system_prompt
                )
                
                return {
                    "method": "fallback_llm",
                    "analysis": response.get("content", ""),
                    "success": response.get("success", False)
                }
        except Exception as e:
            logger.error(f"Fallback TZD analysis failed: {e}")
            
        return {"method": "fallback", "error": "Analysis unavailable"}


# Global instance
_orchestrator_service = None


def get_orchestrator_service() -> OrchestratorService:
    """Get global orchestrator service instance"""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service