"""
Prompt loader for managing system and agent prompts.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from backend.app.core.config import settings
from backend.app.core.logging_config import app_logger
from backend.app.core.exceptions import ConfigurationException


class PromptLoader:
    """Loads and manages prompt templates."""
    
    def __init__(self):
        self.prompts_cache: Dict[str, str] = {}
        self.base_path = Path(__file__).parent.parent / "prompts"
    
    def load_prompt(self, prompt_path: str, use_cache: bool = True) -> str:
        """
        Load a prompt from file.
        
        Args:
            prompt_path: Relative path to prompt file
            use_cache: Whether to use cached version
            
        Returns:
            Prompt text content
        """
        if use_cache and prompt_path in self.prompts_cache:
            return self.prompts_cache[prompt_path]
        
        full_path = self.base_path / prompt_path
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if use_cache:
                self.prompts_cache[prompt_path] = content
            
            app_logger.debug(f"Loaded prompt from {prompt_path}")
            return content
            
        except FileNotFoundError:
            app_logger.error(f"Prompt file not found: {prompt_path}")
            raise ConfigurationException(
                f"Prompt file not found: {prompt_path}",
                {"path": str(full_path)}
            )
        except Exception as e:
            app_logger.error(f"Error loading prompt {prompt_path}: {e}")
            raise ConfigurationException(
                f"Failed to load prompt: {e}",
                {"path": str(full_path)}
            )
    
    def load_agent_prompt(self, agent_name: str, prompt_type: str = "system") -> str:
        """
        Load a prompt for a specific agent.
        
        Args:
            agent_name: Name of the agent
            prompt_type: Type of prompt (system, user, etc.)
            
        Returns:
            Prompt content
        """
        # Try agent-specific prompt first
        agent_prompt_path = f"../agents/{agent_name}/prompts/{prompt_type}.txt"
        full_agent_path = self.base_path.parent / "agents" / agent_name / "prompts" / f"{prompt_type}.txt"
        
        if full_agent_path.exists():
            try:
                with open(full_agent_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                app_logger.warning(f"Failed to load agent prompt: {e}")
        
        # Fall back to default prompt
        return self.load_prompt(f"{prompt_type}_prompt.txt")
    
    def clear_cache(self):
        """Clear the prompt cache."""
        self.prompts_cache.clear()
        app_logger.info("Prompt cache cleared")


# Global prompt loader instance
prompt_loader = PromptLoader()
