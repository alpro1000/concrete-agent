"""
TZD Reader Agent - Fixed Version
Technical Assignment Reader for AI-powered document analysis
"""

from typing import List, Dict, Any, Optional
import os
import time
import json
import logging
from pathlib import Path

try:
    from services.doc_parser import DocParser
except ImportError:
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
        """Get system prompt for technical assignment analysis"""
        if self.use_new_service:
            try:
                system_prompt = self.prompt_loader.get_system_prompt("tzd")
                if system_prompt:
                    return system_prompt
                logger.warning("Empty system prompt from new service, using fallback")
            except Exception as e:
                logger.warning(f"Failed to load new prompt, using fallback: {e}")
        
        return """Ты — инженер-эксперт по строительным ТЗ и техническим заданиям. Извлеки из текста ключевые требования проекта и верни структурированный JSON.

Возвращай результат СТРОГО в JSON формате:
{
  "project_object": "объект строительства (строка)",
  "requirements": ["основные требования к проекту"],
  "norms": ["нормативные документы: СНиП, ГОСТ, ČSN EN и др."],
  "constraints": ["ограничения: бюджетные, временные, технические"],
  "environment": "условия окружающей среды и эксплуатации",
  "functions": ["целевое назначение и основные функции объекта"]
}

Специфические требования:
- Материалы: Выделяй конкретные марки бетона, стали, других материалов в requirements
- Стандарты: Обращай особое внимание на чешские стандарты ČSN EN
- Безопасность: Включай требования пожарной и конструкционной безопасности

Если информация отсутствует - используй пустые строки или массивы.
Отвечай ТОЛЬКО валидным JSON без комментариев."""
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from AI model response"""
        text = response_text.strip()
        
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()
        
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end != -1 and start < end:
            return text[start:end]
        
        return text
    
    def _get_empty_result(self) -> Dict[str, Any]:
        """Base result for errors"""
        return {
            "project_object": "",
            "requirements": [],
            "norms": [],
            "constraints": [],
            "environment": "",
            "functions": [],
            "processing_error": True
        }
    
    async def analyze_with_llm_service(
        self, 
        text: str, 
        provider: str = "claude"
    ) -> Dict[str, Any]:
        """
        Unified analysis using centralized LLM service
        
        Args:
            text: Text to analyze
            provider: "claude" or "openai"
        """
        if not self.use_new_service:
            raise ValueError("New LLM service not available")
        
        try:
            prompt_config = self.prompt_loader.get_prompt_config("tzd")
            model = prompt_config.get("model", 
                "claude-3-5-sonnet-20241022" if provider == "claude" else "gpt-4o-mini"
            )
            
            # Truncate if needed
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
                raise ValueError(f"LLM service error: {response.get('error', 'Unknown')}")
            
            result_text = response.get("content", "")
            if not result_text:
                raise ValueError("Empty response from LLM service")
            
            json_text = self._extract_json_from_response(result_text)
            result = json.loads(json_text)
            
            # Add metadata
            result['ai_model'] = response.get("model", model)
            result['provider'] = provider
            result['processing_time'] = response.get("usage", {}).get("total_tokens")
            result['analysis_method'] = 'centralized_llm_service'
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM service: {e}")
            return self._get_empty_result()
        except Exception as e:
            logger.error(f"LLM service analysis failed: {e}")
            return self._get_empty_result()
    
    def analyze_with_gpt(self, text: str) -> Dict[str, Any]:
        """Analysis using OpenAI GPT"""
        if self.use_new_service:
            try:
                import asyncio
                return asyncio.run(self.analyze_with_llm_service(text, provider="openai"))
            except Exception as e:
                logger.warning(f"New LLM service failed: {e}")
        
        logger.warning("Using legacy GPT client")
        return self._get_empty_result()
    
    def analyze_with_claude(self, text: str) -> Dict[str, Any]:
        """Analysis using Anthropic Claude"""
        if self.use_new_service:
            try:
                import asyncio
                return asyncio.run(self.analyze_with_llm_service(text, provider="claude"))
            except Exception as e:
                logger.warning(f"New LLM service failed: {e}")
        
        logger.warning("Using legacy Claude client")
        return self._get_empty_result()


def _build_project_summary(parsed_text: str, ai_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build project summary from new format results
    
    Args:
        parsed_text: Raw extracted text
        ai_result: AI analysis result with new format
        
    Returns:
        Dictionary with summary sections
    """
    return {
        "overview": ai_result.get("project_object", "")[:500],
        "requirements": ai_result.get("requirements", []),
        "norms": ai_result.get("norms", []),
        "constraints": ai_result.get("constraints", []),
        "environment": ai_result.get("environment", ""),
        "functions": ai_result.get("functions", [])
    }


