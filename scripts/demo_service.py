#!/usr/bin/env python3
"""
🎯 Демонстрация возможностей Concrete Agent Service
Скрипт для показа основных функций сервиса
"""

import os
import sys
import json
import time
import logging
import requests
import tempfile
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class ServiceDemo:
    """Демонстрация функциональности сервиса"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.project_root = Path(__file__).parent.parent.resolve()
    
    def check_server_status(self) -> bool:
        """Проверка статуса сервера"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def demo_service_info(self):
        """Демонстрация информации о сервисе"""
        logger.info("📋 ИНФОРМАЦИЯ О СЕРВИСЕ")
        logger.info("=" * 40)
        
        try:
            response = requests.get(f"{self.server_url}/")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"🏷️ Сервис: {data.get('service', 'Unknown')}")
                logger.info(f"📊 Версия: {data.get('version', 'Unknown')}")
                logger.info(f"🔧 Статус: {data.get('status', 'Unknown')}")
                
                features = data.get('features', {})
                logger.info("✨ Возможности:")
                for feature, enabled in features.items():
                    emoji = "✅" if enabled else "❌"
                    logger.info(f"   {emoji} {feature}")
                
                endpoints = data.get('endpoints', {})
                logger.info("🌐 Доступные endpoints:")
                for name, path in endpoints.items():
                    logger.info(f"   • {name}: {path}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации: {e}")
    
    def demo_status_check(self):
        """Демонстрация проверки статуса"""
        logger.info("\\n🏥 ПРОВЕРКА СОСТОЯНИЯ СИСТЕМЫ")
        logger.info("=" * 40)
        
        try:
            response = requests.get(f"{self.server_url}/status")
            if response.status_code == 200:
                data = response.json()
                
                logger.info(f"🚀 API статус: {data.get('api_status', 'unknown')}")
                logger.info(f"🗄️ База данных: {data.get('database_status', 'unknown')}")
                
                deps = data.get('dependencies', {})
                logger.info("📦 Зависимости:")
                for dep, available in deps.items():
                    emoji = "✅" if available else "❌"
                    logger.info(f"   {emoji} {dep}")
                
                api_config = data.get('api_configuration', {})
                logger.info("🔑 API ключи:")
                for key, config in api_config.items():
                    status = config.get('status', 'unknown')
                    configured = config.get('configured', False)
                    emoji = "✅" if configured else "⚠️"
                    logger.info(f"   {emoji} {key}: {status}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса: {e}")
    
    def demo_file_upload(self):
        """Демонстрация загрузки файлов"""
        logger.info("\\n📤 ЗАГРУЗКА ФАЙЛОВ")
        logger.info("=" * 40)
        
        # Создаем тестовый файл
        test_content = '''Техническое задание на строительство

Объект: Многоэтажный дом
Адрес: г. Прага, ул. Бетонная, д. 456

Спецификация материалов:

1. Фундамент:
   - Бетон М400 (класс B30)
   - Объем: 150 м³

2. Стены:
   - Бетон М350 (класс B25)
   - Объем: 300 м³

3. Перекрытия:
   - Бетон класса B22.5
   - Объем: 180 м³

Дополнительные материалы:
- Арматура A500C - 15 тонн
- Кирпич керамический - 50 тысяч штук
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                files = {'files': ('demo_document.txt', f, 'text/plain')}
                response = requests.post(f"{self.server_url}/legacy/upload/files", files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info("✅ Файл успешно загружен")
                    
                    uploaded = data.get('uploaded', [])
                    for file_info in uploaded:
                        logger.info(f"   📄 {file_info.get('filename')}")
                        logger.info(f"   📂 {file_info.get('path')}")
                    
                    return uploaded
                else:
                    logger.error(f"❌ Ошибка загрузки: {response.status_code}")
                    logger.error(f"   {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка демонстрации загрузки: {e}")
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        return []
    
    def demo_concrete_agent(self):
        """Демонстрация работы агента анализа бетона"""
        logger.info("\\n🧱 АНАЛИЗ БЕТОНА С ПОМОЩЬЮ АГЕНТА")
        logger.info("=" * 40)
        
        # Создаем тестовый документ
        test_content = '''Проект строительства торгового центра

Технические требования к бетону:

Фундаментная плита:
- Марка бетона М450 (класс прочности B35)
- Водонепроницаемость W8
- Объем заливки: 85 м³

