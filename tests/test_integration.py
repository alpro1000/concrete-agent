#!/usr/bin/env python3
"""
Тест интегрированного анализа материалов
test_integration.py

Простой тест для проверки работы оркестратора
"""

import asyncio
import logging
import tempfile
import os
from pathlib import Path

from agents.integration_orchestrator import get_integration_orchestrator, IntegratedAnalysisRequest

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

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
    
    # Простая тестовая смета (текстовая)
    smeta_path = os.path.join(temp_dir, "test_smeta.txt")
    with open(smeta_path, "w", encoding="utf-8") as f:
        f.write("""
Položka 1: Beton C25/30 - 125.5 m3 - 3500 Kč/m3
Položka 2: Výztuž Fe500 - 2500 kg - 25 Kč/kg
Položka 3: Okna PVC - 15 ks - 3500 Kč/ks
Položka 4: Izolace XPS - 85.5 m2 - 250 Kč/m2
        """)
    
    return temp_dir, doc_path, smeta_path

async def test_integration():
    """Тест интегрированного анализа"""
    logger.info("🚀 Запуск теста интегрированного анализа")
    
    # Создаем тестовые файлы
    temp_dir, doc_path, smeta_path = create_test_files()
    
    try:
        # Создаем запрос
        request = IntegratedAnalysisRequest(
            doc_paths=[doc_path],
            smeta_path=smeta_path,
            material_query="výztuž",  # Ищем арматуру
            use_claude=False,  # Не используем Claude для теста
            claude_mode="enhancement",
            language="cz"
        )
        
        # Получаем оркестратор
        orchestrator = get_integration_orchestrator()
        
        # Выполняем анализ
        result = await orchestrator.analyze_materials_integrated(request)
        
        # Выводим результаты
        logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТА:")
        logger.info(f"Успех: {result.success}")
        
        if result.success:
            logger.info(f"🏗️ Анализ бетона:")
            logger.info(f"  - Найдено марок: {result.concrete_summary.get('total_grades', 0)}")
            
            logger.info(f"📐 Анализ объемов:")
            logger.info(f"  - Общий объем: {result.volume_summary.get('total_volume_m3', 0)} м³")
            logger.info(f"  - Общая стоимость: {result.volume_summary.get('total_cost', 0)} Kč")
            
            logger.info(f"🔧 Анализ материалов:")
            logger.info(f"  - Запрос: '{request.material_query}'")
            logger.info(f"  - Найдено материалов: {result.material_summary.get('total_materials', 0)}")
            
            logger.info(f"📋 Статусы анализа:")
            for agent, status in result.analysis_status.items():
                logger.info(f"  - {agent}: {status}")
        else:
            logger.error(f"❌ Ошибка: {result.error_message}")
        
        return result.success
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}")
        return False
    finally:
        # Очищаем временные файлы
        import shutil
        shutil.rmtree(temp_dir)
        logger.info("🧹 Временные файлы удалены")

if __name__ == "__main__":
    success = asyncio.run(test_integration())
    if success:
        logger.info("✅ Тест прошел успешно!")
    else:
        logger.error("❌ Тест завершился с ошибкой!")