"""
OrchestratorAgent - Central coordination system for construction document analysis
Routes files to appropriate specialist agents based on file type and content
"""

import os
import logging
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


class OrchestratorAgent:
    """
    Central orchestrator that routes files to appropriate agents
    based on file type and project context
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or get_llm_service()
        self.prompt_loader = get_prompt_loader()
        
        # We'll import existing agents lazily to avoid circular imports
        self._concrete_agent = None
        self._material_agent = None
        self._volume_agent = None
        self._tzd_reader = None
        
        logger.info("OrchestratorAgent initialized")

    def detect_file_type(self, file_path: str) -> str:
        """
        Detect file type based on extension and content
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected file type category
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        # Smeta/Bill of quantities files
        if extension in ['.xlsx', '.xls', '.xml', '.xc4']:
            return 'smeta'
            
        # Technical assignment files
        elif extension in ['.pdf', '.docx', '.doc', '.txt']:
            # Additional logic could check content to distinguish
            # between technical assignments and general documents
            return 'technical_document'
            
        # Drawing files  
        elif extension in ['.dwg', '.dxf']:
            return 'drawing'
            
        # General document files
        else:
            return 'general_document'

    async def _get_concrete_agent(self):
        """Lazy import of ConcreteAgent"""
        if self._concrete_agent is None:
            try:
                # Import existing concrete agent
                import sys
                sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
                from agents.concrete_agent import analyze_concrete
                self._concrete_agent = analyze_concrete
            except Exception as e:
                logger.error(f"Failed to import ConcreteAgent: {e}")
                self._concrete_agent = self._fallback_concrete_analysis
        return self._concrete_agent

    async def _get_material_agent(self):
        """Lazy import of MaterialAgent"""
        if self._material_agent is None:
            try:
                from agents.materials_agent import analyze_materials
                self._material_agent = analyze_materials
            except Exception as e:
                logger.error(f"Failed to import MaterialAgent: {e}")
                self._material_agent = self._fallback_material_analysis
        return self._material_agent

    async def _get_volume_agent(self):
        """Lazy import of VolumeAgent"""
        if self._volume_agent is None:
            try:
                # Import existing volume agent functionality
                from agents.volume_agent.agent import VolumeAnalysisAgent
                self._volume_agent = VolumeAnalysisAgent()
            except Exception as e:
                logger.error(f"Failed to import VolumeAgent: {e}")
                self._volume_agent = self._fallback_volume_analysis
        return self._volume_agent

    async def _get_tzd_reader(self):
        """Lazy import of TZDReader"""
        if self._tzd_reader is None:
            try:
                from agents.tzd_reader.agent import tzd_reader
                self._tzd_reader = tzd_reader
            except Exception as e:
                logger.error(f"Failed to import TZDReader: {e}")
                self._tzd_reader = self._fallback_tzd_analysis
        return self._tzd_reader

    async def process_file(self, file_path: str) -> FileAnalysis:
        """
        Process a single file by routing to appropriate agent
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            FileAnalysis with results
        """
        try:
            file_type = self.detect_file_type(file_path)
            logger.info(f"Processing {file_path} as {file_type}")
            
            if file_type == 'smeta':
                volume_agent = await self._get_volume_agent()
                if callable(volume_agent):
                    result = await volume_agent.analyze_file(file_path) if hasattr(volume_agent, 'analyze_file') else volume_agent([file_path])
                else:
                    result = await volume_agent.analyze_file(file_path)
                    
                return FileAnalysis(
                    file_path=file_path,
                    file_type=Path(file_path).suffix.lower(),
                    detected_type=file_type,
                    agent_used="VolumeAgent",
                    result=result,
                    success=True
                )
                
            elif file_type == 'technical_document':
                tzd_reader = await self._get_tzd_reader()
                result = await tzd_reader([file_path]) if callable(tzd_reader) else tzd_reader([file_path])
                
                return FileAnalysis(
                    file_path=file_path,
                    file_type=Path(file_path).suffix.lower(),
                    detected_type=file_type,
                    agent_used="TZDReader",
                    result=result,
                    success=True
                )
                
            elif file_type == 'drawing':
                # For now, use volume agent for drawings
                volume_agent = await self._get_volume_agent()
                result = await volume_agent.analyze_file(file_path) if hasattr(volume_agent, 'analyze_file') else {"status": "drawing_analysis_placeholder"}
                
                return FileAnalysis(
                    file_path=file_path,
                    file_type=Path(file_path).suffix.lower(),
                    detected_type=file_type,
                    agent_used="DrawingVolumeAgent",
                    result=result,
                    success=True
                )
                
            else:  # general_document
                # Run both concrete and material analysis
                concrete_agent = await self._get_concrete_agent()
                material_agent = await self._get_material_agent()
                
                concrete_result = await concrete_agent([file_path]) if callable(concrete_agent) else concrete_agent([file_path])
                material_result = await material_agent([file_path]) if callable(material_agent) else material_agent([file_path])
                
                combined_result = {
                    "concrete_analysis": concrete_result,
                    "material_analysis": material_result
                }
                
                return FileAnalysis(
                    file_path=file_path,
                    file_type=Path(file_path).suffix.lower(),
                    detected_type=file_type,
                    agent_used="ConcreteAgent+MaterialAgent",
                    result=combined_result,
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
        Run full project analysis on multiple files
        
        Args:
            files: List of file paths to analyze
            
        Returns:
            Comprehensive project analysis results
        """
        logger.info(f"Starting project analysis for {len(files)} files")
        
        results = []
        file_types = {}
        
        # Process each file
        for file_path in files:
            analysis = await self.process_file(file_path)
            results.append(analysis)
            
            # Count file types
            detected_type = analysis.detected_type
            file_types[detected_type] = file_types.get(detected_type, 0) + 1

        # Aggregate results
        successful_analyses = [r for r in results if r.success]
        failed_analyses = [r for r in results if not r.success]
        
        # Extract key findings
        concrete_findings = []
        material_findings = []
        volume_findings = []
        technical_findings = []
        
        for analysis in successful_analyses:
            if "concrete_analysis" in analysis.result:
                concrete_findings.append(analysis.result["concrete_analysis"])
            if "material_analysis" in analysis.result:
                material_findings.append(analysis.result["material_analysis"])
            if analysis.agent_used == "VolumeAgent":
                volume_findings.append(analysis.result)
            if analysis.agent_used == "TZDReader":
                technical_findings.append(analysis.result)

        project_summary = {
            "total_files": len(files),
            "successful_analyses": len(successful_analyses),
            "failed_analyses": len(failed_analyses),
            "file_type_distribution": file_types,
            "agents_used": list(set([r.agent_used for r in successful_analyses])),
            "concrete_findings": concrete_findings,
            "material_findings": material_findings,
            "volume_findings": volume_findings,
            "technical_findings": technical_findings,
            "detailed_results": [
                {
                    "file": r.file_path,
                    "type": r.detected_type,
                    "agent": r.agent_used,
                    "success": r.success,
                    "result": r.result if r.success else None,
                    "error": r.error
                }
                for r in results
            ]
        }
        
        logger.info(f"Project analysis completed: {len(successful_analyses)}/{len(files)} files processed successfully")
        
        return project_summary

    # Fallback methods for when agents can't be imported
    async def _fallback_concrete_analysis(self, files: List[str]) -> Dict[str, Any]:
        """Fallback concrete analysis using LLM service directly"""
        try:
            system_prompt = self.prompt_loader.get_system_prompt("concrete")
            
            # Read first file for analysis
            if files:
                with open(files[0], 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:10000]  # Limit content
                    
                response = await self.llm.run_prompt(
                    provider="claude",
                    prompt=f"Analyze this construction document for concrete grades:\n\n{content}",
                    system_prompt=system_prompt
                )
                
                return {
                    "method": "fallback_llm",
                    "analysis": response.get("content", ""),
                    "success": response.get("success", False)
                }
        except Exception as e:
            logger.error(f"Fallback concrete analysis failed: {e}")
        
        return {"method": "fallback", "error": "Analysis unavailable"}

    async def _fallback_material_analysis(self, files: List[str]) -> Dict[str, Any]:
        """Fallback material analysis using LLM service directly"""
        try:
            system_prompt = self.prompt_loader.get_system_prompt("material") 
            
            if files:
                with open(files[0], 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:10000]
                    
                response = await self.llm.run_prompt(
                    provider="claude",
                    prompt=f"Analyze this construction document for materials:\n\n{content}",
                    system_prompt=system_prompt
                )
                
                return {
                    "method": "fallback_llm",
                    "analysis": response.get("content", ""),
                    "success": response.get("success", False)
                }
        except Exception as e:
            logger.error(f"Fallback material analysis failed: {e}")
            
        return {"method": "fallback", "error": "Analysis unavailable"}

    async def _fallback_volume_analysis(self, files: List[str]) -> Dict[str, Any]:
        """Fallback volume analysis"""
        return {"method": "fallback", "error": "Volume analysis unavailable"}

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
_orchestrator_agent = None


def get_orchestrator_agent() -> OrchestratorAgent:
    """Get global orchestrator agent instance"""
    global _orchestrator_agent
    if _orchestrator_agent is None:
        _orchestrator_agent = OrchestratorAgent()
    return _orchestrator_agent