# utils/claude_client.py
import os
import logging
from typing import Optional, Dict, Any, List
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
import json

logger = logging.getLogger(__name__)

class ClaudeAnalysisClient:
    """
    Клиент для работы с Claude API для анализа строительных документов
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY не найден в переменных окружения")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-sonnet-20240229"  # Используем Claude 3 Sonnet
        
        # Загружаем промпты из JSON файлов
        self.concrete_prompt = self._load_prompt("prompt/concrete_extractor_prompt.json")
        self.materials_prompt = self._load_prompt("prompt/materials_prompt.json")
    
    def _load_prompt(self, file_path: str) -> Dict[str, Any]:
        """Загрузка промпта из JSON файла"""
        try:
            full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Файл промпта не найден: {file_path}")
                return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки промпта {file_path}: {e}")
            return {}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def analyze_concrete_with_claude(self, document_text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """
        Анализ бетонных конструкций с использованием Claude
        """
        try:
            # Формируем промпт для Claude
            system_prompt = self._build_concrete_system_prompt()
            user_prompt = self._build_concrete_user_prompt(document_text, smeta_data)
            
            # Отправляем запрос к Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.1,  # Низкая температура для точности
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            
            # Обрабатываем ответ
            result_text = response.content[0].text
            logger.info(f"Получен ответ от Claude: {len(result_text)} символов")
            
            # Пытаемся распарсить JSON ответ
            try:
                result_json = json.loads(result_text)
                return {
                    "claude_analysis": result_json,
                    "raw_response": result_text,
                    "model_used": self.model,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                }
            except json.JSONDecodeError:
                # Если JSON не парсится, возвращаем как текст
                return {
                    "claude_analysis": {"error": "Не удалось распарсить JSON ответ"},
                    "raw_response": result_text,
                    "model_used": self.model,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                }
                
        except Exception as e:
            logger.error(f"Ошибка анализа Claude: {e}")
            raise
    
    def _build_concrete_system_prompt(self) -> str:
        """Создание системного промпта для анализа бетона"""
        if not self.concrete_prompt:
            return """Ты — эксперт-инженер по бетонам и строительству. 
            Анализируй проектную документацию и найди все марки бетона и их применение.
            Отвечай в формате JSON."""
        
        prompt_template = self.concrete_prompt.get("prompt_template", {})
        role = prompt_template.get("role", "Ты — инженер-эксперт по бетонам.")
        tasks = prompt_template.get("tasks", [])
        constraints = prompt_template.get("constraints", [])
        
        system_prompt = f"""{role}

ЗАДАЧИ:
{chr(10).join([f"- {task}" for task in tasks])}

ОГРАНИЧЕНИЯ:
{chr(10).join([f"- {constraint}" for constraint in constraints])}

ФОРМАТ ОТВЕТА - строго JSON:
{json.dumps(self.concrete_prompt.get("output_format", {}), indent=2, ensure_ascii=False)}
"""
        return system_prompt
    
    def _build_concrete_user_prompt(self, document_text: str, smeta_data: List[Dict]) -> str:
        """Создание пользовательского промпта"""
        # Ограничиваем длину текста для экономии токенов
        max_doc_length = 8000
        if len(document_text) > max_doc_length:
            document_text = document_text[:max_doc_length] + "...[текст обрезан]"
        
        # Форматируем данные сметы
        smeta_text = ""
        if smeta_data:
            smeta_text = "\n".join([
                f"Строка {item.get('row_number', '?')}: {item.get('description', '')}"
                for item in smeta_data[:50]  # Ограничиваем количество строк
            ])
        
        user_prompt = f"""
ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ:
{document_text}

ДАННЫЕ СМЕТЫ:
{smeta_text}

Проанализируй документы и найди все марки бетона. Верни результат в формате JSON согласно схеме.
"""
        return user_prompt
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def analyze_materials_with_claude(self, document_text: str) -> Dict[str, Any]:
        """
        Анализ строительных материалов (кроме бетона) с использованием Claude
        """
        try:
            system_prompt = """Ты — эксперт по строительным материалам. 
            Найди и классифицируй все строительные материалы в документе, кроме бетона.
            Верни результат в формате JSON."""
            
            user_prompt = f"""
ДОКУМЕНТ:
{document_text[:8000]}

Найди все упоминания строительных материалов: арматуру, окна, двери, уплотнители, металлоконструкции, изоляцию.
Верни в формате JSON с полями: category, term, context_snippet, usage.
"""
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            
            result_text = response.content[0].text
            
            try:
                result_json = json.loads(result_text)
                return {
                    "materials_analysis": result_json,
                    "raw_response": result_text,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                }
            except json.JSONDecodeError:
                return {
                    "materials_analysis": {"error": "Не удалось распарсить JSON ответ"},
                    "raw_response": result_text,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                }
                
        except Exception as e:
            logger.error(f"Ошибка анализа материалов Claude: {e}")
            raise
    
    async def enhance_analysis(self, basic_analysis: Dict[str, Any], document_text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """
        Улучшение базового анализа с помощью Claude
        """
        try:
            # Объединяем базовый анализ с Claude анализом
            claude_concrete = await self.analyze_concrete_with_claude(document_text, smeta_data)
            claude_materials = await self.analyze_materials_with_claude(document_text)
            
            enhanced_result = {
                "basic_analysis": basic_analysis,
                "claude_concrete_analysis": claude_concrete,
                "claude_materials_analysis": claude_materials,
                "enhanced": True,
                "analysis_method": "hybrid_local_claude"
            }
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Ошибка улучшенного анализа: {e}")
            # Возвращаем базовый анализ, если Claude недоступен
            return {
                "basic_analysis": basic_analysis,
                "claude_error": str(e),
                "enhanced": False,
                "analysis_method": "local_only"
            }

# Глобальная инстанция клиента
_claude_client = None

def get_claude_client() -> Optional[ClaudeAnalysisClient]:
    """Получение глобального клиента Claude"""
    global _claude_client
    
    if _claude_client is None:
        try:
            _claude_client = ClaudeAnalysisClient()
            logger.info("Claude клиент инициализирован успешно")
        except Exception as e:
            logger.warning(f"Не удалось инициализировать Claude клиент: {e}")
            _claude_client = None
    
    return _claude_client
