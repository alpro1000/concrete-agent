#!/usr/bin/env python3
"""
🩺 Диагностика сервиса Concrete Agent
Расширенный скрипт для диагностики и устранения проблем
"""

import os
import sys
import json
import logging
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class ServiceDiagnostics:
    """Класс для диагностики сервиса Concrete Agent"""
    
    def __init__(self, project_root: str = None, server_url: str = "http://localhost:8000"):
        self.project_root = Path(project_root).resolve() if project_root else Path(__file__).parent.parent.resolve()
        self.server_url = server_url
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "diagnostics": {},
            "recommendations": [],
            "critical_issues": [],
            "status": "unknown"
        }
    
    def run_full_diagnostics(self) -> Dict[str, Any]:
        """Запуск полной диагностики сервиса"""
        logger.info("🩺 ЗАПУСК ДИАГНОСТИКИ CONCRETE AGENT SERVICE")
        logger.info("=" * 60)
        
        # 1. Проверка файловой структуры
        self.check_file_structure()
        
        # 2. Проверка зависимостей Python
        self.check_python_dependencies()
        
        # 3. Проверка переменных окружения
        self.check_environment_variables()
        
        # 4. Проверка запуска сервера
        self.check_server_startup()
        
        # 5. Проверка доступности API
        self.check_api_availability()
        
        # 6. Проверка функциональности endpoints
        self.check_endpoints_functionality()
        
        # 7. Генерация рекомендаций
        self.generate_recommendations()
        
        # 8. Определение общего статуса
        self.determine_overall_status()
        
        # Вывод результатов
        self.print_summary()
        
        return self.results
    
    def check_file_structure(self):
        """Проверка структуры файлов проекта"""
        logger.info("📁 Проверка структуры файлов...")
        
        critical_files = [
            "app/main.py",
            "requirements.txt",
            "scripts/setup_modules.py"
        ]
        
        important_dirs = [
            "agents", "routers", "app", "utils", "parsers"
        ]
        
        structure_status = {
            "critical_files": {},
            "important_dirs": {},
            "missing_critical": [],
            "missing_dirs": []
        }
        
        # Проверка критических файлов
        for file_path in critical_files:
            full_path = self.project_root / file_path
            exists = full_path.exists()
            structure_status["critical_files"][file_path] = exists
            
            if exists:
                logger.info(f"✅ {file_path}")
            else:
                logger.error(f"❌ {file_path} не найден")
                structure_status["missing_critical"].append(file_path)
                self.results["critical_issues"].append(f"Отсутствует критический файл: {file_path}")
        
        # Проверка важных директорий
        for dir_name in important_dirs:
            dir_path = self.project_root / dir_name
            exists = dir_path.exists()
            structure_status["important_dirs"][dir_name] = exists
            
            if exists:
                logger.info(f"✅ {dir_name}/")
            else:
                logger.warning(f"⚠️ {dir_name}/ не найден")
                structure_status["missing_dirs"].append(dir_name)
        
        self.results["diagnostics"]["file_structure"] = structure_status
    
    def check_python_dependencies(self):
        """Проверка Python зависимостей"""
        logger.info("📦 Проверка Python зависимостей...")
        
        dependencies = {
            "fastapi": "fastapi",
            "uvicorn": "uvicorn",
            "pdfplumber": "pdfplumber",
            "python-docx": "docx",
            "openpyxl": "openpyxl",
            "anthropic": "anthropic",
            "pandas": "pandas",
            "numpy": "numpy",
            "requests": "requests",
            "sqlalchemy": "sqlalchemy"
        }
        
        deps_status = {
            "installed": {},
            "missing": [],
            "versions": {}
        }
        
        for package_name, import_name in dependencies.items():
            try:
                module = __import__(import_name)
                deps_status["installed"][package_name] = True
                
                # Попробуем получить версию
                version = getattr(module, '__version__', 'unknown')
                deps_status["versions"][package_name] = version
                
                logger.info(f"✅ {package_name} ({version})")
            except ImportError:
                deps_status["installed"][package_name] = False
                deps_status["missing"].append(package_name)
                logger.error(f"❌ {package_name} не установлен")
        
        if deps_status["missing"]:
            self.results["critical_issues"].append(f"Не установлены зависимости: {', '.join(deps_status['missing'])}")
        
        self.results["diagnostics"]["dependencies"] = deps_status
    
    def check_environment_variables(self):
        """Проверка переменных окружения"""
        logger.info("🔐 Проверка переменных окружения...")
        
        env_vars = {
            "ANTHROPIC_API_KEY": {"required": False, "description": "API ключ для Claude"},
            "OPENAI_API_KEY": {"required": False, "description": "API ключ для OpenAI"},
            "DATABASE_URL": {"required": False, "description": "URL базы данных"},
            "PORT": {"required": False, "description": "Порт сервера"},
            "DEBUG": {"required": False, "description": "Режим отладки"}
        }
        
        env_status = {
            "configured": {},
            "missing_optional": [],
            "values": {}
        }
        
        for var_name, config in env_vars.items():
            value = os.getenv(var_name)
            is_set = bool(value)
            
            env_status["configured"][var_name] = is_set
            env_status["values"][var_name] = "configured" if is_set else "not_set"
            
            if is_set:
                logger.info(f"✅ {var_name}: установлен")
            else:
                if config["required"]:
                    logger.error(f"❌ {var_name}: не установлен (обязательно)")
                    self.results["critical_issues"].append(f"Не установлена обязательная переменная: {var_name}")
                else:
                    logger.info(f"ℹ️ {var_name}: не установлен (опционально) - {config['description']}")
                    env_status["missing_optional"].append(var_name)
        
        self.results["diagnostics"]["environment"] = env_status
    
    def check_server_startup(self):
        """Проверка возможности запуска сервера"""
        logger.info("🚀 Проверка запуска сервера...")
        
        startup_status = {
            "can_import_app": False,
            "import_error": None,
            "endpoints_count": 0
        }
        
        try:
            # Добавляем проект в PYTHONPATH
            sys.path.insert(0, str(self.project_root))
            
            from app.main import app
            startup_status["can_import_app"] = True
            
            # Подсчитываем endpoints
            endpoints_count = len([route for route in app.routes if hasattr(route, 'path')])
            startup_status["endpoints_count"] = endpoints_count
            
            logger.info(f"✅ Приложение импортируется успешно")
            logger.info(f"✅ Найдено {endpoints_count} endpoints")
            
        except Exception as e:
            startup_status["can_import_app"] = False
            startup_status["import_error"] = str(e)
            logger.error(f"❌ Ошибка импорта приложения: {e}")
            self.results["critical_issues"].append(f"Приложение не запускается: {e}")
        
        self.results["diagnostics"]["server_startup"] = startup_status
    
    def check_api_availability(self):
        """Проверка доступности API"""
        logger.info("🌐 Проверка доступности API...")
        
        api_status = {
            "server_running": False,
            "response_time": None,
            "endpoints_accessible": {},
            "health_check": {}
        }
        
        # Основные endpoints для проверки
        test_endpoints = [
            "/",
            "/health",
            "/status",
            "/docs"
        ]
        
        for endpoint in test_endpoints:
            url = f"{self.server_url}{endpoint}"
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                response_time = time.time() - start_time
                
                api_status["endpoints_accessible"][endpoint] = {
                    "status_code": response.status_code,
                    "response_time": round(response_time, 3),
                    "accessible": response.status_code == 200
                }
                
                if response.status_code == 200:
                    logger.info(f"✅ {endpoint} доступен ({response.status_code}, {response_time:.3f}s)")
                    api_status["server_running"] = True
                else:
                    logger.warning(f"⚠️ {endpoint} вернул {response.status_code}")
                
                # Специальная обработка для /health
                if endpoint == "/health" and response.status_code == 200:
                    try:
                        health_data = response.json()
                        api_status["health_check"] = health_data
                        logger.info(f"✅ Health check: {health_data.get('status', 'unknown')}")
                    except:
                        pass
                
            except requests.exceptions.ConnectionError:
                api_status["endpoints_accessible"][endpoint] = {
                    "accessible": False,
                    "error": "Connection refused"
                }
                logger.warning(f"⚠️ {endpoint} недоступен (сервер не запущен?)")
            except Exception as e:
                api_status["endpoints_accessible"][endpoint] = {
                    "accessible": False,
                    "error": str(e)
                }
                logger.error(f"❌ Ошибка доступа к {endpoint}: {e}")
        
        self.results["diagnostics"]["api_availability"] = api_status
    
    def check_endpoints_functionality(self):
        """Проверка функциональности endpoints"""
        logger.info("🔧 Проверка функциональности endpoints...")
        
        functionality_status = {
            "working_endpoints": [],
            "broken_endpoints": [],
            "untested_endpoints": []
        }
        
        if not self.results["diagnostics"]["api_availability"]["server_running"]:
            logger.warning("⚠️ Сервер не запущен, пропуск проверки функциональности")
            functionality_status["untested_endpoints"] = ["all - server not running"]
        else:
            # Тест простых GET endpoints
            simple_endpoints = ["/", "/health", "/status"]
            
            for endpoint in simple_endpoints:
                url = f"{self.server_url}{endpoint}"
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        functionality_status["working_endpoints"].append(endpoint)
                        logger.info(f"✅ {endpoint} работает")
                    else:
                        functionality_status["broken_endpoints"].append(f"{endpoint} (status: {response.status_code})")
                        logger.warning(f"⚠️ {endpoint} не работает (status: {response.status_code})")
                except Exception as e:
                    functionality_status["broken_endpoints"].append(f"{endpoint} (error: {str(e)})")
                    logger.error(f"❌ {endpoint} ошибка: {e}")
        
        self.results["diagnostics"]["endpoints_functionality"] = functionality_status
    
    def generate_recommendations(self):
        """Генерация рекомендаций по устранению проблем"""
        logger.info("💡 Генерация рекомендаций...")
        
        recommendations = []
        
        # Рекомендации по критическим ошибкам
        if self.results["critical_issues"]:
            recommendations.append({
                "priority": "critical",
                "title": "Устранение критических ошибок",
                "description": "Обнаружены критические проблемы, которые требуют немедленного внимания",
                "actions": self.results["critical_issues"]
            })
        
        # Рекомендации по зависимостям
        missing_deps = self.results["diagnostics"].get("dependencies", {}).get("missing", [])
        if missing_deps:
            recommendations.append({
                "priority": "high",
                "title": "Установка недостающих зависимостей",
                "description": "Установите отсутствующие Python пакеты",
                "actions": [
                    f"pip install {' '.join(missing_deps)}",
                    "или выполните: pip install -r requirements.txt"
                ]
            })
        
        # Рекомендации по API ключам
        env_status = self.results["diagnostics"].get("environment", {})
        missing_apis = env_status.get("missing_optional", [])
        if "ANTHROPIC_API_KEY" in missing_apis or "OPENAI_API_KEY" in missing_apis:
            recommendations.append({
                "priority": "medium",
                "title": "Настройка API ключей",
                "description": "Для полной функциональности настройте API ключи",
                "actions": [
                    "Получите API ключ от Anthropic: https://console.anthropic.com/",
                    "Получите API ключ от OpenAI: https://platform.openai.com/",
                    "Установите переменные окружения: ANTHROPIC_API_KEY и OPENAI_API_KEY"
                ]
            })
        
        # Рекомендации по серверу
        if not self.results["diagnostics"].get("api_availability", {}).get("server_running", False):
            recommendations.append({
                "priority": "high",
                "title": "Запуск сервера",
                "description": "Сервер не запущен или недоступен",
                "actions": [
                    "Запустите сервер: uvicorn app.main:app --host 0.0.0.0 --port 8000",
                    "Или используйте: python -m uvicorn app.main:app --reload",
                    "Проверьте логи запуска на предмет ошибок"
                ]
            })
        
        self.results["recommendations"] = recommendations
        
        # Выводим рекомендации
        for rec in recommendations:
            priority_emoji = {"critical": "🚨", "high": "⚠️", "medium": "💡", "low": "ℹ️"}
            emoji = priority_emoji.get(rec["priority"], "ℹ️")
            logger.info(f"{emoji} {rec['title']}")
            logger.info(f"   {rec['description']}")
            for action in rec["actions"]:
                logger.info(f"   • {action}")
    
    def determine_overall_status(self):
        """Определение общего статуса сервиса"""
        if self.results["critical_issues"]:
            status = "critical"
        elif not self.results["diagnostics"].get("api_availability", {}).get("server_running", False):
            status = "down"
        elif self.results["diagnostics"].get("dependencies", {}).get("missing", []):
            status = "degraded"
        else:
            status = "healthy"
        
        self.results["status"] = status
        
        status_messages = {
            "healthy": "✅ Сервис работает нормально",
            "degraded": "⚠️ Сервис работает с ограничениями",
            "down": "❌ Сервис недоступен",
            "critical": "🚨 Сервис имеет критические проблемы"
        }
        
        logger.info(f"🎯 Общий статус: {status_messages[status]}")
    
    def print_summary(self):
        """Вывод краткой сводки результатов"""
        logger.info("=" * 60)
        logger.info("📊 СВОДКА ДИАГНОСТИКИ")
        logger.info("=" * 60)
        
        # Статус компонентов
        components = [
            ("Структура файлов", not bool(self.results["diagnostics"].get("file_structure", {}).get("missing_critical"))),
            ("Зависимости Python", not bool(self.results["diagnostics"].get("dependencies", {}).get("missing"))),
            ("Запуск приложения", self.results["diagnostics"].get("server_startup", {}).get("can_import_app", False)),
            ("API доступность", self.results["diagnostics"].get("api_availability", {}).get("server_running", False))
        ]
        
        for component, status in components:
            emoji = "✅" if status else "❌"
            logger.info(f"{emoji} {component}")
        
        # Рекомендации
        if self.results["recommendations"]:
            logger.info("\n💡 ПЕРВООЧЕРЕДНЫЕ ДЕЙСТВИЯ:")
            for rec in self.results["recommendations"][:3]:  # Показываем только первые 3
                logger.info(f"• {rec['title']}")
        
        logger.info(f"\n🎯 Общий статус: {self.results['status'].upper()}")
        logger.info("=" * 60)
    
    def save_report(self, filename: str = None):
        """Сохранение отчета в файл"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"diagnostics_report_{timestamp}.json"
        
        report_path = self.project_root / filename
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Отчет сохранен: {report_path}")
        return str(report_path)

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Диагностика сервиса Concrete Agent"
    )
    parser.add_argument(
        "--project-root", 
        type=str, 
        help="Путь к корню проекта"
    )
    parser.add_argument(
        "--server-url", 
        type=str, 
        default="http://localhost:8000",
        help="URL сервера для проверки (по умолчанию: http://localhost:8000)"
    )
    parser.add_argument(
        "--save-report", 
        action="store_true",
        help="Сохранить отчет в файл"
    )
    
    args = parser.parse_args()
    
    diagnostics = ServiceDiagnostics(args.project_root, args.server_url)
    results = diagnostics.run_full_diagnostics()
    
    if args.save_report:
        diagnostics.save_report()
    
    # Выход с кодом ошибки если есть критические проблемы
    exit_code = 0 if results["status"] in ["healthy", "degraded"] else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()