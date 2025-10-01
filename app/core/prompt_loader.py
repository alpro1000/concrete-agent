"""
Prompt Loader - Enhanced version with error handling for JSON reading and support for the latest LLM models.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Global singleton instance
_prompt_loader_instance = None

def get_prompt_loader() -> "PromptLoader":
    """
    Get or create the global PromptLoader singleton instance.
    
    Returns:
        PromptLoader: The singleton instance
    """
    global _prompt_loader_instance
    if _prompt_loader_instance is None:
        _prompt_loader_instance = PromptLoader()
    return _prompt_loader_instance

class PromptLoader:
    """
    A utility class for loading and managing prompts for various LLM models.
    """

    def __init__(self, prompt_dir: Optional[str] = None):
        """
        Initialize the PromptLoader with the directory containing JSON prompt files.
        
        Args:
            prompt_dir (str): Directory containing the JSON prompt files.
        """
        if prompt_dir is None:
            # Calculate correct path relative to this file
            self.prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompt_dir)
        
        # Create directory if it doesn't exist
        if not self.prompts_dir.exists():
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created prompts directory: {self.prompts_dir}")
        else:
            logger.info(f"Prompts directory found: {self.prompts_dir}")
        
        self.prompts = {}
        self.supported_models = {
            "gpt-4.1": "gpt-4.1-2025-04-14",
            "o3": "o3-2025-04-16",
            "o3-pro": "o3-pro-2025-04-16",
            "sonar": "sonar-2025-09",
            "sonar-pro": "sonar-pro-2025-09",
            "sonar-reasoning-pro": "sonar-reasoning-pro-2025-09",
            "claude-opus-4.1": "claude-opus-4-1-20250805",
            "claude-sonnet-4": "claude-sonnet-4-20250514",
            "claude-sonnet-3.7": "claude-3-7-sonnet-20250219",
        }
        self.load_prompts()

    def load_prompts(self):
        """
        Load all JSON prompt files from the prompt directory.
        """
        if not self.prompts_dir.is_dir():
            logger.error(f"Prompt directory not found: {self.prompts_dir}")
            return

        for file_path in self.prompts_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    self.prompts[file_path.name] = content
                    logger.info(f"Loaded prompts from {file_path.name}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON in {file_path.name}: {e}")
            except Exception as e:
                logger.error(f"Error loading prompt file {file_path.name}: {e}")

    def get_prompt(self, model_id: str, prompt_name: str) -> Optional[str]:
        """
        Retrieve a specific prompt for a given model and prompt name.
        
        Args:
            model_id (str): Identifier of the model.
            prompt_name (str): Name of the prompt.
        
        Returns:
            Optional[str]: The prompt text if found, else None.
        """
        if model_id not in self.supported_models:
            logger.warning(f"Model {model_id} is not supported.")
            return None

        for file_name, content in self.prompts.items():
            if prompt_name in content:
                logger.debug(f"Prompt '{prompt_name}' found in {file_name} for model {model_id}")
                return content[prompt_name]

        logger.warning(f"Prompt '{prompt_name}' not found for model {model_id}")
        return None
    
    def load_prompt(self, prompt_name: str) -> str:
        """Load a prompt from the prompts directory"""
        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        if not prompt_path.exists():
            logger.warning(f"Prompt not found: {prompt_path}")
            return ""
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def list_available_prompts(self) -> Dict[str, Any]:
        """
        List all available prompts grouped by their respective files.
        
        Returns:
            Dict[str, Any]: A dictionary of prompts grouped by file names.
        """
        return {file_name: list(content.keys()) for file_name, content in self.prompts.items()}


# Testing the PromptLoader
if __name__ == "__main__":
    # Initialize the loader for testing purposes
    loader = PromptLoader(prompt_dir="prompts")
    
    # List all available prompts
    print("Available Prompts:")
    print(loader.list_available_prompts())
    
    # Retrieve a specific prompt
    model = "gpt-4.1"
    prompt = "example_prompt"
    prompt_text = loader.get_prompt(model_id=model, prompt_name=prompt)
    if prompt_text:
        print(f"Retrieved prompt for {model}: {prompt_text}")
    else:
        print(f"Prompt '{prompt}' not found for model {model}")
