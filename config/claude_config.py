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
        "sonnet": "claude-3-7-sonnet-20250219",
        "haiku": "claude-3-haiku-20240307",  # Быстрая и дешёвая
        "opus": "claude-opus-4-1-20250805"     # Самая мощная, но дорогая
    }

    # Настройки по умолчанию
    DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", MODELS["sonnet"])
    MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "4000"))
    TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.1"))

    # Лимиты токенов для разных режимов
    TOKEN_LIMITS = {
        "enhancement": 6000,
        "primary": 8000,
        "fallback": 4000
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

ФОРМАТ ОТВЕТА:
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
- Těsnění: gumové pásы, profily
- Ocelové konstrukce: nosníky, rámy
- Izolace: EPS, XPS, tepelná izolace

ФОРМАТ JSON:
{
  "materials": [
    {"type": "reinforcement", "mentions": ["Fe500", "ocel"], "count": 12}
  ]
}""",

        "version_diff": """Ты — эксперт по строительной документации.
Сравни старую и новую версию проекта.

ЗАДАЧИ:
- Определи изменения в текстовых документах
- Выяви добавленные или удалённые позиции в смете
- Верни список изменений

ФОРМАТ JSON:
{
  "doc_changes": ["+ přidán odstavec o základech", "- odstraněna specifikace oceli"],
  "smeta_changes": [
    {"row": 12, "old": "Beton C25/30 - 20 m3", "new": "Beton C30/37 - 22 m3"}
  ]
}"""
    }

    # Настройки retry
    RETRY_ATTEMPTS = int(os.getenv("CLAUDE_RETRY_ATTEMPTS", "3"))
    RETRY_DELAY = float(os.getenv("CLAUDE_RETRY_DELAY", "1.0"))

    @classmethod
    def get_model_for_mode(cls, mode: str) -> str:
        """Выбор модели в зависимости от режима"""
        model_mapping = {
            "enhancement": cls.MODELS["sonnet"],  # баланс
            "primary": cls.MODELS["opus"],        # качество
            "fallback": cls.MODELS["haiku"]       # скорость
        }
        return model_mapping.get(mode, cls.DEFAULT_MODEL)

    @classmethod
    def get_token_limit_for_mode(cls, mode: str) -> int:
        """Лимит токенов для режима"""
        return cls.TOKEN_LIMITS.get(mode, cls.MAX_TOKENS)

    @classmethod
    def get_prompt(cls, task: str) -> str:
        """Безопасный доступ к системным промптам"""
        return cls.SYSTEM_PROMPTS.get(task, "No system prompt defined for this task.")

    @classmethod
    def get_pricing_info(cls) -> Dict[str, Any]:
        """Информация о ценах"""
        return {
            "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00}
        }

    @classmethod
    def estimate_cost(cls, input_tokens: int, output_tokens: int, model: str = None) -> float:
        """Оценка стоимости запроса"""
        if not model:
            model = cls.DEFAULT_MODEL

        pricing = cls.get_pricing_info()
        model_prices = pricing.get(model, pricing["claude-3-sonnet-20240229"])

        input_cost = (input_tokens / 1_000_000) * model_prices["input"]
        output_cost = (output_tokens / 1_000_000) * model_prices["output"]

        return round(input_cost + output_cost, 4)


# Глобальная конфигурация
claude_config = ClaudeConfig()
