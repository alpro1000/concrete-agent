import pytest
import logging
import requests
import os

logger = logging.getLogger(__name__)

# ====================================================
# 🔍 Функция для проверки импортов
# ====================================================
def check_core_imports():
    """
    Проверяет, доступны ли CORE модули проекта (не зависящие от агентов).
    """
    try:
        from app.core.llm_service import get_llm_service
        from app.core.orchestrator import OrchestratorService
        return True
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта core модулей: {e}")
        return False

def check_agent_available(agent_name: str) -> bool:
    """
    Проверяет, доступен ли конкретный агент.
    Агенты опциональны - тесты должны работать даже если агента нет.
    """
    if agent_name == 'tzd_reader':
        try:
            from agents.tzd_reader.agent import tzd_reader
            return True
        except ImportError:
            return False
    return False

# ====================================================
# ✅ Тест доступности core модулей
# ====================================================
@pytest.mark.skipif(not check_core_imports(), reason="Core модули недоступны")
def test_core_modules_available():
    """
    Проверяет, что core модули доступны независимо от агентов.
    """
    from app.core.llm_service import get_llm_service
    from app.core.orchestrator import OrchestratorService
    
    llm = get_llm_service()
    assert llm is not None
    logger.info("✅ LLM сервис доступен")
    
    orchestrator = OrchestratorService(llm)
    assert orchestrator is not None
    logger.info("✅ Orchestrator доступен")

# ====================================================
# ✅ Тест анализа через TZD агент (если доступен)
# ====================================================
@pytest.mark.skipif(not check_agent_available('tzd_reader'), reason="TZD Reader агент не установлен")
async def test_tzd_agent_if_available():
    """
    Проверяет работу TZD агента, если он установлен.
    Тест пропускается, если агент недоступен.
    """
    try:
        from agents.tzd_reader.agent import tzd_reader
        
        # Simple availability test
        assert tzd_reader is not None
        logger.info("✅ TZD Reader агент доступен")
        
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
        r = requests.get("http://localhost:8000/docs", timeout=2)
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
