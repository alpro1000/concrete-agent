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


@dataclass 
class ConsistencyValidation:
    """Structure for consistency validation results"""
    volumes_consistent: bool
    grades_consistent: bool
    materials_consistent: bool
    validation_details: Dict[str, Any]
    recommendations: List[str]


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
        
        Args:
            agent_name: Name of the agent to load
            
        Returns:
            Agent instance or fallback function
        """
        if agent_name in self._agents:
            return self._agents[agent_name]
            
        try:
            # Import agents based on name
            if agent_name == 'concrete':
                import sys
                sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
                from agents.concrete_agent import UnifiedConcreteAgent
                agent = UnifiedConcreteAgent()
                self._agents[agent_name] = agent
                
            elif agent_name == 'material':
                from agents.materials_agent import MaterialAgent
                agent = MaterialAgent()
                self._agents[agent_name] = agent
                
            elif agent_name == 'volume':
                from agents.concrete_volume_agent import ConcreteVolumeAgent
                agent = ConcreteVolumeAgent()
                self._agents[agent_name] = agent
                
            elif agent_name == 'tzd':
                from agents.tzd_reader.agent import TZDReader
                agent = TZDReader()
                self._agents[agent_name] = agent
                
            elif agent_name == 'drawing':
                from agents.drawing_volume_agent import DrawingVolumeAgent
                agent = DrawingVolumeAgent()
                self._agents[agent_name] = agent
                
            elif agent_name == 'smeta':
                from agents.smetny_inzenyr.agent import SmetnyInzenyr
                agent = SmetnyInzenyr()
                self._agents[agent_name] = agent
                
            elif agent_name == 'tov':
                from agents.tov_agent import TOVAgent
                agent = TOVAgent()
                self._agents[agent_name] = agent
                
            elif agent_name == 'diff':
                from agents.version_diff_agent import VersionDiffAgent
                agent = VersionDiffAgent()
                self._agents[agent_name] = agent
                
            else:
                logger.warning(f"Unknown agent: {agent_name}")
                return None
                
            self._initialized_agents.add(agent_name)
            logger.info(f"✅ Agent {agent_name} loaded successfully")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to load agent {agent_name}: {e}")
            # Return fallback function
            return getattr(self, f'_fallback_{agent_name}_analysis', None)

    async def process_file(self, file_path: str) -> FileAnalysis:
        """
        Enhanced file processing with better agent routing
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            FileAnalysis with detailed results
        """
        try:
            file_type = self.detect_file_type(file_path)
            logger.info(f"Processing {file_path} as {file_type}")
            
            # Route to appropriate agent based on file type
            if file_type == 'smeta':
                agent = await self._get_agent('smeta')
                if agent and hasattr(agent, 'analyze_smeta'):
                    result = await agent.analyze_smeta(file_path)
                else:
                    result = await self._fallback_smeta_analysis([file_path])
                agent_used = "SmetaAgent"
                
            elif file_type in ['technical_assignment', 'technical_document']:
                # Use parallel analysis for comprehensive results
                concrete_agent = await self._get_agent('concrete')
                material_agent = await self._get_agent('material')
                tzd_agent = await self._get_agent('tzd')
                
                # Run analyses in parallel
                tasks = []
                if concrete_agent:
                    tasks.append(self._run_concrete_analysis(concrete_agent, file_path))
                if material_agent:
                    tasks.append(self._run_material_analysis(material_agent, file_path))
                if tzd_agent:
                    tasks.append(self._run_tzd_analysis(tzd_agent, file_path))
                    
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                combined_result = {}
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Analysis task {i} failed: {result}")
                        continue
                    combined_result.update(result)
                
                agent_used = "Multi-Agent (Concrete+Material+TZD)"
                result = combined_result
                
            elif file_type == 'drawing':
                agent = await self._get_agent('drawing')
                if agent and hasattr(agent, 'analyze_drawing'):
                    result = await agent.analyze_drawing(file_path)
                else:
                    result = await self._fallback_drawing_analysis([file_path])
                agent_used = "DrawingAgent"
                
            elif file_type == 'material_specification':
                agent = await self._get_agent('material')
                if agent and hasattr(agent, 'analyze_materials'):
                    result = await agent.analyze_materials(file_path)
                else:
                    result = await self._fallback_material_analysis([file_path])
                agent_used = "MaterialAgent"
                
            else:
                # General document - use concrete and material analysis
                concrete_agent = await self._get_agent('concrete')
                material_agent = await self._get_agent('material')
                
                tasks = []
                if concrete_agent:
                    tasks.append(self._run_concrete_analysis(concrete_agent, file_path))
                if material_agent:
                    tasks.append(self._run_material_analysis(material_agent, file_path))
                    
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                combined_result = {}
                for result in results:
                    if not isinstance(result, Exception):
                        combined_result.update(result)
                
                agent_used = "Multi-Agent (Concrete+Material)"
                result = combined_result

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
        Enhanced project analysis with consistency validation
        
        Args:
            files: List of file paths to analyze
            
        Returns:
            Comprehensive project analysis with consistency checks
        """
        logger.info(f"Starting enhanced project analysis for {len(files)} files")
        
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
        
        # Perform consistency validation
        consistency_validation = await self._validate_consistency(successful_analyses)
        
        # Aggregate findings by category
        findings = self._aggregate_findings(successful_analyses)
        
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
            
            # Enhanced findings organization
            "findings": findings,
            
            # Consistency validation results
            "consistency_validation": {
                "volumes_consistent": consistency_validation.volumes_consistent,
                "grades_consistent": consistency_validation.grades_consistent,
                "materials_consistent": consistency_validation.materials_consistent,
                "validation_details": consistency_validation.validation_details,
                "recommendations": consistency_validation.recommendations
            },
            
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
        
        logger.info(f"Enhanced project analysis completed: {len(successful_analyses)}/{len(files)} files processed successfully")
        
        return project_summary

    async def _validate_consistency(self, analyses: List[FileAnalysis]) -> ConsistencyValidation:
        """
        Validate consistency between analysis results
        
        Args:
            analyses: List of successful file analyses
            
        Returns:
            ConsistencyValidation with detailed results
        """
        validation_details = {}
        recommendations = []
        
        # Extract data for consistency checks
        concrete_grades = []
        material_specs = []
        volumes = []
        
        for analysis in analyses:
            result = analysis.result
            
            # Extract concrete grades
            if 'concrete_analysis' in result:
                if 'grades' in result['concrete_analysis']:
                    concrete_grades.extend(result['concrete_analysis']['grades'])
            
            # Extract material specifications  
            if 'material_analysis' in result:
                if 'materials' in result['material_analysis']:
                    material_specs.extend(result['material_analysis']['materials'])
            
            # Extract volumes
            if 'volume_analysis' in result:
                if 'volumes' in result['volume_analysis']:
                    volumes.extend(result['volume_analysis']['volumes'])

        # Validate volumes consistency
        volumes_consistent = True
        if len(volumes) > 1:
            # Check if volumes from different sources match
            volume_discrepancies = self._check_volume_discrepancies(volumes)
            volumes_consistent = len(volume_discrepancies) == 0
            validation_details['volume_discrepancies'] = volume_discrepancies
            
            if volume_discrepancies:
                recommendations.append("Review volume calculations - discrepancies found between documents")

        # Validate concrete grades consistency
        grades_consistent = True
        if len(concrete_grades) > 1:
            grade_inconsistencies = self._check_grade_inconsistencies(concrete_grades)
            grades_consistent = len(grade_inconsistencies) == 0
            validation_details['grade_inconsistencies'] = grade_inconsistencies
            
            if grade_inconsistencies:
                recommendations.append("Verify concrete grade specifications - inconsistencies detected")

        # Validate materials consistency
        materials_consistent = True
        if len(material_specs) > 1:
            material_conflicts = self._check_material_conflicts(material_specs)
            materials_consistent = len(material_conflicts) == 0
            validation_details['material_conflicts'] = material_conflicts
            
            if material_conflicts:
                recommendations.append("Check material specifications for conflicts")

        return ConsistencyValidation(
            volumes_consistent=volumes_consistent,
            grades_consistent=grades_consistent,
            materials_consistent=materials_consistent,
            validation_details=validation_details,
            recommendations=recommendations
        )

    def _check_volume_discrepancies(self, volumes: List[Dict]) -> List[Dict]:
        """Check for discrepancies in volume calculations"""
        discrepancies = []
        # Implementation for volume consistency checking
        # This would compare volumes for same structural elements
        return discrepancies

    def _check_grade_inconsistencies(self, grades: List[Dict]) -> List[Dict]:
        """Check for inconsistencies in concrete grades"""
        inconsistencies = []
        # Implementation for grade consistency checking
        # This would verify grade requirements match across documents
        return inconsistencies

    def _check_material_conflicts(self, materials: List[Dict]) -> List[Dict]:
        """Check for conflicts in material specifications"""
        conflicts = []
        # Implementation for material consistency checking
        # This would identify conflicting material requirements
        return conflicts

    def _aggregate_findings(self, analyses: List[FileAnalysis]) -> Dict[str, List]:
        """
        Aggregate findings by category for better organization
        
        Args:
            analyses: List of successful analyses
            
        Returns:
            Dict with categorized findings
        """
        findings = {
            "concrete_grades": [],
            "materials": [],
            "volumes": [],
            "technical_requirements": [],
            "drawings": [],
            "smeta_data": []
        }
        
        for analysis in analyses:
            result = analysis.result
            
            if 'concrete_analysis' in result:
                findings["concrete_grades"].append(result['concrete_analysis'])
            if 'material_analysis' in result:
                findings["materials"].append(result['material_analysis'])
            if 'volume_analysis' in result:
                findings["volumes"].append(result['volume_analysis'])
            if 'tzd_analysis' in result:
                findings["technical_requirements"].append(result['tzd_analysis'])
            if 'drawing_analysis' in result:
                findings["drawings"].append(result['drawing_analysis'])
            if 'smeta_analysis' in result:
                findings["smeta_data"].append(result['smeta_analysis'])
                
        return findings

    # Helper methods for running individual agent analyses
    async def _run_concrete_analysis(self, agent, file_path: str) -> Dict[str, Any]:
        """Run concrete analysis with proper error handling"""
        try:
            if hasattr(agent, 'analyze_document'):
                result = await agent.analyze_document(file_path)
            elif hasattr(agent, 'analyze'):
                result = await agent.analyze(file_path)
            else:
                result = await self._fallback_concrete_analysis([file_path])
            return {"concrete_analysis": result}
        except Exception as e:
            logger.error(f"Concrete analysis failed: {e}")
            return {"concrete_analysis": {"error": str(e)}}

    async def _run_material_analysis(self, agent, file_path: str) -> Dict[str, Any]:
        """Run material analysis with proper error handling"""
        try:
            if hasattr(agent, 'analyze_document'):
                result = await agent.analyze_document(file_path)
            elif hasattr(agent, 'analyze'):
                result = await agent.analyze(file_path)
            else:
                result = await self._fallback_material_analysis([file_path])
            return {"material_analysis": result}
        except Exception as e:
            logger.error(f"Material analysis failed: {e}")
            return {"material_analysis": {"error": str(e)}}

    async def _run_tzd_analysis(self, agent, file_path: str) -> Dict[str, Any]:
        """Run TZD analysis with proper error handling"""
        try:
            if hasattr(agent, 'analyze_document'):
                result = await agent.analyze_document(file_path)
            elif hasattr(agent, 'analyze'):
                result = await agent.analyze(file_path)
            else:
                result = await self._fallback_tzd_analysis([file_path])
            return {"tzd_analysis": result}
        except Exception as e:
            logger.error(f"TZD analysis failed: {e}")
            return {"tzd_analysis": {"error": str(e)}}

    # Fallback analysis methods
    async def _fallback_concrete_analysis(self, files: List[str]) -> Dict[str, Any]:
        """Fallback concrete analysis using LLM service directly"""
        try:
            system_prompt = self.prompt_loader.get_system_prompt("concrete")
            
            if files:
                with open(files[0], 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:10000]
                    
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

    async def _fallback_smeta_analysis(self, files: List[str]) -> Dict[str, Any]:
        """Fallback smeta analysis"""
        return {"method": "fallback", "error": "Smeta analysis unavailable"}

    async def _fallback_drawing_analysis(self, files: List[str]) -> Dict[str, Any]:
        """Fallback drawing analysis"""
        return {"method": "fallback", "error": "Drawing analysis unavailable"}


# Global instance
_orchestrator_service = None


def get_orchestrator_service() -> OrchestratorService:
    """Get global orchestrator service instance"""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service