Колонны первого этажа:
- Бетон класса B40
- Объем: 45 м³

Перекрытия:
- Марка М350, класс B25
- Общий объем: 220 м³

Лестничные марши:
- Бетон М400
- Объем: 30 м³
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_file = f.name
        
        try:
            # Тестируем агента напрямую
            sys.path.insert(0, str(self.project_root))
            from agents.concrete_agent.agent import ConcreteGradeExtractor
            
            agent = ConcreteGradeExtractor()
            result = agent.analyze_document(temp_file)
            
            if result.get('success'):
                logger.info("✅ Анализ бетона выполнен успешно")
                logger.info(f"🔍 Агент: {result.get('agent_name')} v{result.get('agent_version')}")
                logger.info(f"📊 Найдено марок: {result.get('total_grades_found')}")
                
                summary = result.get('summary', {})
                logger.info(f"📈 Уникальных марок: {summary.get('unique_grades')}")
                logger.info(f"📐 Общий объем: {summary.get('total_volume')} м³")
                
                logger.info("\\n📋 Детальные результаты:")
                for i, grade in enumerate(result.get('concrete_grades', []), 1):
                    logger.info(f"   {i}. Марка: {grade.get('grade')}")
                    if grade.get('strength_class'):
                        logger.info(f"      Класс: {grade.get('strength_class')}")
                    if grade.get('volume_m3'):
                        logger.info(f"      Объем: {grade.get('volume_m3')} м³")
                    if grade.get('locations'):
                        logger.info(f"      Применение: {', '.join(grade.get('locations'))}")
                    logger.info(f"      Достоверность: {grade.get('confidence')*100:.0f}%")
                    
            else:
                logger.error(f"❌ Ошибка анализа: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка демонстрации агента: {e}")
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def demo_diagnostics(self):
        """Демонстрация диагностики"""
        logger.info("\\n🩺 ДИАГНОСТИКА СИСТЕМЫ")
        logger.info("=" * 40)
        
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, 
                str(self.project_root / "scripts" / "diagnose_service.py"),
                "--server-url", self.server_url
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("✅ Диагностика завершена успешно")
                # Показываем только последние строки для краткости
                lines = result.stdout.strip().split('\\n')
                summary_start = -1
                for i, line in enumerate(lines):
                    if "СВОДКА ДИАГНОСТИКИ" in line:
                        summary_start = i
                        break
                
                if summary_start >= 0:
                    logger.info("\\n📊 Краткая сводка:")
                    for line in lines[summary_start:]:
                        if line.strip() and not line.startswith('['):
                            logger.info(f"   {line}")
            else:
                logger.warning("⚠️ Диагностика обнаружила проблемы")
                logger.info("💡 Для деталей запустите: python scripts/diagnose_service.py")
                
        except Exception as e:
            logger.error(f"❌ Ошибка запуска диагностики: {e}")
    
    def run_full_demo(self):
        """Запуск полной демонстрации"""
        logger.info("🎯 ДЕМОНСТРАЦИЯ CONCRETE AGENT SERVICE")
        logger.info("=" * 60)
        
        # Проверяем доступность сервера
        if not self.check_server_status():
            logger.error("❌ Сервер недоступен!")
            logger.info("💡 Запустите сервер: python scripts/start_service.py")
            return False
        
        logger.info("✅ Сервер доступен, начинаем демонстрацию...")
        
        # Демонстрируем различные возможности
        self.demo_service_info()
        self.demo_status_check()
        self.demo_file_upload()
        self.demo_concrete_agent()
        self.demo_diagnostics()
        
        logger.info("\\n" + "=" * 60)
        logger.info("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
        logger.info("=" * 60)
        logger.info("💡 ПОЛЕЗНЫЕ КОМАНДЫ:")
        logger.info("   • Диагностика:     python scripts/diagnose_service.py")
        logger.info("   • Настройка:       python scripts/setup_modules.py")
        logger.info("   • Запуск сервера:  python scripts/start_service.py")
        logger.info("   • API документация: http://localhost:8000/docs")
        logger.info("=" * 60)
        
        return True

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🎯 Демонстрация возможностей Concrete Agent Service"
    )
    parser.add_argument(
        "--server-url", 
        type=str, 
        default="http://localhost:8000",
        help="URL сервера (по умолчанию: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    demo = ServiceDemo(args.server_url)
    success = demo.run_full_demo()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()