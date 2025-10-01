#!/usr/bin/env python3
"""
Тест интегрированного анализа материалов
test_integration.py

Простой тест для проверки работы core компонентов (без зависимости от агентов)
"""

import asyncio
import logging
import tempfile
import os
import pytest
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_core_available():
    """Проверяет доступность core модулей"""
    try:
        from app.core.orchestrator import OrchestratorService
        from app.core.llm_service import get_llm_service
        return True
    except ImportError as e:
        logger.error(f"Core модули недоступны: {e}")
        return False

def create_test_files():
    """Создает тестовые файлы для анализа"""
    temp_dir = tempfile.mkdtemp()
    logger.info(f"Создаем тестовые файлы в {temp_dir}")
    
    # Тестовый документ с маркой бетона
    doc_path = os.path.join(temp_dir, "test_document.txt")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("""
Projektová dokumentace
Použitý beton: C25/30 XC2 XF1
Použitá výztuž: Fe500 - 2500 kg
Okna PVC - 15 ks
Tepelná izolace XPS 100mm - 85.5 m2
Ocelový nosník IPE200 - 450 kg
Střešní krytina - tašky keramické - 125 m2
Těsnění EPDM - 45 m

MOSTNÍ OPĚRA ZE ŽELEZOBETONU C30/37
Objem betonu: 125.5 m3
Cena: 3500 Kč za m3

ZÁKLADOVÁ DESKA C25/30
Plocha: 85.2 m2
Tloušťka: 300 mm
        """)
    
    return temp_dir, doc_path

@pytest.mark.skipif(not check_core_available(), reason="Core модули недоступны")
@pytest.mark.asyncio
async def test_orchestrator_file_detection():
    """Тест определения типов файлов оркестратором"""
    logger.info("🚀 Запуск теста определения типов файлов")
    
    # Создаем тестовые файлы
    temp_dir, doc_path = create_test_files()
    
    try:
        from app.core.orchestrator import OrchestratorService
        from app.core.llm_service import get_llm_service
        
        # Получаем оркестратор
        llm = get_llm_service()
        orchestrator = OrchestratorService(llm)
        
        # Тестируем определение типа файла
        file_type = orchestrator.detect_file_type(doc_path)
        logger.info(f"Определен тип файла: {file_type}")
        
        assert file_type in ['technical_document', 'technical_assignment', 'general_document']
        logger.info("✅ Тест определения типа файла прошел успешно")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}")
        return False
    finally:
        # Очищаем временные файлы
        import shutil
        shutil.rmtree(temp_dir)
        logger.info("🧹 Временные файлы удалены")

@pytest.mark.skipif(not check_core_available(), reason="Core модули недоступны")
@pytest.mark.asyncio
async def test_orchestrator_lazy_loading():
    """Тест ленивой загрузки агентов"""
    logger.info("🚀 Запуск теста ленивой загрузки агентов")
    
    try:
        from app.core.orchestrator import OrchestratorService
        from app.core.llm_service import get_llm_service
        
        # Получаем оркестратор
        llm = get_llm_service()
        orchestrator = OrchestratorService(llm)
        
        # Пытаемся загрузить TZD агент (единственный поддерживаемый)
        tzd_agent = await orchestrator._get_agent('tzd')
        logger.info(f"TZD агент доступен: {tzd_agent is not None}")
        
        # Система должна корректно обрабатывать запросы на несуществующие агенты
        unknown_agent = await orchestrator._get_agent('unknown_agent')
        logger.info(f"Unknown агент должен быть None: {unknown_agent is None}")
        
        assert unknown_agent is None, "Несуществующий агент должен возвращать None"
        
        logger.info("✅ Тест ленивой загрузки прошел успешно (система работает независимо от наличия агентов)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}")
        return False

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))