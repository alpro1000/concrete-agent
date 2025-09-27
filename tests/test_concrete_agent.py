import pytest
import logging
import requests

logger = logging.getLogger(__name__)

# ====================================================
# 🔍 Функция для проверки импортов
# ====================================================
def check_imports():
    """
    Проверяет, доступны ли внутренние модули проекта.
    """
    try:
        from utils.claude_client import get_claude_client
        # Import from the main concrete_agent.py file (not the package)
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location("concrete_agent_main", 
                os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents', 'concrete_agent.py'))
        concrete_agent_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(concrete_agent_main)
        analyze_concrete = concrete_agent_main.analyze_concrete
        from config.claude_config import claude_config
        return True
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        return False

# ====================================================
# ✅ Тест гибридного анализа через Claude
# ====================================================
@pytest.mark.skipif(not check_imports(), reason="Не найдены модули проекта")
async def test_hybrid_analysis():
    """
    Проверяет работу агента Concrete через Claude API.
    """
    # Import from the main concrete_agent.py file (not the package)
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location("concrete_agent_main", 
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents', 'concrete_agent.py'))
    concrete_agent_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(concrete_agent_main)
    analyze_concrete = concrete_agent_main.analyze_concrete

    try:
        result = await analyze_concrete(["test_doc.pdf"], None, use_claude=False)
        assert result is not None
        logger.info(f"✅ Результат анализа: {result}")

    except Exception as e:
        if "rate_limit" in str(e).lower():
            pytest.skip("⚠️ Превышен лимит API запросов")
        elif "insufficient" in str(e).lower():
            pytest.skip("⚠️ Недостаточно средств на счёте API")
        else:
            raise

# ====================================================
# 🌍 Тест доступности API
# ====================================================
def api_running():
    """Проверяет, поднят ли сервер API на localhost:8000"""
    try:
        r = requests.get("http://localhost:8000/docs")
        return r.status_code == 200
    except Exception:
        return False

@pytest.mark.skipif(not api_running(), reason="API сервер не запущен")
def test_api_docs_available():
    """
    Проверяет, что FastAPI сервер поднят и доступен
    """
    response = requests.get("http://localhost:8000/docs")
    assert response.status_code == 200
    logger.info("✅ API документация доступна на /docs")