def _process_files_with_parsers(files: List[str], base_dir: Optional[str] = None) -> str:
    """Process files using DocParser with optional MinerU integration"""
    if not files:
        raise ValueError("File list cannot be empty")
    
    if len(files) > 20:
        raise ValueError("Too many files to process (maximum: 20)")
    
    validator = FileSecurityValidator()
    doc_parser = DocParser()
    text_parts = []
    total_length = 0
    processed_files = 0
    
    # Try MinerU for PDFs
    pdf_files = [f for f in files if Path(f).suffix.lower() == '.pdf']
    if pdf_files:
        mineru_text = extract_with_mineru_if_available(pdf_files)
        if mineru_text:
            logger.info(f"MinerU processed {len(pdf_files)} PDF files")
            text_parts.append(f"\n=== MinerU Extracted Content ===\n{mineru_text}\n")
            total_length += len(mineru_text)
            processed_files += len(pdf_files)
            files = [f for f in files if Path(f).suffix.lower() != '.pdf']
    
    # Process remaining files
    for file_path in files:
        try:
            validator.validate_file_path(file_path, base_dir)
            validator.validate_file_size(file_path)
            validator.validate_file_extension(file_path)
            
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue
            
            logger.info(f"Processing file: {Path(file_path).name}")
            text = doc_parser.parse(file_path)
            
            if text.strip():
                file_header = f"\n=== File: {Path(file_path).name} ===\n"
                text_parts.extend([file_header, text, "\n"])
                total_length += len(file_header) + len(text) + 1
                
                if total_length > MAX_TOTAL_TEXT_LENGTH:
                    logger.warning("Maximum text limit reached")
                    break
                    
                processed_files += 1
            else:
                logger.warning(f"Empty text in file: {file_path}")
                
        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"File processing error {file_path}: {e}")
            continue
    
    combined_text = ''.join(text_parts)
    
    if not combined_text.strip():
        raise ValueError("Could not extract text from any file")
    
    logger.info(f"Processed {processed_files} files, {len(combined_text)} chars")
    return combined_text


def tzd_reader(
    files: List[str], 
    engine: str = "gpt", 
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function for secure technical assignment analysis
    
    Args:
        files: List of file paths
        engine: AI engine ("gpt", "claude", or "auto")
        base_dir: Base directory for file access restriction
        
    Returns:
        Dictionary with analysis results
    """
    if not files:
        raise ValueError("File list cannot be empty")
    
    if engine.lower() not in ['gpt', 'claude', 'auto']:
        raise ValueError(f"Unsupported AI engine: {engine}")
    
    start_time = time.time()
    
    try:
        combined_text = _process_files_with_parsers(files, base_dir)
        analyzer = SecureAIAnalyzer()
        
        # Select engine
        if engine.lower() == "auto" and analyzer.use_new_service:
            try:
                import asyncio
                result = asyncio.run(
                    analyzer.analyze_with_llm_service(combined_text, provider="claude")
                )
                logger.info("Used centralized LLM service (Claude)")
            except Exception as e:
                logger.warning(f"Auto mode failed, falling back to GPT: {e}")
                result = analyzer.analyze_with_gpt(combined_text)
        elif engine.lower() == "gpt":
            result = analyzer.analyze_with_gpt(combined_text)
        else:  # claude
            result = analyzer.analyze_with_claude(combined_text)
        
        # Add summary and metadata
        result['project_summary'] = _build_project_summary(combined_text, result)
        result['processing_metadata'] = {
            'processed_files': len([f for f in files if os.path.exists(f)]),
            'total_text_length': len(combined_text),
            'processing_time_seconds': round(time.time() - start_time, 2),
            'ai_engine': engine.lower(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return result
        
    except (ValueError, SecurityError) as e:
        raise e
    except Exception as e:
        logger.error(f"Critical error in tzd_reader: {e}")
        error_result = SecureAIAnalyzer()._get_empty_result()
        error_result['critical_error'] = str(e)
        error_result['project_summary'] = {}
        return error_result