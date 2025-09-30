"""
Prompt Loader - Enhanced version with error handling for JSON reading and support for the latest LLM models.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PromptLoader:
    """
    A utility class for loading and managing prompts for various LLM models.
    """

    def __init__(self, prompt_dir: Optional[str] = "prompts"):
        """
        Initialize the PromptLoader with the directory containing JSON prompt files.
        
        Args:
            prompt_dir (str): Directory containing the JSON prompt files.
        """
        self.prompt_dir = prompt_dir
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
        if not os.path.isdir(self.prompt_dir):
            logger.error(f"Prompt directory not found: {self.prompt_dir}")
            return

        for file_name in os.listdir(self.prompt_dir):
            if file_name.endswith(".json"):
                file_path = os.path.join(self.prompt_dir, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = json.load(f)
                        self.prompts[file_name] = content
                        logger.info(f"Loaded prompts from {file_name}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON in {file_name}: {e}")
                except Exception as e:
                    logger.error(f"Error loading prompt file {file_name}: {e}")

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
