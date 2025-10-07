"""
Claude API Client Wrapper
"""
import json
import base64
from pathlib import Path
from typing import Optional, Union, Dict, Any
from anthropic import Anthropic

from app.core.config import settings


class ClaudeClient:
    """Wrapper for Anthropic Claude API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in settings or environment")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS
    
    def call(
        self, 
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Basic Claude API call
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
        
        Returns:
            Parsed JSON response from Claude
        """
        messages = [{"role": "user", "content": prompt}]
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature,
            system=system_prompt if system_prompt else "",
            messages=messages
        )
        
        # Extract text response
        text_response = response.content[0].text
        
        # Try to parse as JSON
        try:
            return json.loads(text_response)
        except json.JSONDecodeError:
            # If not JSON, return as text in dict
            return {"raw_text": text_response}
    
    def parse_excel(
        self, 
        file_path: Path, 
        prompt: str
    ) -> Dict[str, Any]:
        """
        Parse Excel file using Claude
        
        Args:
            file_path: Path to Excel file
            prompt: Parsing instructions
        
        Returns:
            Parsed data
        """
        # Read Excel file
        import pandas as pd
        
        try:
            # Try reading as Excel
            df = pd.read_excel(file_path)
            
            # Convert to text representation
            excel_text = f"Excel file: {file_path.name}\n\n"
            excel_text += f"Columns: {', '.join(df.columns)}\n\n"
            excel_text += "Data:\n"
            excel_text += df.to_string(index=False, max_rows=1000)
            
            # Build full prompt
            full_prompt = f"{prompt}\n\n{excel_text}"
            
            # Call Claude
            return self.call(full_prompt)
        
        except Exception as e:
            raise Exception(f"Failed to parse Excel: {str(e)}")
    
    def parse_pdf(
        self,
        file_path: Path,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Parse PDF file using Claude with Vision
        
        Args:
            file_path: Path to PDF file
            prompt: Parsing instructions
        
        Returns:
            Parsed data
        """
        # Read PDF as base64
        with open(file_path, "rb") as f:
            pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        # Build message with PDF
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        # Call Claude with document
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages
        )
        
        # Extract and parse response
        text_response = response.content[0].text
        
        try:
            return json.loads(text_response)
        except json.JSONDecodeError:
            return {"raw_text": text_response}
    
    def analyze_image(
        self,
        image_path: Path,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Analyze image using Claude Vision
        
        Args:
            image_path: Path to image file
            prompt: Analysis instructions
        
        Returns:
            Analysis results
        """
        # Read image as base64
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        # Detect media type
        suffix = image_path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        media_type = media_types.get(suffix, "image/jpeg")
        
        # Build message with image
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages
        )
        
        # Extract response
        text_response = response.content[0].text
        
        try:
            return json.loads(text_response)
        except json.JSONDecodeError:
            return {"raw_text": text_response}
    
    def complete(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete with context (for multi-turn conversations)
        
        Args:
            prompt: User prompt
            context: Additional context dict
            system_prompt: System instructions
        
        Returns:
            Response dict
        """
        # Add context to prompt if provided
        if context:
            full_prompt = f"Context:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        return self.call(full_prompt, system_prompt=system_prompt)
