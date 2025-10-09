"""
Claude API Client with proper file-based prompt loading
FIXED: Load prompts from files, support XML parsing
"""
from pathlib import Path
import json
import base64
import logging
from typing import Dict, Any, Optional
import xml.etree.ElementTree as ET
import pandas as pd

from anthropic import Anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for interacting with Claude API"""
    
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = 4096
        self.prompts_dir = settings.PROMPTS_DIR / "claude"
    
    def _load_prompt_from_file(self, prompt_name: str) -> str:
        """
        Load prompt from file
        
        Args:
            prompt_name: Name like 'parsing/parse_vykaz_vymer'
        
        Returns:
            Prompt text
        """
        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        try:
            # ВАЖНО: Используем UTF-8 для чешских символов
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load prompt from {prompt_path}: {e}")
            raise
    
    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Call Claude API with prompt
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
        
        Returns:
            Parsed JSON response
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": temperature,
                "messages": messages
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            response = self.client.messages.create(**kwargs)
            
            # Extract text from response
            result_text = response.content[0].text
            
            # Remove markdown code blocks if present
            result_text = result_text.replace("```json\n", "").replace("```json", "")
            result_text = result_text.replace("```\n", "").replace("```", "")
            result_text = result_text.strip()
            
            # Try to parse as JSON
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                logger.warning("Response is not valid JSON, returning raw text")
                return {"raw_text": result_text}
        
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise
    
    def parse_excel(
        self,
        file_path: Path,
        prompt_name: str = "parsing/parse_vykaz_vymer"
    ) -> Dict[str, Any]:
        """
        Parse Excel file using Claude
        Supports .xlsx, .xls
        
        Args:
            file_path: Path to Excel file
            prompt_name: Name of prompt file to use
        
        Returns:
            Parsed data as dict
        """
        try:
            # Load parsing prompt from file
            parsing_prompt = self._load_prompt_from_file(prompt_name)
            
            logger.info(f"Parsing Excel file: {file_path}")
            
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=0)
            
            # Convert to string representation
            excel_text = df.to_string(index=False, max_rows=1000)
            
            # Also get first 20 rows for detailed view
            sample_text = df.head(20).to_string(index=False)
            
            # Build full prompt
            full_prompt = f"""{parsing_prompt}

===== UKÁZKA PRVNÍCH 20 ŘÁDKŮ =====
{sample_text}

===== CELÝ DOKUMENT =====
{excel_text}
"""
            
            logger.info(f"Sending {len(df)} rows to Claude for parsing")
            
            # Call Claude
            result = self.call(full_prompt)
            
            logger.info(f"Parsed {result.get('total_positions', 0)} positions")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to parse Excel: {e}")
            raise
    
    def parse_xml(
        self,
        file_path: Path,
        prompt_name: str = None
    ) -> Dict[str, Any]:
        """
        Parse XML file using Claude
        Supports .xml files (KROS/RTS export format)
        Auto-detects UNIXML format
        
        Args:
            file_path: Path to XML file
            prompt_name: Name of prompt file to use (auto-detected if None)
        
        Returns:
            Parsed data as dict
        """
        try:
            logger.info(f"Parsing XML file: {file_path}")
            
            # Read XML file with UTF-8 encoding
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Auto-detect XML format
            if prompt_name is None:
                if '<unixml' in xml_content.lower():
                    prompt_name = "parsing/parse_kros_unixml"
                    logger.info("Detected KROS UNIXML format (Soupis prací)")
                elif '<TZ>' in xml_content or '<Row>' in xml_content:
                    prompt_name = "parsing/parse_kros_table_xml"
                    logger.info("Detected KROS Table XML format (Kalkulace s cenami)")
                else:
                    prompt_name = "parsing/parse_vykaz_vymer"
                    logger.info("Using generic XML parser")
            
            # Load appropriate parsing prompt
            parsing_prompt = self._load_prompt_from_file(prompt_name)
            
            # Try to pretty-print XML for better readability
            try:
                root = ET.fromstring(xml_content)
                xml_text = ET.tostring(root, encoding='unicode', method='xml')
            except:
                xml_text = xml_content
            
            # Limit XML size (Claude has token limits)
            max_chars = 50000
            if len(xml_text) > max_chars:
                logger.warning(f"XML truncated from {len(xml_text)} to {max_chars} chars")
                xml_text = xml_text[:max_chars] + "\n\n[... XML ZKRÁCENO PRO ANALÝZU ...]"
            
            # Build full prompt
            full_prompt = f"""{parsing_prompt}

===== XML DOKUMENT =====
{xml_text}
"""
            
            logger.info(f"Sending XML to Claude for parsing (size: {len(xml_text)} chars, prompt: {prompt_name})")
            
            # Call Claude
            result = self.call(full_prompt)
            
            # Validate result
            total_positions = result.get('total_positions', 0)
            positions_count = len(result.get('positions', []))
            
            logger.info(f"Parsed {positions_count} positions from XML (reported: {total_positions})")
            
            if positions_count == 0:
                logger.warning("⚠️  No positions parsed! Check XML structure or prompt.")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to parse XML: {e}")
            raise
    
    def parse_pdf(
        self,
        file_path: Path,
        prompt_name: str = "parsing/parse_vykaz_vymer"
    ) -> Dict[str, Any]:
        """
        Parse PDF file using Claude with Vision
        
        Args:
            file_path: Path to PDF file
            prompt_name: Name of prompt file to use
        
        Returns:
            Parsed data as dict
        """
        try:
            # Load parsing prompt from file
            parsing_prompt = self._load_prompt_from_file(prompt_name)
            
            logger.info(f"Parsing PDF file: {file_path}")
            
            # Read PDF as base64
            with open(file_path, "rb") as f:
                pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")
            
            # Build message with PDF document
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
                            "text": parsing_prompt
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
            result_text = response.content[0].text
            
            # Remove markdown if present
            result_text = result_text.replace("```json\n", "").replace("```json", "")
            result_text = result_text.replace("```\n", "").replace("```", "")
            result_text = result_text.strip()
            
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                logger.warning("PDF parse result is not valid JSON")
                result = {"raw_text": result_text}
            
            logger.info(f"Parsed {result.get('total_positions', 0)} positions from PDF")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            raise
    
    def audit_position(
        self,
        position: Dict[str, Any],
        knowledge_base: Dict[str, Any],
        prompt_name: str = "audit/audit_position"
    ) -> Dict[str, Any]:
        """
        Audit a single position using Claude
        
        Args:
            position: Position data to audit
            knowledge_base: Relevant KB data
            prompt_name: Name of audit prompt file
        
        Returns:
            Audit result
        """
        try:
            # Load audit prompt from file
            audit_prompt = self._load_prompt_from_file(prompt_name)
            
            # Build context
            full_prompt = f"""{audit_prompt}

===== POZICE K AUDITU =====
{json.dumps(position, indent=2, ensure_ascii=False)}

===== KNOWLEDGE BASE =====
{json.dumps(knowledge_base, indent=2, ensure_ascii=False)}
"""
            
            # Call Claude
            result = self.call(full_prompt)
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to audit position: {e}")
            raise
    
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
            Analysis result
        """
        try:
            # Determine image media type
            suffix = image_path.suffix.lower()
            media_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            media_type = media_types.get(suffix, 'image/jpeg')
            
            # Read image as base64
            with open(image_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")
            
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
            result_text = response.content[0].text
            
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                return {"raw_text": result_text}
        
        except Exception as e:
            logger.error(f"Failed to analyze image: {e}")
            raise
