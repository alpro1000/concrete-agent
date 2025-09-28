"""
TZD Reader Agent - Refactored Version
Technical Assignment Reader for AI-powered document analysis
"""

from typing import List, Dict, Any, Optional
import os
import time
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from parsers.doc_parser import DocParser
from utils.ai_clients import get_openai_client, get_anthropic_client
from utils.mineru_client import extract_with_mineru_if_available
from .security import FileSecurityValidator, SecurityError

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
MAX_TOTAL_TEXT_LENGTH = 500_000


class SecureAIAnalyzer:
    """Secure AI analyzer using centralized LLM service"""
    
    def __init__(self):
        # Import new LLM service
        import sys
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        
        try:
            from app.core.llm_service import get_llm_service
            from app.core.prompt_loader import get_prompt_loader
            self.llm_service = get_llm_service()
            self.prompt_loader = get_prompt_loader()
            self.use_new_service = True
            logger.info("Using new centralized LLM service")
        except Exception as e:
            logger.warning(f"Failed to load new LLM service, falling back to legacy: {e}")
            self.use_new_service = False
            
        # Always initialize legacy clients as fallback
        try:
            self.openai_client = get_openai_client()
            self.anthropic_client = get_anthropic_client()
        except Exception as e:
            logger.warning(f"Failed to initialize legacy clients: {e}")
            self.openai_client = None
            self.anthropic_client = None
            
        self.openai_model = os.getenv('OPENAI_MODEL', DEFAULT_OPENAI_MODEL)
        self.claude_model = os.getenv('CLAUDE_MODEL', DEFAULT_CLAUDE_MODEL)
    
    def get_analysis_prompt(self) -> str:
        """Prompt for technical assignment analysis"""
        if self.use_new_service:
            try:
                # Use new prompt system
                return self.prompt_loader.get_system_prompt("tzd")
            except Exception as e:
                logger.warning(f"Failed to load new prompt, using fallback: {e}")
        
        # Fallback to hardcoded prompt
        return """Проанализируй техническое задание и верни результат СТРОГО в формате JSON.

Требуемые поля JSON:
{
  "project_name": "название проекта (строка)",
  "project_scope": "описание объёма работ (строка)", 
  "materials": ["список материалов"],
  "concrete_requirements": ["марки бетона и требования"],
  "norms": ["нормативные документы"],
  "functional_requirements": ["функциональные требования"],
  "risks_and_constraints": ["риски и ограничения"],
  "estimated_complexity": "низкая|средняя|высокая",
  "key_technologies": ["ключевые технологии"]
}

Если информация отсутствует - используй пустые строки или массивы.
Отвечай ТОЛЬКО валидным JSON без комментариев.

Текст технического задания:
"""
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from AI model response"""
        text = response_text.strip()
        
        # Remove markdown blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()
        
        # Find JSON object
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end != -1 and start < end:
            return text[start:end]
        
        return text
    
    def _get_empty_result(self) -> Dict[str, Any]:
        """Base result for errors"""
        return {
            "project_name": "",
            "project_scope": "",
            "materials": [],
            "concrete_requirements": [],
            "norms": [],
            "functional_requirements": [],
            "risks_and_constraints": [],
            "estimated_complexity": "неопределена",
            "key_technologies": [],
            "processing_error": True
        }
    
    async def analyze_with_new_llm_service(self, text: str) -> Dict[str, Any]:
        """Analysis using new centralized LLM service"""
        if not self.use_new_service:
            raise ValueError("New LLM service not available")
        
        try:
            # Get prompt configuration
            prompt_config = self.prompt_loader.get_prompt_config("tzd")
            provider = prompt_config.get("provider", "gpt")
            model = prompt_config.get("model", "gpt-4o-mini")
            
            # Truncate text if too long
            max_tokens_input = 100000
            if len(text) > max_tokens_input:
                text = text[:max_tokens_input] + "\n\n[ТЕКСТ ОБРЕЗАН ПО ЛИМИТУ]"
                logger.warning("Text truncated for API")
            
            system_prompt = self.get_analysis_prompt()
            
            response = await self.llm_service.run_prompt(
                provider=provider,
                prompt=text,
                system_prompt=system_prompt,
                model=model,
                max_tokens=4000
            )
            
            if not response.get("success"):
                raise ValueError(f"LLM service error: {response.get('error', 'Unknown error')}")
            
            result_text = response.get("content", "")
            if not result_text:
                raise ValueError("Empty response from LLM service")
            
            # Extract and parse JSON
            json_text = self._extract_json_from_response(result_text)
            result = json.loads(json_text)
            
            # Add metadata
            result['ai_model'] = response.get("model", model)
            result['provider'] = provider
            result['processing_time'] = response.get("usage", {}).get("output_tokens", None)
            result['analysis_method'] = 'new_llm_service'
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from new LLM service: {e}")
            return self._get_empty_result()
        except Exception as e:
            logger.error(f"New LLM service analysis failed: {e}")
            return self._get_empty_result()
    
    def analyze_with_gpt(self, text: str) -> Dict[str, Any]:
        """Analysis using OpenAI GPT"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        # Truncate text if too long
        max_tokens_input = 100000  # Approximate limit for gpt-4o-mini
        if len(text) > max_tokens_input:
            text = text[:max_tokens_input] + "\n\n[ТЕКСТ ОБРЕЗАН ПО ЛИМИТУ]"
            logger.warning("Text truncated for OpenAI API")
        
        try:
            prompt = self.get_analysis_prompt() + text
            
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты эксперт по анализу технических заданий в строительстве. "
                                 "Отвечай ТОЛЬКО валидным JSON без дополнительного текста."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                timeout=API_TIMEOUT
            )
            
            result_text = response.choices[0].message.content
            if not result_text:
                raise ValueError("Empty response from OpenAI")
            
            json_text = self._extract_json_from_response(result_text)
            result = json.loads(json_text)
            
            # Add metadata
            result['ai_model'] = self.openai_model
            result['processing_time'] = response.usage.total_tokens if hasattr(response, 'usage') else None
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from GPT: {e}")
            return self._get_empty_result()
        except Exception as e:
            logger.error(f"GPT analysis error: {e}")
            return self._get_empty_result()
    
    def analyze_with_claude(self, text: str) -> Dict[str, Any]:
        """Analysis using Anthropic Claude"""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")
        
        # Truncate text if too long  
        max_tokens_input = 180000  # Limit for Claude
        if len(text) > max_tokens_input:
            text = text[:max_tokens_input] + "\n\n[ТЕКСТ ОБРЕЗАН ПО ЛИМИТУ]"
            logger.warning("Text truncated for Claude API")
        
        try:
            prompt = self.get_analysis_prompt() + text
            
            response = self.anthropic_client.messages.create(
                model=self.claude_model,
                max_tokens=4000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=API_TIMEOUT
            )
            
            result_text = response.content[0].text
            if not result_text:
                raise ValueError("Empty response from Claude")
            
            json_text = self._extract_json_from_response(result_text)
            result = json.loads(json_text)
            
            # Add metadata
            result['ai_model'] = self.claude_model
            result['processing_time'] = response.usage.output_tokens if hasattr(response, 'usage') else None
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Claude: {e}")
            return self._get_empty_result()
        except Exception as e:
            logger.error(f"Claude analysis error: {e}")
            return self._get_empty_result()


