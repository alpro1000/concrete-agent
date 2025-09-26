# app/core/router_registry.py
"""
Автоматическая система регистрации роутеров
Больше не нужно менять main.py при добавлении новых агентов!
"""

import importlib
import logging
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter

logger = logging.getLogger(__name__)

class RouterRegistry:
    """Автоматическая регистрация роутеров"""
    
    def __init__(self):
        self.registered_routers = {}
        self.failed_routers = {}
    
    def discover_routers(self, routers_dir: str = "app/routers") -> List[Dict[str, Any]]:
        """
        Автоматически находит и загружает все роутеры из папки
        """
        routers = []
        routers_path = Path(routers_dir)
        
        if not routers_path.exists():
            logger.warning(f"Папка роутеров не найдена: {routers_dir}")
            return routers
        
        # Ищем все Python файлы в папке роuters
        for router_file in routers_path.glob("*.py"):
            if router_file.name.startswith("__"):
                continue
                
            router_name = router_file.stem
            
            # Определяем правильный путь импорта
            if routers_dir.startswith("app/"):
                module_path = f"{routers_dir.replace('/', '.')}.{router_name}"
            else:
                module_path = f"{routers_dir}.{router_name}"
            
            try:
                # Импортируем модуль
                module = importlib.import_module(module_path)
                
                # Ищем роутер в модуле (разные варианты имен)
                router_attr = None
                for attr_name in ['router', 'app_router', f'{router_name}_router']:
                    if hasattr(module, attr_name):
                        router_attr = getattr(module, attr_name)
                        break
                
                if router_attr and isinstance(router_attr, APIRouter):
                    # Получаем метаданные роутера
                    metadata = self._extract_router_metadata(module, router_attr, router_name)
                    routers.append(metadata)
                    self.registered_routers[router_name] = metadata
                    logger.info(f"✅ Роутер {router_name} загружен успешно")
                else:
                    logger.warning(f"⚠️ {router_name}: не найден объект 'router' типа APIRouter")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки роутера {router_name}: {e}")
                self.failed_routers[router_name] = str(e)
        
        return routers
    
    def _extract_router_metadata(self, module, router: APIRouter, name: str) -> Dict[str, Any]:
        """Извлекает метаданные роутера"""
        
        # Попытка получить информацию из модуля
        module_doc = getattr(module, '__doc__', None)
        description = module_doc.strip() if module_doc else f"Router {name}"
        
        # Информация из самого роутера
        prefix = getattr(router, 'prefix', '')
        tags = getattr(router, 'tags', [])
        
        # Подсчитываем endpoints
        routes_count = len(router.routes) if hasattr(router, 'routes') else 0
        
        return {
            'name': name,
            'router': router,
            'prefix': prefix,
            'tags': tags,
            'description': description,
            'routes_count': routes_count,
            'module_path': f"app.routers.{name}",
            'status': 'active'
        }
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Возвращает статус всех роутеров"""
        return {
            'total_discovered': len(self.registered_routers) + len(self.failed_routers),
            'successful': len(self.registered_routers),
            'failed': len(self.failed_routers),
            'registered_routers': list(self.registered_routers.keys()),
            'failed_routers': list(self.failed_routers.keys()),
            'detailed_status': self.registered_routers
        }

# Глобальный экземпляр реестра
router_registry = RouterRegistry()
