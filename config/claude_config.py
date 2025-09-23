# config/claude_config.py
"""
Конфигурация для Claude API
"""
import os
from typing import Dict, Any

class ClaudeConfig:
    """Настройки для Claude API"""
    
    # Модели Claude
    MODELS = {
        "sonnet": "claude-3-sonnet-20240229",
        "haiku": "claude-3-haiku-20240307",  # Более быстрая и дешевая
        "opus": "claude-3-opus-20240229"     # Самая мощная, но дорогая
    }
    
    # Настройки по умолчанию
    DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", MODELS["sonnet"])
    MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "4000"))
    TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.1"))
    
    # Лимиты токенов для разных режимов
    TOKEN_LIMITS = {
        "enhancement": 6000,  # Ограничиваем для экономии
        "primary": 8000,      # Полный анализ
        "fallback": 4000      # Минимальный
    }
    
    # Системные промпты
    SYSTEM_PROMPTS = {
        "concrete_analysis": """Ты — эксперт-инженер по бетонам и строительству в Чехии. 
Анализируй проектную документацию и находи все марки бетона и их применение.

ЗАДАЧИ:
- Найди все упоминания марок бетона (B20, C25/30, C30/37 XF4 и т.д.)
- Определи классы среды (XO, XC1-4, XD1-3, XS1-3, XF1-4, XA1-3)
- Определи где применяется каждая марка (základy, věnce, stropy, stěny, sloupy)
- Найди соответствия в смете

ФОРМАТ ОТВЕТА - обязательно JSON:
{
  "concrete_grades": [
    {
      "grade": "C25/30",
      "environment_classes": ["XC1", "XF1"],
      "used_in": ["základy", "věnce"],
      "smeta_references": ["řádek 15: Beton C25/30 pro základy"]
    }
  ]
}""",
        
        "materials_analysis": """Ты — эксперт по строительным материалам в Чехии.
Найди и классифицируй все строительные материалы кроме бетона.

КАТЕГОРИИ:
- Výztuž (арматура): ocel, Fe500, R100
- Okna a dveře: PVC, dřevo, hliník
- Těsnění: gumové pásy, profily
- Ocelové konstrukce: nosníky, rámy
- Izolace: EPS, XPS, tepelná izolace

Верни в JSON формате."""
    }
    
    # Настройки retry
    RETRY_ATTEMPTS = int(os.getenv("CLAUDE_RETRY_ATTEMPTS", "3"))
    RETRY_DELAY = float(os.getenv("CLAUDE_RETRY_DELAY", "1.0"))
    
    @classmethod
    def get_model_for_mode(cls, mode: str) -> str:
        """Выбор модели в зависимости от режима"""
        model_mapping = {
            "enhancement": cls.MODELS["sonnet"],  # Баланс
            "primary": cls.MODELS["sonnet"],      # Качество
            "fallback": cls.MODELS["haiku"]       # Скорость
        }
        return model_mapping.get(mode, cls.DEFAULT_MODEL)
    
    @classmethod
    def get_token_limit_for_mode(cls, mode: str) -> int:
        """Лимит токенов для режима"""
        return cls.TOKEN_LIMITS.get(mode, cls.MAX_TOKENS)
    
    @classmethod
    def get_pricing_info(cls) -> Dict[str, Any]:
        """Информация о ценах"""
        return {
            "claude-3-sonnet": {
                "input": 3.00,   # $ per 1M tokens
                "output": 15.00
            },
            "claude-3-haiku": {
                "input": 0.25,   # Дешевле
                "output": 1.25
            },
            "claude-3-opus": {
                "input": 15.00,  # Дороже
                "output": 75.00
            }
        }
    
    @classmethod
    def estimate_cost(cls, input_tokens: int, output_tokens: int, model: str = None) -> float:
        """Оценка стоимости запроса"""
        if not model:
            model = cls.DEFAULT_MODEL
        
        pricing = cls.get_pricing_info()
        model_prices = pricing.get(model, pricing["claude-3-sonnet"])
        
        input_cost = (input_tokens / 1_000_000) * model_prices["input"]
        output_cost = (output_tokens / 1_000_000) * model_prices["output"]
        
        return round(input_cost + output_cost, 4)

# Глобальная конфигурация
claude_config = ClaudeConfig()