def _build_project_summary(parsed_text: str, ai_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build project summary by sections
    
    Args:
        parsed_text: Raw extracted text
        ai_result: AI analysis result
        
    Returns:
        Dictionary with summary sections
    """
    return {
        "overview": ai_result.get("project_scope", "")[:500],
        "scope": ai_result.get("project_scope", ""),
        "concrete": ai_result.get("concrete_requirements", []),
        "materials": ai_result.get("materials", []),
        "norms": ai_result.get("norms", []),
        "risks": ai_result.get("risks_and_constraints", []),
        "schedule": [],  # Could be extracted with additional logic
        "costs": [],     # Could be extracted with additional logic
        "deliverables": []  # Could be extracted with additional logic
    }


def _process_files_with_parsers(files: List[str], base_dir: Optional[str] = None) -> str:
    """
    Process files using DocParser with optional MinerU integration
    
    Args:
        files: List of file paths
        base_dir: Base directory for security validation
        
    Returns:
        Combined text from all files
        
    Raises:
        SecurityError: For security violations
        ValueError: For invalid inputs
    """
    if not files:
        raise ValueError("File list cannot be empty")
    
    if len(files) > 20:
        raise ValueError("Too many files to process (maximum: 20)")
    
    validator = FileSecurityValidator()
    doc_parser = DocParser()
    text_parts = []
    total_length = 0
    processed_files = 0
    
    # Try MinerU first for PDFs if available
    pdf_files = [f for f in files if Path(f).suffix.lower() == '.pdf']
    mineru_text = None
    
    if pdf_files:
        mineru_text = extract_with_mineru_if_available(pdf_files)
        if mineru_text:
            logger.info(f"MinerU processed {len(pdf_files)} PDF files")
            text_parts.append(f"\n=== MinerU Extracted Content ===\n{mineru_text}\n")
            total_length += len(mineru_text)
            processed_files += len(pdf_files)
            # Remove processed PDFs from the main list
            files = [f for f in files if Path(f).suffix.lower() != '.pdf']
    
    # Process remaining files with DocParser
    for file_path in files:
        try:
            # Security validation
            validator.validate_file_path(file_path, base_dir)
            validator.validate_file_size(file_path)
            validator.validate_file_extension(file_path)
            
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue
            
            logger.info(f"Processing file: {Path(file_path).name}")
            
            # Use DocParser
            text = doc_parser.parse(file_path)
            
            if text.strip():
                file_header = f"\n=== File: {Path(file_path).name} ===\n"
                text_parts.extend([file_header, text, "\n"])
                
                total_length += len(file_header) + len(text) + 1
                
                # Check total limit
                if total_length > MAX_TOTAL_TEXT_LENGTH:
                    logger.warning("Maximum text limit reached")
                    break
                    
                processed_files += 1
            else:
                logger.warning(f"Empty text in file: {file_path}")
                
        except SecurityError:
            raise  # Security issues interrupt processing
        except Exception as e:
            logger.error(f"File processing error {file_path}: {e}")
            continue  # Continue with other files
    
    combined_text = ''.join(text_parts)
    
    if not combined_text.strip():
        raise ValueError("Could not extract text from any file")
    
    logger.info(f"Processed files: {processed_files}")
    logger.info(f"Total text length: {len(combined_text)} characters")
    
    return combined_text


def tzd_reader(files: List[str], engine: str = "gpt", base_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Main function for secure technical assignment analysis
    
    Args:
        files: List of file paths
        engine: AI engine ("gpt", "claude", or "auto" for new service)
        base_dir: Base directory for file access restriction
        
    Returns:
        Dictionary with analysis results including project_summary
        
    Raises:
        ValueError: For invalid parameters
        SecurityError: For security issues
    """
    if not files:
        raise ValueError("File list cannot be empty")
    
    if engine.lower() not in ['gpt', 'claude', 'auto']:
        raise ValueError(f"Unsupported AI engine: {engine}. Use 'gpt', 'claude', or 'auto'")
    
    start_time = time.time()
    
    try:
        # Process files using DocParser with optional MinerU
        combined_text = _process_files_with_parsers(files, base_dir)
        
        # AI analysis
        analyzer = SecureAIAnalyzer()
        
        # Try new LLM service first if available and auto mode
        if engine.lower() == "auto" and analyzer.use_new_service:
            try:
                import asyncio
                result = asyncio.run(analyzer.analyze_with_new_llm_service(combined_text))
                logger.info("Used new centralized LLM service")
            except Exception as e:
                logger.warning(f"New LLM service failed, falling back to legacy: {e}")
                # Fallback to GPT
                result = analyzer.analyze_with_gpt(combined_text)
        elif engine.lower() == "gpt":
            result = analyzer.analyze_with_gpt(combined_text)
        else:  # claude
            result = analyzer.analyze_with_claude(combined_text)
        
        # Add project summary
        result['project_summary'] = _build_project_summary(combined_text, result)
        
        # Add processing metadata
        result['processing_metadata'] = {
            'processed_files': len([f for f in files if os.path.exists(f)]),
            'total_text_length': len(combined_text),
            'processing_time_seconds': round(time.time() - start_time, 2),
            'ai_engine': engine.lower(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'mineru_used': extract_with_mineru_if_available([]) is not None  # Check if MinerU is available
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Critical error in tzd_reader: {e}")
        error_result = SecureAIAnalyzer()._get_empty_result()
        error_result['critical_error'] = str(e)
        error_result['project_summary'] = {}
        return error_result