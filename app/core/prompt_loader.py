"""
Prompt loading utility for Construction Analysis API
Handles loading and caching of agent prompts from JSON files
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptLoader:
    """Utility class for loading and caching agent prompts"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        # Default to app/prompts directory
        if prompts_dir is None:
            current_dir = Path(__file__).parent.parent
            self.prompts_dir = current_dir / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
            
        self._cache = {}
        logger.info(f"PromptLoader initialized with directory: {self.prompts_dir}")

    def load_prompt(self, agent_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Load prompt for specified agent
        
        Args:
            agent_name: Name of the agent (e.g., 'concrete', 'material', 'tzd')
            use_cache: Whether to use cached prompts
            
        Returns:
            Dict containing prompt data
        """
        if use_cache and agent_name in self._cache:
            return self._cache[agent_name]
            
        prompt_file = self.prompts_dir / f"{agent_name}_prompt.json"
        
        try:
            if not prompt_file.exists():
                logger.warning(f"Prompt file not found: {prompt_file}")
                return self._get_default_prompt(agent_name)
                
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)
                
            # Cache the loaded prompt
            if use_cache:
                self._cache[agent_name] = prompt_data
                
            logger.debug(f"Loaded prompt for {agent_name}")
            return prompt_data
            
        except Exception as e:
            logger.error(f"Error loading prompt for {agent_name}: {e}")
            return self._get_default_prompt(agent_name)

    def get_prompt_content(self, agent_name: str) -> str:
        """Get just the content string from prompt"""
        prompt_data = self.load_prompt(agent_name)
        return prompt_data.get("content", "")

    def get_system_prompt(self, agent_name: str) -> str:
        """Get system prompt content for agent"""
        prompt_data = self.load_prompt(agent_name)
        if prompt_data.get("role") == "system":
            return prompt_data.get("content", "")
        return ""

    def get_prompt_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration parameters for agent prompt"""
        prompt_data = self.load_prompt(agent_name)
        return {
            "provider": prompt_data.get("provider", "claude"),
            "model": prompt_data.get("model", "claude-3-sonnet-20240229"),
            "parameters": prompt_data.get("parameters", {})
        }

    def _get_default_prompt(self, agent_name: str) -> Dict[str, Any]:
        """Get default prompt if file not found"""
        defaults = {
            "concrete": {
                "role": "system",
                "content": "You are a concrete analysis specialist. Extract concrete grades and specifications from construction documents.",
                "provider": "claude",
                "model": "claude-3-sonnet-20240229"
            },
            "material": {
                "role": "system", 
                "content": "You are a materials analysis specialist. Identify construction materials (except concrete) from project documents.",
                "provider": "claude",
                "model": "claude-3-sonnet-20240229"
            },
            "volume": {
                "role": "system",
                "content": "You are a volume analysis specialist. Extract quantities and volumes from construction documents and smeta.",
                "provider": "claude", 
                "model": "claude-3-sonnet-20240229"
            },
            "tzd": {
                "role": "system",
                "content": "You are a technical assignment reader. Extract structured information from technical specifications.",
                "provider": "gpt",
                "model": "gpt-4o-mini"
            },
            "orchestrator": {
                "role": "system",
                "content": "You are an orchestrator agent. Coordinate file analysis and route to appropriate specialist agents.",
                "provider": "claude",
                "model": "claude-3-sonnet-20240229"
            }
        }
        
        return defaults.get(agent_name, {
            "role": "system",
            "content": f"You are {agent_name} agent for construction document analysis.",
            "provider": "claude",
            "model": "claude-3-sonnet-20240229"
        })

    def list_available_prompts(self) -> list:
        """List all available prompt files"""
        if not self.prompts_dir.exists():
            return []
            
        prompt_files = []
        for file in self.prompts_dir.glob("*_prompt.json"):
            agent_name = file.stem.replace("_prompt", "")
            prompt_files.append(agent_name)
            
        return sorted(prompt_files)

    def reload_cache(self):
        """Clear cache and reload all prompts"""
        self._cache.clear()
        logger.info("Prompt cache cleared")

    def validate_prompts(self) -> Dict[str, bool]:
        """Validate all prompt files can be loaded"""
        results = {}
        
        for agent_name in self.list_available_prompts():
            try:
                prompt_data = self.load_prompt(agent_name, use_cache=False)
                # Check required fields
                has_content = bool(prompt_data.get("content"))
                has_role = bool(prompt_data.get("role"))
                results[agent_name] = has_content and has_role
            except Exception as e:
                logger.error(f"Validation failed for {agent_name}: {e}")
                results[agent_name] = False
                
        return results


# Global instance
_prompt_loader = None


def get_prompt_loader() -> PromptLoader:
    """Get global prompt loader instance"""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader