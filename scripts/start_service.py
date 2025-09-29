#!/usr/bin/env python3
"""
🚀 Быстрый запуск сервиса Concrete Agent
Скрипт для упрощенного запуска и проверки сервиса
"""

import os
import sys
import time
import logging
import subprocess
import requests
from pathlib import Path
from typing import Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class ServiceLauncher:
    """Класс для запуска и управления сервисом"""
    
    def __init__(self, project_root: str = None, port: int = 8000, host: str = "0.0.0.0"):
        self.project_root = Path(project_root).resolve() if project_root else Path(__file__).parent.parent.resolve()
        self.port = port
        self.host = host
        self.server_url = f"http://localhost:{port}"
        self.process: Optional[subprocess.Popen] = None
    
    def check_port_available(self) -> bool:
        """Проверка доступности порта"""
        try:
            response = requests.get(self.server_url, timeout=2)
            logger.warning(f"⚠️ Порт {self.port} уже используется (получен ответ {response.status_code})")
            return False
        except requests.exceptions.ConnectionError:
            # Порт свободен
            return True
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки порта: {e}")
            return True
    
    def run_pre_launch_checks(self) -> bool:
        """Предварительные проверки перед запуском"""
        logger.info("🔍 Предварительные проверки...")
        
        # Проверка основных файлов
        critical_files = ["app/main.py", "requirements.txt"]
        for file_path in critical_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                logger.error(f"❌ Критический файл не найден: {file_path}")
                return False
            logger.info(f"✅ {file_path}")
        
        # Проверка зависимостей
        try:
            import fastapi
            import uvicorn
            logger.info("✅ Основные зависимости установлены")
        except ImportError as e:
            logger.error(f"❌ Не установлены зависимости: {e}")
            logger.info("💡 Выполните: pip install -r requirements.txt")
            return False
        
        # Проверка порта
        if not self.check_port_available():
            logger.info("💡 Для остановки существующего сервера используйте Ctrl+C или закройте процесс")
            return False
        
        return True
    
    def start_server(self, reload: bool = True, log_level: str = "info") -> bool:
        """Запуск сервера"""
        if not self.run_pre_launch_checks():
            return False
        
        logger.info(f"🚀 Запуск Concrete Agent на {self.host}:{self.port}")
        logger.info("=" * 50)
        
        # Команда запуска
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "app.main:app",
            "--host", self.host,
            "--port", str(self.port),
            "--log-level", log_level
        ]
        
        if reload:
            cmd.append("--reload")
        
        try:
            # Запуск в текущей директории проекта
            os.chdir(self.project_root)
            
            logger.info(f"📝 Команда: {' '.join(cmd)}")
            logger.info("⏳ Запуск сервера...")
            
            self.process = subprocess.Popen(cmd)
            
            # Ждем запуск сервера
            self.wait_for_server_start()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска сервера: {e}")
            return False
    
    def wait_for_server_start(self, max_wait: int = 30):
        """Ожидание запуска сервера"""
        logger.info("⏳ Ожидание запуска сервера...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{self.server_url}/health", timeout=2)
                if response.status_code == 200:
                    logger.info("✅ Сервер успешно запущен!")
                    self.print_server_info()
                    return True
            except requests.exceptions.ConnectionError:
                pass
            except Exception as e:
                logger.debug(f"Проверка сервера: {e}")
            
            time.sleep(1)
        
        logger.warning("⚠️ Сервер не отвечает в течение 30 секунд")
        return False
    
    def print_server_info(self):
        """Вывод информации о запущенном сервере"""
        logger.info("=" * 50)
        logger.info("🎉 СЕРВЕР ЗАПУЩЕН УСПЕШНО!")
        logger.info("=" * 50)
        logger.info(f"🌐 URL сервера: {self.server_url}")
        logger.info(f"📚 API документация: {self.server_url}/docs")
        logger.info(f"📖 ReDoc документация: {self.server_url}/redoc")
        logger.info(f"❤️ Health check: {self.server_url}/health")
        logger.info(f"📊 Статус сервиса: {self.server_url}/status")
        logger.info("=" * 50)
        logger.info("💡 ПОЛЕЗНЫЕ КОМАНДЫ:")
        logger.info("   • Ctrl+C - остановить сервер")
        logger.info("   • Проверить статус: curl http://localhost:8000/health")
        logger.info("   • Диагностика: python scripts/diagnose_service.py")
        logger.info("=" * 50)
        
        # Проверим статус сервера
        try:
            response = requests.get(f"{self.server_url}/status", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                logger.info("📈 СТАТУС КОМПОНЕНТОВ:")
                
                # API ключи
                api_config = status_data.get("api_configuration", {})
                claude_ready = api_config.get("anthropic_api_key", {}).get("configured", False)
                openai_ready = api_config.get("openai_api_key", {}).get("configured", False)
                
                logger.info(f"   🤖 Claude API: {'✅ Ready' if claude_ready else '❌ Not configured'}")
                logger.info(f"   🧠 OpenAI API: {'✅ Ready' if openai_ready else '❌ Not configured'}")
                
                # База данных
                db_status = status_data.get("database_status", "unknown")
                logger.info(f"   🗄️ База данных: {'✅ Connected' if db_status == 'operational' else '❌ Issues'}")
                
                if not claude_ready and not openai_ready:
                    logger.info("💡 Для полной функциональности настройте API ключи:")
                    logger.info("   export ANTHROPIC_API_KEY='your_key_here'")
                    logger.info("   export OPENAI_API_KEY='your_key_here'")
                
        except Exception as e:
            logger.debug(f"Не удалось получить статус: {e}")
    
    def stop_server(self):
        """Остановка сервера"""
        if self.process:
            logger.info("🛑 Остановка сервера...")
            self.process.terminate()
            self.process.wait()
            logger.info("✅ Сервер остановлен")

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🚀 Быстрый запуск сервиса Concrete Agent"
    )
    parser.add_argument(
        "--project-root", 
        type=str, 
        help="Путь к корню проекта"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Порт для сервера (по умолчанию: 8000)"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0",
        help="Хост для сервера (по умолчанию: 0.0.0.0)"
    )
    parser.add_argument(
        "--no-reload", 
        action="store_true",
        help="Отключить автоперезагрузку при изменениях"
    )
    parser.add_argument(
        "--log-level", 
        type=str, 
        default="info",
        choices=["critical", "error", "warning", "info", "debug"],
        help="Уровень логирования (по умолчанию: info)"
    )
    parser.add_argument(
        "--check-only", 
        action="store_true",
        help="Только проверить возможность запуска, не запускать сервер"
    )
    
    args = parser.parse_args()
    
    launcher = ServiceLauncher(args.project_root, args.port, args.host)
    
    if args.check_only:
        logger.info("🔍 Режим проверки (без запуска сервера)")
        success = launcher.run_pre_launch_checks()
        if success:
            logger.info("✅ Все проверки пройдены, сервер готов к запуску")
        else:
            logger.error("❌ Обнаружены проблемы, устраните их перед запуском")
        sys.exit(0 if success else 1)
    
    try:
        success = launcher.start_server(
            reload=not args.no_reload,
            log_level=args.log_level
        )
        
        if success:
            # Ожидаем сигнала завершения
            try:
                launcher.process.wait()
            except KeyboardInterrupt:
                logger.info("\n🛑 Получен сигнал остановки")
                launcher.stop_server()
        else:
            logger.error("❌ Не удалось запустить сервер")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Получен сигнал остановки")
        launcher.stop_server()
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        launcher.stop_server()
        sys.exit(1)

if __name__ == "__main__":
    main()