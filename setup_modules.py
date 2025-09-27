#!/usr/bin/env python3
"""
🚀 Автоматическая установка и активация рабочих модулей для Concrete-Agent
Скрипт для проверки и исправления всех компонентов системы
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class ConcreteAgentSetup:
    """Автоматическая настройка Concrete-Agent"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.results = {
            "agents": {},
            "routers": {},
            "services": {},
            "dependencies": {},
            "endpoints": []
        }
    
    def check_project_structure(self) -> bool:
        """Проверка структуры проекта"""
        logger.info("🔍 Проверка структуры проекта...")
        
        required_dirs = [
            "agents", "routers", "app", "utils", "parsers", "prompts"
        ]
        
        missing_dirs = []
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
                logger.warning(f"⚠️ Отсутствует директория: {dir_name}")
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"✅ Создана директория: {dir_name}")
        
        return len(missing_dirs) == 0
    
    def check_agents(self) -> Dict[str, bool]:
        """Проверка наличия рабочих агентов"""
        logger.info("🤖 Проверка агентов...")
        
        expected_agents = [
            ("concrete_agent/agent.py", "ConcreteGradeExtractor"),
            ("volume_agent/agent.py", "VolumeAnalysisAgent"),
            ("material_agent/agent.py", "MaterialAnalysisAgent"),
            ("tzd_reader_secure.py", "SecureAIAnalyzer"),
            ("smetny_inzenyr/agent.py", "SmetnyInzenyr"),
            ("dwg_agent/agent.py", "DwgAnalysisAgent")
        ]
        
        for agent_path, class_name in expected_agents:
            full_path = self.project_root / "agents" / agent_path
            exists = full_path.exists()
            self.results["agents"][agent_path] = exists
            
            if exists:
                logger.info(f"✅ {agent_path}")
            else:
                logger.error(f"❌ {agent_path} не найден")
        
        return self.results["agents"]
    
    def check_routers(self) -> Dict[str, bool]:
        """Проверка роутеров"""
        logger.info("🛣️ Проверка роутеров...")
        
        expected_routers = [
            "analyze_concrete.py",
            "analyze_materials.py", 
            "analyze_volume.py",
            "version_diff.py",
            "upload.py",
            "tzd_router.py"
        ]
        
        for router_file in expected_routers:
            router_path = self.project_root / "routers" / router_file
            exists = router_path.exists()
            self.results["routers"][router_file] = exists
            
            if exists:
                # Проверяем наличие объекта router
                try:
                    with open(router_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        has_router = "router = APIRouter()" in content
                        if has_router:
                            logger.info(f"✅ {router_file}")
                        else:
                            logger.warning(f"⚠️ {router_file} - отсутствует объект router")
                except Exception as e:
                    logger.error(f"❌ Ошибка чтения {router_file}: {e}")
            else:
                logger.error(f"❌ {router_file} не найден")
        
        return self.results["routers"]
    
    def check_services(self) -> Dict[str, bool]:
        """Проверка сервисов и утилит"""
        logger.info("🔧 Проверка сервисов...")
        
        expected_services = [
            "utils/knowledge_base_service.py",
            "utils/report_generator.py",
            "utils/czech_preprocessor.py",
            "parsers/doc_parser.py",
            "parsers/smeta_parser.py"
        ]
        
        for service_path in expected_services:
            full_path = self.project_root / service_path
            exists = full_path.exists()
            self.results["services"][service_path] = exists
            
            if exists:
                logger.info(f"✅ {service_path}")
            else:
                logger.error(f"❌ {service_path} не найден")
        
        return self.results["services"]
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Проверка зависимостей"""
        logger.info("📦 Проверка зависимостей...")
        
        critical_packages = [
            "fastapi", "uvicorn", "pdfplumber", "python-docx", 
            "openpyxl", "anthropic", "pandas", "numpy"
        ]
        
        for package in critical_packages:
            try:
                __import__(package.replace("-", "_"))
                self.results["dependencies"][package] = True
                logger.info(f"✅ {package}")
            except ImportError:
                self.results["dependencies"][package] = False
                logger.error(f"❌ {package} не установлен")
        
        return self.results["dependencies"]
    
    def install_missing_dependencies(self) -> bool:
        """Установка отсутствующих зависимостей"""
        missing = [pkg for pkg, status in self.results["dependencies"].items() if not status]
        
        if not missing:
            logger.info("✅ Все зависимости установлены")
            return True
        
        logger.info(f"📥 Установка отсутствующих зависимостей: {missing}")
        
        try:
            requirements_path = self.project_root / "requirements.txt"
            if requirements_path.exists():
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_path)
                ], check=True)
                logger.info("✅ Зависимости установлены из requirements.txt")
                return True
            else:
                logger.error("❌ requirements.txt не найден")
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка установки зависимостей: {e}")
            return False
    
    def test_server(self) -> Tuple[bool, List[str]]:
        """Тестирование запуска сервера"""
        logger.info("🚀 Тестирование запуска сервера...")
        
        try:
            # Импортируем приложение
            sys.path.insert(0, str(self.project_root))
            from app.main import app
            
            # Получаем список endpoints
            endpoints = []
            for route in app.routes:
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    for method in route.methods:
                        if method != 'HEAD':  # Исключаем HEAD методы
                            endpoints.append(f"{method} {route.path}")
            
            self.results["endpoints"] = endpoints
            logger.info(f"✅ Сервер загружается успешно, найдено {len(endpoints)} endpoints")
            return True, endpoints
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска сервера: {e}")
            return False, []
    
    def generate_report(self) -> str:
        """Генерация отчета о состоянии системы"""
        logger.info("📊 Генерация отчета...")
        
        report = {
            "timestamp": "2025-09-27T15:00:00Z",
            "project_root": str(self.project_root),
            "summary": {
                "agents_ok": sum(self.results["agents"].values()),
                "agents_total": len(self.results["agents"]),
                "routers_ok": sum(self.results["routers"].values()),
                "routers_total": len(self.results["routers"]),
                "services_ok": sum(self.results["services"].values()),
                "services_total": len(self.results["services"]),
                "dependencies_ok": sum(self.results["dependencies"].values()),
                "dependencies_total": len(self.results["dependencies"]),
                "endpoints_count": len(self.results["endpoints"])
            },
            "detailed_results": self.results
        }
        
        report_path = self.project_root / "setup_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Отчет сохранен: {report_path}")
        return str(report_path)
    
    def run_full_setup(self) -> bool:
        """Запуск полной настройки"""
        logger.info("🚀 ЗАПУСК АВТОМАТИЧЕСКОЙ НАСТРОЙКИ CONCRETE-AGENT")
        logger.info("=" * 60)
        
        success = True
        
        # 1. Структура проекта
        if not self.check_project_structure():
            logger.warning("⚠️ Были созданы отсутствующие директории")
        
        # 2. Проверка агентов
        agents_status = self.check_agents()
        if not all(agents_status.values()):
            logger.error("❌ Не все агенты найдены")
            success = False
        
        # 3. Проверка роутеров
        routers_status = self.check_routers()
        if not all(routers_status.values()):
            logger.error("❌ Не все роутеры найдены")
            success = False
        
        # 4. Проверка сервисов
        services_status = self.check_services()
        if not all(services_status.values()):
            logger.error("❌ Не все сервисы найдены")
            success = False
        
        # 5. Проверка зависимостей
        deps_status = self.check_dependencies()
        if not all(deps_status.values()):
            logger.warning("⚠️ Попытка установки недостающих зависимостей...")
            if not self.install_missing_dependencies():
                success = False
        
        # 6. Тест сервера
        server_ok, endpoints = self.test_server()
        if not server_ok:
            logger.error("❌ Сервер не запускается")
            success = False
        
        # 7. Генерация отчета
        report_path = self.generate_report()
        
        # Итоговый статус
        logger.info("=" * 60)
        if success:
            logger.info("✅ НАСТРОЙКА ЗАВЕРШЕНА УСПЕШНО!")
            logger.info(f"🎯 Найдено {len(endpoints)} активных endpoints")
            logger.info("🚀 Проект готов к работе!")
        else:
            logger.error("❌ НАСТРОЙКА ЗАВЕРШЕНА С ОШИБКАМИ")
            logger.info("📄 Проверьте отчет для деталей")
        
        logger.info(f"📊 Отчет: {report_path}")
        return success


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Автоматическая установка и активация модулей Concrete-Agent"
    )
    parser.add_argument(
        "--project-root", 
        type=str, 
        help="Путь к корню проекта (по умолчанию: текущая директория)"
    )
    parser.add_argument(
        "--install-deps", 
        action="store_true",
        help="Принудительная переустановка зависимостей"
    )
    
    args = parser.parse_args()
    
    setup = ConcreteAgentSetup(args.project_root)
    
    if args.install_deps:
        logger.info("🔄 Принудительная установка зависимостей...")
        setup.install_missing_dependencies()
    
    success = setup.run_full_setup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()