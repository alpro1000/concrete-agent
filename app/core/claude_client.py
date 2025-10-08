"""
Claude API Client Wrapper - WITH XML Support
"""
import json
import base64
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Union, Dict, Any
from anthropic import Anthropic

from app.core.config import settings


class ClaudeClient:
    """Wrapper for Anthropic Claude API with XML support"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")
        
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
        """Basic Claude API call"""
        messages = [{"role": "user", "content": prompt}]
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature,
            system=system_prompt if system_prompt else "",
            messages=messages
        )
        
        text_response = response.content[0].text
        
        try:
            return json.loads(text_response)
        except json.JSONDecodeError:
            return {"raw_text": text_response}
    
    def parse_excel(
        self, 
        file_path: Path, 
        prompt: str
    ) -> Dict[str, Any]:
        """
        Parse Excel file using Claude
        NOW with XML fallback support
        """
        import pandas as pd
        
        try:
            # Try reading as Excel first
            df = pd.read_excel(file_path)
            
            excel_text = f"Excel file: {file_path.name}\n\n"
            excel_text += f"Columns: {', '.join(df.columns)}\n\n"
            excel_text += "Data:\n"
            excel_text += df.to_string(index=False, max_rows=1000)
            
            full_prompt = f"{prompt}\n\n{excel_text}"
            
            return self.call(full_prompt)
        
        except Exception as excel_error:
            print(f"      ⚠️  Excel parsing failed: {excel_error}")
            print(f"      🔄 Trying XML parsing...")
            
            # Fallback to XML parsing
            try:
                return self.parse_xml(file_path, prompt)
            except Exception as xml_error:
                raise Exception(
                    f"Failed to parse as Excel ({excel_error}) "
                    f"and XML ({xml_error}). "
                    f"File may be corrupted or in unsupported format."
                )
    
    def parse_xml(
        self,
        file_path: Path,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Parse XML file using Claude
        
        Supports Czech building XML formats like:
        - KROS XML export
        - RTS XML export  
        - Custom výkaz XML
        """
        print(f"      📄 Parsing XML: {file_path.name}")
        
        try:
            # Read XML file
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Parse XML to verify it's valid
            try:
                tree = ET.fromstring(xml_content)
                print(f"      ✅ Valid XML detected, root tag: <{tree.tag}>")
            except ET.ParseError as e:
                raise Exception(f"Invalid XML structure: {e}")
            
            # Build prompt with XML content
            xml_text = f"XML file: {file_path.name}\n\n"
            xml_text += "XML Content:\n"
            xml_text += xml_content[:10000]  # First 10KB
            
            if len(xml_content) > 10000:
                xml_text += f"\n\n... (truncated, total size: {len(xml_content)} chars)"
            
            full_prompt = f"""{prompt}

IMPORTANT: This is an XML file, not Excel.
Parse the XML structure and extract positions.

Common XML formats:
- <Position> or <Pozice> tags
- <Item> tags
- Attributes: number, description, quantity, unit, price

{xml_text}
"""
            
            return self.call(full_prompt)
        
        except Exception as e:
            raise Exception(f"Failed to parse XML: {str(e)}")
    
    def parse_pdf(
        self,
        file_path: Path,
        prompt: str
    ) -> Dict[str, Any]:
        """Parse PDF file using Claude with Vision"""
        with open(file_path, "rb") as f:
            pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
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
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages
        )
        
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
        """Analyze image using Claude Vision"""
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        suffix = image_path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        media_type = media_types.get(suffix, "image/jpeg")
        
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
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages
        )
        
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
        """Complete with context"""
        if context:
            full_prompt = f"Context:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        return self.call(full_prompt, system_prompt=system_prompt)
