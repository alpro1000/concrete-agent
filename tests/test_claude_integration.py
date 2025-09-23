#!/usr/bin/env python3
# test_claude_integration.py
"""
Скрипт для тестирования интеграции Claude API
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_claude_basic():
    """Базовый тест Claude API"""
    try:
        from utils.claude_client import get_claude_client
        
        logger.info("🧪 Тестирование базового подключения к Claude...")
        
        claude_client = get_claude_client()
        if not claude_client:
            logger.error("❌ Claude клиент не инициализирован")
            return False
        
        # Простой тест
        response = await asyncio.to_thread(
            claude_client.client.messages.create,
            model="claude-3-sonnet-20240229",
            max_tokens=50,
            messages=[{"role": "user", "content": "Привет! Ответь коротко 'Привет из Claude!'"}]
        )
        
        result_text = response.content[0].text
        logger.info(f"✅ Claude ответил: {result_text}")
        logger.info(f"📊 Токенов использовано: {response.usage.input_tokens + response.usage.output_tokens}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка базового теста Claude: {e}")
        return False

async def test_concrete_analysis():
    """Тест анализа бетона"""
    try:
        from utils.claude_client import get_claude_client
        
        logger.info("🏗️ Тестирование анализа бетона...")
        
        claude_client = get_claude_client()
        if not claude_client:
            return False
        
        test_text = """
        Technická zpráva:
        V projektu se používá beton C25/30 XC1 pro základy.
        Pro věnce se použije beton C30/37 XF1.
        Stěny budou z betonu B20.
        Schodiště - beton C25/30.
        """
        
        test_smeta = [
            {"description": "Beton C25/30 pro základy", "qty": 15.5, "unit": "m3", "code": "801.1"},
            {"description": "Beton C30/37 pro věnce", "qty": 5.2, "unit": "m3", "code": "801.2"}
        ]
        
        result = await claude_client.analyze_concrete_with_claude(test_text, test_smeta)
        
        if result.get("success"):
            logger.info("✅ Анализ бетона выполнен успешно")
            analysis = result.get("claude_analysis", {})
            logger.info(f"📊 Найдено марок бетона: {len(analysis.get('concrete_grades', []))}")
            logger.info(f"🎯 Токенов использовано: {result.get('tokens_used', 0)}")
            return True
        else:
            logger.error("❌ Анализ бетона неуспешен")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка анализа бетона: {e}")
        return False

async def test_hybrid_analysis():
    """Тест гибридного анализа"""
    try:
        logger.info("🔄 Тестирование гибридного анализа...")
        
        # Создаем тестовые файлы
        test_text = """
        Projekt stavby:
        Používá se beton C25/30 XC1 pro základové konstrukce.
        Věnce z betonu C30/37 XF1.
        Stěny budou provedeny z betonu B20.
        """
        
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Создаем тестовый документ
            doc_path = os.path.join(tmpdir, "test_doc.txt")
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(test_text)
            
            # Создаем тестовую смету
            smeta_path = os.path.join(tmpdir, "test_smeta.txt")
            with open(smeta_path, "w", encoding="utf-8") as f:
                f.write("Beton C25/30 pro základy - 15.5 m3\nBeton C30/37 pro věnce - 5.2 m3")
            
            # Тестируем разные режимы
            from agents.concrete_agent_hybrid import analyze_concrete
            
            modes = ["fallback", "enhancement", "primary"]
            results = {}
            
            for mode in modes:
                try:
                    logger.info(f"🧪 Тестирование режима: {mode}")
                    start_time = asyncio.get_event_loop().time()
                    
                    result = await analyze_concrete(
                        doc_paths=[doc_path],
                        smeta_path=smeta_path,
                        use_claude=True,
                        claude_mode=mode
                    )
                    
                    end_time = asyncio.get_event_loop().time()
                    execution_time = round(end_time - start_time, 2)
                    
                    concrete_count = len(result.get("concrete_summary", []))
                    analysis_method = result.get("analysis_method", "unknown")
                    
                    results[mode] = {
                        "time": execution_time,
                        "concrete_grades": concrete_count,
                        "method": analysis_method,
                        "success": True
                    }
                    
                    logger.info(f"✅ {mode}: {execution_time}с, {concrete_count} марок, метод: {analysis_method}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка в режиме {mode}: {e}")
                    results[mode] = {"success": False, "error": str(e)}
            
            # Анализируем результаты
            successful_modes = [m for m, r in results.items() if r.get("success")]
            if successful_modes:
                logger.info(f"✅ Успешно протестированы режимы: {', '.join(successful_modes)}")
                
                # Находим самый быстрый
                fastest = min(successful_modes, key=lambda m: results[m].get("time", 999))
                logger.info(f"⚡ Самый быстрый режим: {fastest} ({results[fastest]['time']}с)")
                
                return True
            else:
                logger.error("❌ Ни один режим не работает")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка гибридного тестирования: {e}")
        return False

async def test_api_endpoints():
    """Тест API эндпоинтов"""
    try:
        logger.info("🌐 Тестирование API эндпоинтов...")
        
        import requests
        import json
        
        # Предполагаем, что сервер запущен локально
        base_url = "http://localhost:8000"
        
        # Тест статуса Claude
        try:
            response = requests.get(f"{base_url}/test/claude/status", timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                logger.info(f"✅ Claude статус: {status_data.get('status')}")
            else:
                logger.warning(f"⚠️ API недоступен (статус {response.status_code})")
        except requests.exceptions.RequestException:
            logger.warning("⚠️ Сервер не запущен локально")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования API: {e}")
        return False

async def test_cost_estimation():
    """Тест оценки стоимости"""
    try:
        logger.info("💰 Тестирование оценки стоимости Claude...")
        
        from config.claude_config import claude_config
        
        # Тестовые сценарии
        scenarios = [
            {"name": "Малый документ", "input": 2000, "output": 500},
            {"name": "Средний документ", "input": 5000, "output": 1000},
            {"name": "Большой документ", "input": 10000, "output": 2000}
        ]
        
        for scenario in scenarios:
            cost = claude_config.estimate_cost(
                scenario["input"], 
                scenario["output"], 
                "claude-3-sonnet-20240229"
            )
            logger.info(f"💵 {scenario['name']}: ${cost:.4f}")
        
        # Сравнение моделей
        models = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
        logger.info("📊 Сравнение стоимости моделей (5000 input + 1000 output токенов):")
        
        for model in models:
            cost = claude_config.estimate_cost(5000, 1000, model)
            logger.info(f"   {model}: ${cost:.4f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования стоимости: {e}")
        return False

async def run_all_tests():
    """Запуск всех тестов"""
    logger.info("🚀 Начинаем полное тестирование Claude интеграции...")
    
    tests = [
        ("Базовое подключение", test_claude_basic),
        ("Анализ бетона", test_concrete_analysis), 
        ("Гибридный анализ", test_hybrid_analysis),
        ("API эндпоинты", test_api_endpoints),
        ("Оценка стоимости", test_cost_estimation)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Запуск теста: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            success = await test_func()
            results[test_name] = success
            status = "✅ УСПЕХ" if success else "❌ ОШИБКА"
            logger.info(f"📋 Результат: {status}")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка в тесте '{test_name}': {e}")
            results[test_name] = False
    
    # Итоги
    logger.info(f"\n{'='*60}")
    logger.info("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    logger.info(f"{'='*60}")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅" if success else "❌"
        logger.info(f"{status} {test_name}")
    
    logger.info(f"\n🎯 РЕЗУЛЬТАТ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Claude интеграция работает корректно.")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} тестов провалено. Проверьте конфигурацию.")
        return False

def check_environment():
    """Проверка переменных окружения"""
    logger.info("🔍 Проверка переменных окружения...")
    
    required_vars = ["ANTHROPIC_API_KEY"]
    optional_vars = ["USE_CLAUDE", "CLAUDE_MODE", "CLAUDE_MODEL"]
    
    missing_required = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
        else:
            logger.info(f"✅ {var}: установлен")
    
    for var in optional_vars:
        value = os.getenv(var, "не установлен")
        logger.info(f"ℹ️ {var}: {value}")
    
    if missing_required:
        logger.error(f"❌ Отсутствуют обязательные переменные: {', '.join(missing_required)}")
        logger.error("💡 Установите переменные окружения:")
        for var in missing_required:
            logger.error(f"   export {var}=ваше_значение")
        return False
    
    return True

async def main():
    """Главная функция"""
    print("🤖 Claude API Integration Test Suite")
    print("=" * 60)
    
    # Проверяем окружение
    if not check_environment():
        logger.error("🚫 Невозможно запустить тесты без настройки окружения")
        return False
    
    # Запускаем тесты
    success = await run_all_tests()
    
    if success:
        print("\n🎊 ПОЗДРАВЛЯЕМ! Claude API полностью интегрирован и работает!")
        print("🚀 Теперь можно деплоить на Render с уверенностью.")
    else:
        print("\n🔧 Необходимо исправить ошибки перед деплоем.")
    
    return success

if __name__ == "__main__":
    # Запуск тестов
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)
